"""Verify the deployable file with the official, exact pinned GenLayer SDK.

No wallet, RPC, browser, or private key is used. SDK download is a public artifact.
Run with the Python environment containing requirements.txt.
"""
import contextlib
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = next(ROOT.glob("*.py"))
EVIDENCE = ROOT / "evidence"
EVIDENCE.mkdir(exist_ok=True)
from gltest.direct.sdk_loader import setup_sdk_paths

with (EVIDENCE / "sdk-setup.log").open("w", encoding="utf-8") as stream:
    with contextlib.redirect_stdout(stream):
        sdk_paths = setup_sdk_paths(CONTRACT, version="v0.2.12")
sdk = next(path / "genlayer" for path in sdk_paths if (path / "genlayer").is_dir())
sdk_root = ROOT / ".sdk"
target = sdk_root / "runners" / "genlayer-py-std" / "src" / "genlayer"
shutil.copytree(sdk, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
env = dict(os.environ, GENVMROOT=str(sdk_root), PYTHONIOENCODING="utf-8")
report = {
    "source": CONTRACT.name,
    "source_sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
    "genvm_release": "v0.2.12",
    "runner": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6",
    "stdlib": "py-lib-genlayer-std:11rhn002yfajawsz7fai6mykznbxkxs6l91iskj5cm82c92qhy3v",
    "packages": {name: importlib.metadata.version(name) for name in ("genlayer-test", "genvm-linter", "cloudpickle", "pytest")},
    "checks": {},
    "live_consensus_tested": False,
    "deployment": None,
}
commands = {
    "tests": [sys.executable, "-m", "pytest", "-q"],
    "lint": [sys.executable, "-m", "genvm_linter.cli", "check", str(CONTRACT), "--json"],
    "schema": [sys.executable, "-m", "genvm_linter.cli", "schema", str(CONTRACT), "--json"],
}
for name, command in commands.items():
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, encoding="utf-8", capture_output=True)
    output = result.stdout + result.stderr
    (EVIDENCE / ("verification-" + name + ".log")).write_text(output, encoding="utf-8")
    report["checks"][name] = {"exit_code": result.returncode, "passed": result.returncode == 0}
    print(name + ": " + ("PASS" if result.returncode == 0 else "FAIL"))
    if result.returncode:
        print(output[-4000:])
(EVIDENCE / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
raise SystemExit(0 if all(check["passed"] for check in report["checks"].values()) else 1)

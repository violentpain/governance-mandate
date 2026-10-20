"""Test-only compatibility for gltest 0.29.2; no contract substitutions.

Upstream unlinks a message file while fd0 still holds it. POSIX permits that;
Windows raises WinError 32. Defer ONLY this failed unlink until VM teardown.
The official injector, calldata, storage and nondet/validator functions run intact.
"""
import os
from pathlib import Path
import tempfile
import pytest

@pytest.fixture(autouse=True)
def gltest_windows_message_file(monkeypatch):
    import gltest.direct.loader as loader
    from gltest.direct.vm import VMContext
    original_inject = loader._inject_message_to_fd0
    original_unlink = os.unlink
    original_refresh = VMContext._refresh_gl_message
    pending = []

    def refresh(vm):
        original_refresh(vm)
        # gltest.warp updates _datetime but 0.29.2's refresh omits this key.
        # Synchronize the official message metadata, not a contract clock.
        import sys
        gl = sys.modules.get("genlayer.gl")
        if gl is not None and getattr(gl, "message_raw", None) is not None:
            gl.message_raw["datetime"] = vm._datetime

    def inject(vm):
        def unlink_message(path, *args, **kwargs):
            try:
                return original_unlink(path, *args, **kwargs)
            except PermissionError as exc:
                if exc.winerror != 32 or Path(path).parent != Path(tempfile.gettempdir()):
                    raise
                pending.append(path)
        # The interception only lasts while upstream injects its own message.
        os.unlink = unlink_message
        try:
            return original_inject(vm)
        finally:
            os.unlink = original_unlink

    if os.name == "nt":
        monkeypatch.setattr(loader, "_inject_message_to_fd0", inject)
    monkeypatch.setattr(VMContext, "_refresh_gl_message", refresh)
    yield
    for path in pending:
        try:
            original_unlink(path)
        except FileNotFoundError:
            pass

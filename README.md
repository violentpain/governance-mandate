# GovernanceMandate

AI-assisted, unaudited prototype. A standalone GenLayer governance authorization primitive combining a versioned natural-language charter, independent scope assessment, snapshotted voting and a bounded challenge path. This is an independent contribution, not a Project extract. It holds no real funds and emits no transfers.

An owner publishes a charter; authors propose an action and evidence. Leader and validators independently evaluate the **same immutable charter version/action/evidence**, using separate `gl.nondet.exec_prompt` executions. A custom `run_nondet_unsafe` validator compares the normalized decision and reason code. A well-formed leader YES is insufficient. Only YES/IN_SCOPE opens a ballot. NO and UNCERTAIN are terminal rejection, and invalid model output aborts rather than approving.

## Source and deployment

`governance_mandate.py` is the only deployable file and pins runner `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`.

Constructor arguments are `(charter_text, electorate_addresses, absolute_yes_quorum)`. Example shape:

```json
["The committee may approve public SDK documentation grants up to 100 units. Private marketing and charter amendments are outside its authority.", ["0x1111111111111111111111111111111111111111", "0x2222222222222222222222222222222222222222"], 2]
```

Use addresses actually controlled by the intended demo participants; the example values are placeholders. A single-address electorate with quorum 1 can demonstrate the flow but offers no multi-person governance. No private key is an input.

The prototype is deployed on GenLayer Studionet, chain ID 61999, using Studio Normal (Full Consensus) mode. The recorded deployment transaction is FINALIZED with SUCCESS:

- Contract: `0x66f37C0B2565E6A49e206A58CEe28C0E027f3d97`
- Deployment transaction: `0x92c85d45f61a5913ec0a531ba07c8713d3cea5ae2914d440afc8b72af04f5f8d`
- Deployed source SHA-256: `a7dae2a86945857a25f6d096c835d7fe1dcbfe3a0117f4f86841d7440c89aead`

Constructor deployment and a finalized `get_configuration()` readback were verified live: owner/electorate `0x30e3892feee48f8fa96fb272ae6d9d274940b11b`, quorum 1 and charter version 1. This is a single-member demo configuration. See `evidence/deployment.json` for exact constructor text and recorded readback. Proposal assessment, independent live LLM consensus, voting, challenges, finalization and charter upgrades remain unverified on the live network.

## State and interface

Each charter version stores exact text, SHA-256, owner, version and publication time. The owner may append a new version but cannot overwrite old ones. Each proposal snapshots charter version/hash, electorate, quorum, target, action, evidence and deadlines. Later electorate changes affect future proposals only. Later charter upgrades make old authorizations inactive and old in-flight proposals stale; they never substitute new rules into the old assessment.

| Method | Behavior |
|---|---|
| `upgrade_charter(text)` | Owner only; append immutable version, deactivate authorizations under older versions. |
| `configure_electorate(addresses,quorum)` | Owner only; 1..64 distinct nonzero addresses, fixed YES quorum 1..size for new proposals. |
| `propose(target,action,evidence,voting_seconds,challenge_seconds) -> id` | Snapshot proposal. Vote duration 300..604800 seconds; challenge duration 300..86400 seconds. |
| `assess(id)` | Author only, once during REVIEW before vote deadline. Independent assessment sets VOTING or REJECTED. |
| `vote(id,choice)` | Snapshot elector only, once, before vote deadline. YES/NO/ABSTAIN. |
| `challenge(id,evidence)` | Snapshot elector only, one challenge in `[vote_deadline,challenge_deadline)`. Suspends the proposal as CHALLENGED. |
| `resolve_challenge(id)` | Anyone may trigger a fresh independent evaluation including original and challenge evidence; negative/uncertain result rejects. |
| `finalize(id)` | Anyone at/after challenge deadline; unresolved challenge blocks. Authorization requires reviewed YES, YES >= snapshot quorum, YES > NO and current charter version. Otherwise DENIED/STALE. Terminal proposals cannot finalize again. |
| `get_proposal(id)`, `get_charter(version)` | Full auditable records. |
| `get_configuration()`, `get_vote(id,account)` | Current constitutional authority/configuration and immutable ballot. |
| `is_authorized(id,target)` | True only for finalized AUTHORIZED, exact integration target, and still-current charter version. |

Charter is <=6000 characters, target <=128, action <=2000, initial and challenge evidence <=8000 each. Text is nonempty without leading/trailing whitespace. Proposal IDs bind contract, chain, sequence and all snapshotted inputs. Public authors may create proposals; the chain's execution charges are the resource control, with no private admission backend.

Only these model pairs are accepted: YES/IN_SCOPE; NO/OUT_OF_SCOPE; UNCERTAIN with INSUFFICIENT_EVIDENCE, AMBIGUOUS_CHARTER or UNSAFE_INSTRUCTIONS. No model-generated prose, confidence or executable code controls state.

## Integration and threat model

An integration should read a finalized record, require its own exact `target`, verify the exact `action`, charter version/hash and current authorization, and deduplicate proposal IDs in its own execution state. This primitive records authorization; it does not execute, consume, escrow or reserve assets. Re-reading AUTHORIZED does not make a second execution legitimate. Handle network appeals/finality before irreversible effects.

Owner authority over the charter/electorate is explicit: a compromised or malicious owner can publish new constitutional rules or invalidate old authorizations. Snapshots prevent vote manipulation by changing a current electorate. Address uniqueness is not person uniqueness; Sybil electorates and collusion remain governance assumptions. Every voter and caller check uses the immediate sender, not transaction origin.

Prompt input is serialized as untrusted data, and the instruction layer disallows document directives overriding charter evaluation. Independent validators re-evaluate original inputs rather than following the leader. This reduces single-leader trust; it does **not** prove prompt-injection immunity or model correctness. Correlated model mistakes, ambiguous charters and false evidence remain risks. The injection fixture tests fail-closed state for an UNCERTAIN response, not a live model's resistance. Exact reason-code agreement may reduce liveness across different model judgments.

The first challenge is the only challenge; an early malicious challenge may consume that opportunity. Resolution may occur after the challenge deadline, and unresolved challenges can block finalization indefinitely. This deliberately fails closed and does not guarantee timely finality. A successful challenge reassessment preserves the already-closed ballots; it cannot add votes. No external facts are independently fetched: evidence is an immutable public assertion, not a truth oracle. There is no automatic expiry of a finalized authorization other than charter-version invalidation; downstream systems must enforce any execution-time policy.

## Tests and evidence

Python 3.12+. From this standalone directory:

```text
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe tools/verify.py
```

On Linux/macOS use `.venv/bin/python`. The verifier uses the official `v0.2.12` release SDK corresponding to the exact pinned runner, executes the actual deployable contract with official direct tests, and records semantic lint/schema output plus source digest. `tests/conftest.py` contains documented test-only upstream gltest 0.29.2 compatibility for Windows open-file cleanup and `warp()` message-time refresh; it does not replace contract logic or validator decisions. Only external model responses are mocked.

`evidence/tdd-red.log` records the actual NOT_IMPLEMENTED failure before implementation. The first green suite has 20 passing tests covering independent validator disagreement/forged outputs, invalid/negative/uncertain model responses, voting, snapshot immutability, caller guards, ties/quorum, challenge resolution and deadline boundaries, stale proposals and authorization invalidation. `evidence/verification.json` is the historical local record binding the source to test/lint/schema outcomes; its deployment field predates the separate live record in `evidence/deployment.json`. Direct tests do not prove live LLM quality, live governance flows, or gas costs. Only constructor plus configuration readback have the live evidence described above. No deployed users, audit or production success is claimed.

Official sources checked on 2026-10-21: [current boilerplate](https://github.com/genlayerlabs/genlayer-project-boilerplate), [storage](https://docs.genlayer.com/developers/intelligent-contracts/features/storage), [transaction context](https://docs.genlayer.com/developers/intelligent-contracts/features/transaction-context), [equivalence principles](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle), [direct testing](https://github.com/genlayerlabs/genlayer-testing-suite/blob/main/docs/direct-runner.md), [GenVM v0.2.12](https://github.com/genlayerlabs/genvm/releases/tag/v0.2.12). Pinned SDK source was also inspected.

MIT licensed. See `LICENSE`.

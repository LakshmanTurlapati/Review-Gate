---
phase: 04-automated-hardening-verification
verified: 2026-04-02T22:06:32Z
status: passed
score: 3/3 must-haves verified
---

# Phase 4: Automated Hardening Verification Verification Report

**Phase Goal:** Maintainers can run automated regression checks for the shipped Review Gate runtime before release.
**Verified:** 2026-04-02T22:06:32Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Maintainer can run automated tests for Python server trigger creation, acknowledgement handling, response matching, and timeout behavior. | ✓ VERIFIED | `tests/python/review_gate_test_loader.py:48`, `tests/python/review_gate_test_loader.py:122`, `tests/python/review_gate_test_loader.py:132`, `tests/python/review_gate_test_loader.py:144`, `tests/python/test_review_gate_v2_mcp.py:58`, `tests/python/test_review_gate_v2_mcp.py:93`, `tests/python/test_review_gate_v2_mcp.py:159`, `tests/python/test_review_gate_v2_mcp.py:201`, `tests/python/test_review_gate_v2_mcp.py:297`; `python3 -m unittest discover -s tests/python -p 'test_review_gate_v2_mcp.py' -v` passed 9 tests. |
| 2 | Maintainer can run automated tests for Cursor extension popup lifecycle, session routing, and attachment handling. | ✓ VERIFIED | `V2/cursor-extension/extension.js:420`, `V2/cursor-extension/extension.js:644`, `V2/cursor-extension/extension.js:974`, `V2/cursor-extension/extension.js:1185`, `V2/cursor-extension/extension.js:1395`, `V2/cursor-extension/extension.js:3032`, `V2/cursor-extension/extension.js:3590`, `tests/node/load-extension.js:176`, `tests/node/extension.runtime.test.js:98`, `tests/node/extension.runtime.test.js:126`, `tests/node/extension.runtime.test.js:165`, `tests/node/extension.runtime.test.js:204`, `tests/node/extension.runtime.test.js:233`; `node --test tests/node/extension.runtime.test.js` passed 5 tests. |
| 3 | Maintainer can run repeatable smoke checks for supported installers, including MCP configuration merge behavior. | ✓ VERIFIED | `V2/install.sh:65`, `V2/install.sh:191`, `V2/install.ps1:19`, `V2/install.ps1:175`, `V2/install.bat:46`, `V2/install.bat:156`, `V2/update_mcp_config.py:80`, `V2/update_mcp_config.py:112`, `tests/python/test_update_mcp_config.py:47`, `tests/python/test_update_mcp_config.py:111`, `tests/smoke/test_installers.py:46`, `tests/smoke/test_installers.py:98`, `tests/smoke/test_installers.py:124`, `tests/smoke/test_installers.py:152`, `scripts/run_review_gate_regression_checks.py:21`; installer/config suite passed 8 tests with 2 explicit environment skips, and `python3 scripts/run_review_gate_regression_checks.py` passed all suites. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `tests/python/review_gate_test_loader.py` | Stdlib-only loader for `V2/review_gate_v2_mcp.py` | ✓ VERIFIED | Stubs `mcp` and `faster_whisper`, isolates `REVIEW_GATE_USER_ID`, patches temp runtime, and disables speech-monitor startup in tests. |
| `tests/python/test_review_gate_v2_mcp.py` | Python regression coverage for trigger, ack, response, timeout | ✓ VERIFIED | Covers signed trigger creation, valid and invalid ack envelopes, busy/cancelled branches, response matching, wrong-session cleanup, and timeout cleanup. |
| `V2/cursor-extension/extension.js` | Narrow deterministic extension test seam | ✓ VERIFIED | Exposes `__testHooks` without splitting runtime; hook surface includes reset, trigger processing, popup opening, response writing, upload handling, and session-path helpers. |
| `tests/node/load-extension.js` | Built-in Node loader for the shipped extension | ✓ VERIFIED | Stubs `vscode`, fake webview panels, output channels, open-dialog behavior, and cleanup around runtime root. |
| `tests/node/extension.runtime.test.js` | Node `node:test` coverage for extension runtime behavior | ✓ VERIFIED | Covers valid trigger intake, forged and stale trigger rejection, busy routing, popup cancellation, and attachment response persistence. |
| `V2/install.sh` | POSIX installer smoke contract | ✓ VERIFIED | Supports `REVIEW_GATE_SMOKE` and redirected temp HOME/install roots while still copying assets and writing MCP config. |
| `V2/install.ps1` | PowerShell installer smoke contract | ✓ VERIFIED | Mirrors smoke contract, redirects Windows profile paths, and merges config through `update_mcp_config.py`. |
| `V2/install.bat` | Batch installer smoke contract | ✓ VERIFIED | Mirrors smoke contract, redirects Windows profile paths, preserves backup/restore behavior, and calls the shared config helper. |
| `tests/python/test_update_mcp_config.py` | Fixture coverage for config merge/remove helper | ✓ VERIFIED | Covers POSIX and Windows path injection, merge preservation, remove behavior, invalid JSON, and missing server failure. |
| `tests/smoke/test_installers.py` | Installer smoke driver | ✓ VERIFIED | Runs `install.sh` when available and Windows installers when shells exist; asserts copied assets, rule install, backup creation, and merged config. |
| `scripts/run_review_gate_regression_checks.py` | Single repo-root Phase 4 runner | ✓ VERIFIED | Lists suites, injects suite-local `PYTHONPATH`, runs Python, Node, and installer suites in fixed order, and fails fast on non-zero exit. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `tests/python/review_gate_test_loader.py` | `V2/review_gate_v2_mcp.py` | stubbed import seam | ✓ WIRED | `load_review_gate_module()` imports the shipped module with stubbed `mcp` and `faster_whisper`. |
| `tests/python/test_review_gate_v2_mcp.py` | `V2/review_gate_v2_mcp.py` | real session files + async waits | ✓ WIRED | Tests call `_trigger_cursor_popup_immediately()`, `_wait_for_extension_acknowledgement()`, and `_wait_for_user_input()` directly against the shipped server. |
| `tests/node/load-extension.js` | `V2/cursor-extension/extension.js` | stubbed `vscode` via `Module._load` | ✓ WIRED | Loader injects a fake VS Code host, requires the shipped extension, and resets runtime state through `__testHooks`. |
| `tests/node/extension.runtime.test.js` | `V2/cursor-extension/extension.js` | `__testHooks` + real runtime files | ✓ WIRED | Tests drive `processTriggerFile()`, `openReviewGatePopup()`, `handleImageUpload()`, and `writeSessionResponse()` against real temp session files. |
| `tests/python/test_update_mcp_config.py` | `V2/update_mcp_config.py` | CLI subprocess fixtures | ✓ WIRED | Tests invoke the shipped helper through `sys.executable` and assert the resulting config JSON. |
| `tests/smoke/test_installers.py` | `V2/install.sh` | smoke env contract | ✓ WIRED | Smoke suite exports `REVIEW_GATE_SMOKE`, temp HOME/install roots, and asserts copied assets plus merged config. |
| `tests/smoke/test_installers.py` | `V2/install.ps1` | smoke env contract | ✓ WIRED | PowerShell smoke path is implemented and will execute when `pwsh` or `powershell.exe` exists. |
| `tests/smoke/test_installers.py` | `V2/install.bat` | smoke env contract | ✓ WIRED | Batch smoke path is implemented and will execute when `cmd.exe` exists. |
| `scripts/run_review_gate_regression_checks.py` | `tests/python/test_review_gate_v2_mcp.py` | repo-root subprocess execution | ✓ WIRED | Runner invokes the Python server suite with a suite-local `PYTHONPATH`. |
| `scripts/run_review_gate_regression_checks.py` | `tests/node/extension.runtime.test.js` | repo-root subprocess execution | ✓ WIRED | Runner invokes the Node extension suite directly with `node --test`. |
| `scripts/run_review_gate_regression_checks.py` | `tests/python/test_update_mcp_config.py` and `tests/smoke/test_installers.py` | repo-root subprocess execution | ✓ WIRED | Runner invokes the installer/config suite in the same fixed release-check path. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `tests/python/test_review_gate_v2_mcp.py` | `payload`, `acknowledged`, `response`, `self.server._last_*` | Real JSON written through `MODULE._write_json_atomically()` into isolated session files, then consumed by shipped server wait loops in `V2/review_gate_v2_mcp.py:1187` and `V2/review_gate_v2_mcp.py:1289` | Yes | ✓ FLOWING |
| `tests/node/extension.runtime.test.js` | trigger files, ack/response files, `state.panels[0].webview.messages` | Real temp files plus the shipped extension helpers in `V2/cursor-extension/extension.js:1185`, `V2/cursor-extension/extension.js:1395`, `V2/cursor-extension/extension.js:3032`, and `V2/cursor-extension/extension.js:3590` | Yes | ✓ FLOWING |
| `tests/smoke/test_installers.py` | installed assets and `payload["mcpServers"]["review-gate-v2"]` | Installer subprocesses mutate temp HOME/install roots, then tests read copied files and merged `mcp.json` | Yes | ✓ FLOWING |
| `scripts/run_review_gate_regression_checks.py` | `suite["command"]` and subprocess exit codes | `build_suites()` defines the real Phase 4 commands, `run_suite()` executes them from repo root with suite-local env | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Python server regression suite is runnable | `python3 -m unittest discover -s tests/python -p 'test_review_gate_v2_mcp.py' -v` | 9 tests passed | ✓ PASS |
| Node extension regression suite is runnable | `node --test tests/node/extension.runtime.test.js` | 5 tests passed | ✓ PASS |
| Installer/config smoke suite is runnable | `python3 -m unittest tests/python/test_update_mcp_config.py tests/smoke/test_installers.py -v` | 8 tests passed, 2 skipped because `pwsh`/`powershell.exe`/`cmd.exe` were unavailable on this host | ✓ PASS |
| Repo-root runner advertises the expected suites | `python3 scripts/run_review_gate_regression_checks.py --list` | Listed `python-server`, `node-extension`, and `installers` | ✓ PASS |
| Repo-root release-check runs the full Phase 4 path | `python3 scripts/run_review_gate_regression_checks.py` | `python-server` PASS, `node-extension` PASS, `installers` PASS | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `QUAL-01` | `04-01-PLAN.md` | Maintainer can run automated tests for the Python server's trigger, acknowledgement, response, and timeout behavior. | ✓ SATISFIED | `tests/python/review_gate_test_loader.py:48`, `tests/python/test_review_gate_v2_mcp.py:58`, `tests/python/test_review_gate_v2_mcp.py:93`, `tests/python/test_review_gate_v2_mcp.py:201`, `tests/python/test_review_gate_v2_mcp.py:297`; discover suite passed. |
| `QUAL-02` | `04-02-PLAN.md` | Maintainer can run automated tests for the Cursor extension's popup lifecycle, session routing, and attachment handling. | ✓ SATISFIED | `V2/cursor-extension/extension.js:420`, `V2/cursor-extension/extension.js:1185`, `V2/cursor-extension/extension.js:1395`, `V2/cursor-extension/extension.js:3032`, `V2/cursor-extension/extension.js:3590`; `tests/node/extension.runtime.test.js:98`, `tests/node/extension.runtime.test.js:165`, `tests/node/extension.runtime.test.js:204`, `tests/node/extension.runtime.test.js:233`; Node suite passed. |
| `QUAL-03` | `04-03-PLAN.md` | Maintainer can run repeatable smoke checks for supported installers and confirm MCP configuration merge behavior. | ✓ SATISFIED | `V2/install.sh:65`, `V2/install.ps1:19`, `V2/install.bat:46`, `V2/update_mcp_config.py:80`, `tests/python/test_update_mcp_config.py:47`, `tests/smoke/test_installers.py:98`, `tests/smoke/test_installers.py:124`, `tests/smoke/test_installers.py:152`, `scripts/run_review_gate_regression_checks.py:21`; installer/config suite and repo-root runner passed. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| None | - | No TODO/FIXME/placeholders, empty implementations, or dead test seams were found in the Phase 4 artifacts. | - | No blocker anti-patterns detected. |

### Human Verification Required

No human validation is required to accept Phase 4 against `QUAL-01`, `QUAL-02`, and `QUAL-03`; the requirement is specifically about automated verification, and the automated phase entrypoints passed.

Minimum extra UAT for host-confidence only:

### 1. Windows Installer Smoke Availability

**Test:** Run `python3 -m unittest tests/smoke/test_installers.py -v` or `python3 scripts/run_review_gate_regression_checks.py --suite installers` on a Windows host with `pwsh`, `powershell.exe`, or `cmd.exe` available.
**Expected:** `test_install_ps1_smoke_mode_uses_temp_roots` and/or `test_install_bat_smoke_mode_uses_temp_roots` execute and pass instead of skipping; temp install roots contain copied assets, a `ReviewGateV2.mdc` rule, a backup `mcp.json`, and a merged `review-gate-v2` MCP entry.
**Why human:** This verification host was macOS and lacked Windows shells, so the Windows-specific smoke paths were present and wired but not executed here.

### Gaps Summary

No blocking gaps found. Phase 4 satisfies the roadmap goal and all three mapped requirements automatically.

Residual risk remains in two places:

1. Windows installer smoke execution was skipped in this verification environment because `pwsh`/`powershell.exe` and `cmd.exe` were unavailable. The test coverage and smoke hooks exist, but this host did not execute those branches.
2. The Python server suite is stable through the documented entrypoints `python3 -m unittest discover -s tests/python -p 'test_review_gate_v2_mcp.py' -v` and `python3 scripts/run_review_gate_regression_checks.py`. A bare `python3 -m unittest tests/python/test_review_gate_v2_mcp.py -v` invocation does not work unless `tests/python` is on `PYTHONPATH`, which the repo-root runner handles explicitly in `scripts/run_review_gate_regression_checks.py:29` and `scripts/run_review_gate_regression_checks.py:89`.

---

_Verified: 2026-04-02T22:06:32Z_
_Verifier: Codex (gsd-verifier)_

---
phase: 01-installation-integrity
verified: 2026-04-02T19:36:06Z
status: human_needed
score: 4/4 must-haves verified
human_verification:
  - test: "macOS install smoke on default macOS with an existing multi-server ~/.cursor/mcp.json"
    expected: "install.sh completes without shell redirection or missing-timeout failures, preserves unrelated MCP servers, and installs review-gate-v2, ReviewGateV2.mdc, and review-gate-v2-2.7.3.vsix."
    why_human: "Running the installer would mutate the local machine and Cursor profile, and real Homebrew/SoX/Cursor behavior is platform-specific."
  - test: "Windows PowerShell install/uninstall smoke with an existing multi-server %USERPROFILE%\\.cursor\\mcp.json"
    expected: "install.ps1 merges only review-gate-v2, uninstall.ps1 removes only review-gate-v2, and unrelated MCP servers remain unchanged."
    why_human: "Requires native PowerShell, Cursor, and Windows filesystem behavior that is not available in this session."
  - test: "Windows batch install/uninstall smoke with an existing multi-server %USERPROFILE%\\.cursor\\mcp.json"
    expected: "install.bat and uninstall.bat preserve unrelated MCP servers while installing or removing the current V2 assets."
    why_human: "Requires native cmd.exe, Cursor, and Windows filesystem behavior that is not available in this session."
---

# Phase 1: Installation Integrity Verification Report

**Phase Goal:** Users can install the current Review Gate V2 safely on supported platforms without breaking existing Cursor MCP configuration.
**Verified:** 2026-04-02T19:36:06Z
**Status:** human_needed
**Re-verification:** No - initial verification

## Goal Achievement

All four Phase 1 roadmap success criteria are supported by the current source, and all declared Phase 01 plan must-haves were checked. `gsd-tools` verified all 14 declared plan artifacts and all 17 declared key links across `01-01` through `01-04`.

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | User can run the macOS/Linux installer without shell parsing failures caused by dependency version specifiers. | ✓ VERIFIED | `V2/install.sh` uses `"$VENV_PYTHON" -m pip install "mcp>=1.9.2"` and `"faster-whisper>=1.0.0"` at lines 172-192; negative grep for bare `pip install ...>=` passed. |
| 2 | User can install on default macOS without needing GNU `timeout` or manual script edits. | ✓ VERIFIED | `V2/install.sh` defines `run_with_timeout` with `gtimeout` -> `timeout` -> `python3 subprocess.run(..., timeout=...)` fallback at lines 27-57, and uses it for both the SoX probe and MCP smoke test at lines 126 and 303. |
| 3 | User can install on Windows without unrelated MCP server entries being removed from the user's Cursor MCP configuration. | ✓ VERIFIED | `V2/update_mcp_config.py` merges and removes only `review-gate-v2` at lines 80-120, and is wired from `V2/install.ps1`, `V2/install.bat`, `V2/uninstall.ps1`, and `V2/uninstall.bat`; temp-fixture spot checks preserved `other-server` through merge and remove. |
| 4 | User installs the current V2 rule and current VSIX artifact from filenames and paths that match the shipped repository contents. | ✓ VERIFIED | `V2/cursor-extension/package.json` declares version `2.7.3`, both shipped VSIX files exist, installers resolve `review-gate-v2-2.7.3.vsix`, and install/uninstall scripts plus docs consistently reference `ReviewGateV2.mdc`. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `V2/install.sh` | POSIX installer with quoted pip specifiers, portable timeout helper, current VSIX lookup, and current rule handling | ✓ VERIFIED | `run_with_timeout` defined; quoted specifiers used; root-first `2.7.3` VSIX lookup; installs `ReviewGateV2.mdc`; `bash -n` passed. |
| `V2/update_mcp_config.py` | Shared JSON-safe MCP config merge/remove helper | ✓ VERIFIED | `merge` and `remove` implemented; invalid JSON exits non-zero; temp-fixture merge/remove checks passed; `py_compile` passed. |
| `V2/install.ps1` | PowerShell installer wired to merge-safe MCP config helper and current assets | ✓ VERIFIED | Invokes `update_mcp_config.py merge`; quotes pip specifiers; uses `review-gate-v2-2.7.3.vsix`; installs `ReviewGateV2.mdc`. |
| `V2/install.bat` | Batch installer wired to merge-safe MCP config helper and current assets | ✓ VERIFIED | Invokes `update_mcp_config.py merge`; uses `review-gate-v2-2.7.3.vsix`; installs `ReviewGateV2.mdc`. |
| `V2/uninstall.sh` | POSIX uninstaller that removes only Review Gate's MCP entry and current V2 rule | ✓ VERIFIED | Calls `update_mcp_config.py remove`; no destructive `{ "mcpServers": {} }` rewrite remains; removes `ReviewGateV2.mdc`; `bash -n` passed. |
| `V2/uninstall.ps1` | PowerShell uninstaller that removes only the Review Gate MCP entry and current V2 rule | ✓ VERIFIED | Invokes `update_mcp_config.py remove`; removes `ReviewGateV2.mdc`; backup and restore path present. |
| `V2/uninstall.bat` | Batch uninstaller that removes only the Review Gate MCP entry and current V2 rule | ✓ VERIFIED | Invokes `update_mcp_config.py remove`; removes `ReviewGateV2.mdc`; backup and restore path present. |
| `V2/INSTALLATION.md` | Detailed installation guide aligned to shipped V2 assets and merge-safe MCP behavior | ✓ VERIFIED | References `review-gate-v2-2.7.3.vsix`, `ReviewGateV2.mdc`, and preserving existing `mcpServers`. |
| `readme.md` | Top-level install guidance aligned to current V2 assets and MCP preservation | ✓ VERIFIED | Points to `V2/INSTALLATION.md`, names the current `2.7.3` VSIX and `ReviewGateV2.mdc`, and states MCP config is preserved. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `V2/install.sh` | `V2/requirements_simple.txt` | venv-backed pip installation | ✓ WIRED | `gsd-tools verify key-links` passed and quoted venv-backed pip calls are present. |
| `V2/install.sh` | SoX probe / MCP smoke test | shared timeout wrapper | ✓ WIRED | `run_with_timeout` is used for both checks. |
| `V2/install.ps1` | `V2/update_mcp_config.py` | merge invocation | ✓ WIRED | Calls `merge --config ... --template ... --server-name review-gate-v2`. |
| `V2/install.bat` | `V2/update_mcp_config.py` | merge invocation | ✓ WIRED | Calls `merge --config ... --template ... --server-name review-gate-v2`. |
| `V2/uninstall.ps1` | `V2/update_mcp_config.py` | remove invocation | ✓ WIRED | Calls `remove --config ... --server-name review-gate-v2`. |
| `V2/uninstall.bat` | `V2/update_mcp_config.py` | remove invocation | ✓ WIRED | Calls `remove --config ... --server-name review-gate-v2`. |
| `V2/uninstall.sh` | `V2/update_mcp_config.py` | remove invocation | ✓ WIRED | Calls `remove --config "$HOME/.cursor/mcp.json" --server-name review-gate-v2`. |
| `V2/cursor-extension/package.json` | `V2/install.sh`, `V2/install.ps1`, `V2/install.bat` | current `2.7.3` VSIX basename | ✓ WIRED | All installers resolve `review-gate-v2-2.7.3.vsix`, matching the packaged extension version and shipped files. |
| `V2/ReviewGateV2.mdc` | install and uninstall scripts | current rule copy/removal path | ✓ WIRED | All six runtime scripts reference `ReviewGateV2.mdc`; stale `ReviewGate.mdc` references are absent. |
| `V2/INSTALLATION.md` | `V2/ReviewGateV2.mdc` | manual rule-copy instructions | ✓ WIRED | Manual steps point users at the current V2 rule file. |
| `readme.md` | `V2/INSTALLATION.md` | same current artifact names and merge-safe MCP guidance | ✓ WIRED | README and detailed guide agree on `review-gate-v2-2.7.3.vsix`, `ReviewGateV2.mdc`, and MCP preservation. |

### Data-Flow Trace (Level 4)

Scripts and docs in this phase are mostly static wiring artifacts, so Level 4 tracing was needed only for MCP configuration mutation.

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `V2/update_mcp_config.py` | `servers` / `merged_servers` | Existing config JSON plus `V2/mcp.json` | Yes | ✓ FLOWING |
| `V2/install.sh` | `existing_servers` | Existing `~/.cursor/mcp.json` read by the inline Python merger | Yes (source-traced) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| POSIX installer/uninstaller syntax and helper compilation | `bash -n V2/install.sh && bash -n V2/uninstall.sh && python3 -m py_compile V2/update_mcp_config.py` | success | ✓ PASS |
| MCP merge/remove preserves unrelated servers | temp Python fixture against `V2/update_mcp_config.py` | `ok` | ✓ PASS |
| Invalid JSON is rejected without overwriting the file | temp Python fixture against `V2/update_mcp_config.py remove` | `ok` | ✓ PASS |
| Version alignment between package manifest, scripts, and docs | temp Python assertion against `package.json`, installers, and docs | `ok review-gate-v2-2.7.3.vsix` | ✓ PASS |
| Stale filenames and shell-timeout regressions are absent | negative `rg` for `2.6.4`, `ReviewGate.mdc`, bare `pip install ...>=`, and direct `timeout 3s|5s` | no matches | ✓ PASS |
| Native Windows installer execution | not run | requires native Windows shell and Cursor environment | ? SKIP |
| Real Cursor extension/rule installation in a live user profile | not run | would mutate the local Cursor profile and extension set | ? SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `INST-01` | `01-01` | User can run the macOS/Linux installer without shell parsing failures from dependency version specifiers. | ✓ SATISFIED | `V2/install.sh` uses quoted version specifiers through the venv interpreter; stale bare specifiers are absent. `REQUIREMENTS.md` traceability still shows Pending, but implementation evidence is present. |
| `INST-02` | `01-01` | User can install Review Gate on default macOS without requiring GNU `timeout` or manual script patching. | ✓ SATISFIED | `run_with_timeout` provides `gtimeout` -> `timeout` -> python3 fallback and is used at both timeout call sites. `REQUIREMENTS.md` traceability still shows Pending, but implementation evidence is present. |
| `INST-03` | `01-02`, `01-03` | User can install Review Gate on Windows without losing unrelated MCP server entries in the user's MCP configuration. | ✓ SATISFIED | `update_mcp_config.py` merge/remove behavior passed temp-fixture tests and is wired into both Windows installers and both Windows uninstallers. |
| `INST-04` | `01-03`, `01-04` | User can install the current V2 rule and current VSIX artifact without following stale file names or wrong rule paths. | ✓ SATISFIED | Shipped VSIX files exist for `2.7.3`; installers and docs consistently reference `review-gate-v2-2.7.3.vsix` and `ReviewGateV2.mdc`. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| - | - | None in Phase 01 implementation artifacts after source scan and spot checks | - | No blocker or warning-level anti-patterns were found in the modified phase files. |

### Human Verification Required

### 1. macOS Install Smoke

**Test:** On a default macOS machine, create `~/.cursor/mcp.json` with at least one non-Review Gate server, then run `V2/install.sh` from a clean clone.
**Expected:** The install finishes without `>` shell parsing failures or missing `timeout` errors, preserves unrelated MCP servers, and installs the current VSIX plus `ReviewGateV2.mdc`.
**Why human:** This would modify the local machine, package manager state, and Cursor profile, and it depends on real macOS/Homebrew/Cursor behavior.

### 2. Windows PowerShell Install/Uninstall Smoke

**Test:** On Windows, seed `%USERPROFILE%\.cursor\mcp.json` with at least one unrelated server, run `V2/install.ps1`, then run `V2/uninstall.ps1`.
**Expected:** Install adds or updates only `review-gate-v2`; uninstall removes only `review-gate-v2`; other servers remain intact throughout.
**Why human:** Native PowerShell, Windows path handling, and live Cursor extension installation are not available in this session.

### 3. Windows Batch Install/Uninstall Smoke

**Test:** On Windows, seed `%USERPROFILE%\.cursor\mcp.json` with at least one unrelated server, run `V2/install.bat`, then run `V2/uninstall.bat`.
**Expected:** Install and uninstall preserve unrelated MCP servers while using the current `2.7.3` VSIX and `ReviewGateV2.mdc`.
**Why human:** Native cmd.exe, Windows path handling, and live Cursor extension installation are not available in this session.

### Gaps Summary

No automated implementation gaps were found. The current repo state satisfies the Phase 01 roadmap success criteria and the declared must-haves in `01-01` through `01-04`. Remaining uncertainty is limited to native installer smoke and live Cursor-side installation on supported platforms, so the correct verification status is `human_needed` rather than `passed`.

---

_Verified: 2026-04-02T19:36:06Z_
_Verifier: Claude (gsd-verifier)_

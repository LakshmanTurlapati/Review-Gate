---
phase: 01-installation-integrity
plan: "03"
subsystem: infra
tags: [cursor, installer, vsix, mcp, shell, powershell, batch]
requires:
  - phase: 01-01
    provides: POSIX installer and uninstaller baseline for current V2 distribution assets
  - phase: 01-02
    provides: Safe MCP config helper usage on Windows install and uninstall paths
provides:
  - Root-first VSIX resolution for the shipped `review-gate-v2-2.7.3.vsix` artifact across installers
  - Canonical `ReviewGateV2.mdc` install and uninstall handling on all supported platforms
  - Targeted POSIX MCP cleanup that preserves unrelated Cursor MCP servers during uninstall
affects: [01-04, installation-docs, release-packaging]
tech-stack:
  added: []
  patterns:
    - root-first VSIX artifact lookup with cursor-extension fallback
    - targeted MCP config mutation through update_mcp_config.py
    - canonical V2 rule filename usage across runtime scripts
key-files:
  created:
    - .planning/phases/01-installation-integrity/01-03-SUMMARY.md
  modified:
    - V2/install.sh
    - V2/install.ps1
    - V2/install.bat
    - V2/uninstall.sh
    - V2/uninstall.ps1
    - V2/uninstall.bat
key-decisions:
  - "Resolve installers against the shipped VSIX in V2/ first, then fall back to V2/cursor-extension/ while keeping the installed basename stable."
  - "Treat ReviewGateV2.mdc as the only supported V2 rule filename in install and uninstall scripts."
  - "Use update_mcp_config.py remove on POSIX uninstall so unrelated user MCP entries survive cleanup."
patterns-established:
  - "Installer artifact resolution: look for the committed VSIX in V2/ before using cursor-extension build output."
  - "Runtime script cleanup: remove only the Review Gate MCP entry instead of rewriting the full MCP config."
requirements-completed: [INST-03, INST-04]
duration: 2min
completed: 2026-04-02
---

# Phase 01 Plan 03: Installation Script Asset Alignment Summary

**Cross-platform runtime scripts now resolve the shipped 2.7.3 VSIX, install and remove ReviewGateV2.mdc, and preserve unrelated Cursor MCP config on POSIX uninstall**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-02T19:24:27Z
- **Completed:** 2026-04-02T19:26:28Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Normalized `install.sh`, `install.ps1`, and `install.bat` to resolve the current `review-gate-v2-2.7.3.vsix` from `V2/` first, then `V2/cursor-extension/`, and copy the selected file into the install directory under a stable basename.
- Replaced legacy `ReviewGate.mdc` references with `ReviewGateV2.mdc` across all platform install and uninstall scripts so the shipped V2 rule file is the only rule they install or remove.
- Updated `uninstall.sh` to call `update_mcp_config.py remove` with backup restore on failure instead of overwriting the entire Cursor MCP configuration.

## Task Commits

Each task was committed atomically:

1. **Task 1: Normalize installer VSIX lookup to the shipped 2.7.3 artifact set** - `0e4937a` (fix)
2. **Task 2: Replace legacy rule handling with `ReviewGateV2.mdc` everywhere** - `1bd323a` (fix)
3. **Task 3: Preserve unrelated MCP config during POSIX uninstall** - `8da997b` (fix)

## Files Created/Modified

- `V2/install.sh` - resolves the shipped VSIX in the required order, copies the stable basename, and reports `ReviewGateV2.mdc` in install output.
- `V2/install.ps1` - mirrors the shipped-VSIX resolution and `ReviewGateV2.mdc` install behavior for PowerShell installs.
- `V2/install.bat` - mirrors the shipped-VSIX resolution and `ReviewGateV2.mdc` install behavior for batch installs.
- `V2/uninstall.sh` - removes `ReviewGateV2.mdc` and uses `update_mcp_config.py remove` with backup restore on failure.
- `V2/uninstall.ps1` - removes `ReviewGateV2.mdc` and reports the exact rule path in uninstall output.
- `V2/uninstall.bat` - removes `ReviewGateV2.mdc` and reports the exact rule path in uninstall output.
- `.planning/phases/01-installation-integrity/01-03-SUMMARY.md` - records execution results, decisions, and verification for this plan.

## Decisions Made

- Installer VSIX resolution now prefers the committed root `V2/` artifact and only falls back to the `cursor-extension/` copy, which matches the shipped asset layout documented in `CLAUDE.md`.
- `ReviewGateV2.mdc` is now the canonical V2 rule filename across install and uninstall flows; the legacy root rule remains untouched outside these runtime scripts.
- POSIX uninstall now uses the same targeted MCP mutation approach already established on Windows so unrelated user MCP entries are preserved.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Task 1 verification checks required the literal shipped VSIX basename to appear in each installer, so the scripts keep an explicit `review-gate-v2-2.7.3.vsix` constant while still resolving the file from two supported locations.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 04 can update installation documentation against the now-correct runtime filenames and uninstall behavior without papering over script drift.
- No known blockers remain inside the owned install and uninstall scripts for this phase slice.

---
*Phase: 01-installation-integrity*
*Completed: 2026-04-02*

## Self-Check: PASSED

- Summary file exists at `.planning/phases/01-installation-integrity/01-03-SUMMARY.md`
- Task commits `0e4937a`, `1bd323a`, and `8da997b` are present in git history

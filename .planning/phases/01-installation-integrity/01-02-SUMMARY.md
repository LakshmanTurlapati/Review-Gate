---
phase: 01-installation-integrity
plan: "02"
subsystem: infra
tags: [windows, installer, uninstaller, mcp, cursor, powershell, batch, python]
requires: []
provides:
  - Shared MCP config merge and remove helper for Windows install flows
  - PowerShell installer/uninstaller paths that preserve unrelated Cursor MCP servers
  - Batch installer/uninstaller paths that preserve unrelated Cursor MCP servers
affects: [installation-integrity, session-routing-reliability, release-consistency]
tech-stack:
  added: []
  patterns:
    - Shared Python CLI for MCP config mutation from shell entrypoints
    - Backup then restore workflow around Windows MCP config changes
key-files:
  created:
    - V2/update_mcp_config.py
  modified:
    - V2/install.ps1
    - V2/install.bat
    - V2/uninstall.ps1
    - V2/uninstall.bat
key-decisions:
  - "Use one Python helper for merge/remove so both Windows shells preserve unrelated MCP server entries with the same JSON rules."
  - "Keep V2/mcp.json declarative and inject install-dir plus Python executable paths at helper runtime instead of hardcoding Windows-specific template paths."
patterns-established:
  - "Windows install and uninstall scripts back up Cursor MCP config before delegating mutation to update_mcp_config.py."
  - "Installer scripts avoid inline MCP JSON generation when a shared mutator can preserve user-owned entries."
requirements-completed: [INST-03]
duration: 3min
completed: 2026-04-02
---

# Phase 01 Plan 02: Windows MCP Config Preservation Summary

**Windows install and uninstall now merge or remove only the `review-gate-v2` MCP entry through a shared Python config mutator.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-02T19:16:50Z
- **Completed:** 2026-04-02T19:19:57Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Added `V2/update_mcp_config.py` with `merge` and `remove` commands that reject invalid JSON, preserve unrelated `mcpServers` entries, and write UTF-8 JSON atomically.
- Rewired `V2/install.ps1` and `V2/install.bat` to back up Cursor MCP config and call the shared merge helper instead of rewriting `mcp.json` inline.
- Rewired `V2/uninstall.ps1` and `V2/uninstall.bat` to remove only `review-gate-v2` and restore the backup if the shared helper fails.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create a shared MCP config merge/remove helper** - `a1c8554` (feat)
2. **Task 2: Wire Windows installers to the shared helper and fix PowerShell pip parsing** - `6ffcd34` (fix)
3. **Task 3: Wire Windows uninstallers to remove only the Review Gate entry** - `2e16c00` (fix)

## Files Created/Modified

- `V2/update_mcp_config.py` - Shared CLI for safe merge/remove mutation of Cursor MCP config.
- `V2/install.ps1` - PowerShell installer now calls the merge helper and quotes pip version specifiers.
- `V2/install.bat` - Batch installer now calls the merge helper and restores backup on failure.
- `V2/uninstall.ps1` - PowerShell uninstaller now calls the remove helper and restores backup on failure.
- `V2/uninstall.bat` - Batch uninstaller now calls the remove helper and restores backup on failure.
- `.planning/phases/01-installation-integrity/01-02-SUMMARY.md` - Captures Plan 02 execution details and verification results.

## Decisions Made

- Used a shared Python mutator instead of duplicating JSON merge logic in PowerShell and batch so Windows install and uninstall paths share one correctness boundary.
- Left the MCP template as the source of the Review Gate server definition and injected the resolved install directory and Python executable via CLI arguments.
- Left shared planning state files untouched in this parallel executor run to honor the ownership boundary on Phase 01 work.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Native Windows execution was not available in this environment, so verification here was limited to Python helper fixture coverage plus source-level checks on the PowerShell and batch scripts.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Windows scripts now preserve unrelated user-managed MCP servers, so later installation alignment work can build on a safe config mutation path.
- Native Windows smoke execution remains a follow-up validation concern for the broader installer verification phase.

## Self-Check

PASSED

---
*Phase: 01-installation-integrity*
*Completed: 2026-04-02*

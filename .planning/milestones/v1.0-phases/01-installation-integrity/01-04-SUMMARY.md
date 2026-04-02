---
phase: 01-installation-integrity
plan: "04"
subsystem: docs
tags: [cursor, mcp, vsix, installation, docs]
requires:
  - phase: 01-03
    provides: corrected V2 installer asset selection and MCP config preservation behavior
provides:
  - detailed installation instructions aligned to shipped V2 assets
  - README install guidance aligned to current V2 rule and MCP-preserving setup
affects: [01-installation-integrity, 05-canonical-release-surface]
tech-stack:
  added: []
  patterns:
    - Documentation points users to the shipped repo-root VSIX first and the cursor-extension build artifact second.
    - Manual MCP instructions preserve unrelated mcpServers entries while adding review-gate-v2.
key-files:
  created:
    - .planning/phases/01-installation-integrity/01-04-SUMMARY.md
  modified:
    - V2/INSTALLATION.md
    - readme.md
key-decisions:
  - "Used V2/review-gate-v2-2.7.3.vsix as the primary public artifact and V2/cursor-extension/review-gate-v2-2.7.3.vsix as the documented fallback."
  - "Documented MCP setup as merge-safe so manual instructions match the corrected installer behavior from Plan 03."
patterns-established:
  - "Doc pattern: keep user-facing artifact names aligned to committed V2 assets."
  - "Doc pattern: reference ReviewGateV2.mdc as the canonical V2 rule file in all current installation guidance."
requirements-completed: [INST-04]
duration: 3min
completed: 2026-04-02
---

# Phase 01 Plan 04: Installation Docs Alignment Summary

**V2 installation docs now point to the shipped 2.7.3 VSIX, the ReviewGateV2.mdc rule, and merge-safe MCP configuration updates**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-02T19:28:30Z
- **Completed:** 2026-04-02T19:31:41Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Updated `V2/INSTALLATION.md` to use `V2/review-gate-v2-2.7.3.vsix` as the primary VSIX, document `V2/cursor-extension/review-gate-v2-2.7.3.vsix` as the fallback, and replace stale manual install references.
- Added explicit `ReviewGateV2.mdc` rule instructions and merge-safe MCP guidance so manual setup preserves unrelated `mcpServers` entries.
- Aligned `readme.md` with the same shipped V2 install surface and preservation behavior described in the detailed guide.

## Task Commits

Each task was committed atomically:

1. **Task 1: Update the detailed installation guide to match shipped files and merge-safe config behavior** - `05409e3` (fix)
2. **Task 2: Update the top-level README installation section to match the corrected V2 flow** - `2835216` (fix)

## Files Created/Modified

- `V2/INSTALLATION.md` - Detailed V2 installation guide aligned to the shipped 2.7.3 VSIX, `ReviewGateV2.mdc`, and MCP-preserving setup.
- `readme.md` - Top-level installation section aligned to the same current V2 artifacts and configuration behavior.
- `.planning/phases/01-installation-integrity/01-04-SUMMARY.md` - Execution summary for Plan 01-04.

## Decisions Made

- Used the repo-root `V2/review-gate-v2-2.7.3.vsix` as the primary documented artifact because it matches the corrected installer lookup order.
- Kept the README focused on the same current V2 surface instead of expanding release-channel or marketplace guidance outside this phase.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Planning state files outside this summary were left untouched because execution ownership for this run limited planning changes to `.planning/phases/01-installation-integrity/01-04-SUMMARY.md`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 01 documentation now matches the corrected install and uninstall behavior from Plans 01-01 through 01-03.
- The next phase can assume the public install surface is `review-gate-v2-2.7.3.vsix`, `ReviewGateV2.mdc`, and MCP config preservation.

## Self-Check: PASSED

- Found `.planning/phases/01-installation-integrity/01-04-SUMMARY.md`
- Found commit `05409e3`
- Found commit `2835216`

---
phase: 04-automated-hardening-verification
plan: "03"
subsystem: testing
tags: [installers, smoke, unittest, node:test, argparse, regression]
requires:
  - phase: "04-01"
    provides: "Repo-local Python MCP regression coverage for the hardened server contract"
  - phase: "04-02"
    provides: "Repo-local Node extension regression coverage for popup and session routing behavior"
provides:
  - "A shared REVIEW_GATE_SMOKE installer contract that redirects config and install roots into temp paths without touching the maintainer workstation"
  - "Fixture-driven CLI coverage for update_mcp_config.py merge and remove behavior with POSIX and Windows-style path injection"
  - "A repo-root regression runner that executes the Phase 04 Python, Node, and installer suites in one fixed release-check command"
affects: [QUAL-03, release-consistency, phase-05-canonical-release-surface]
tech-stack:
  added: []
  patterns: [shared installer smoke env contract, unittest installer smoke harness, repo-root regression runner]
key-files:
  created: [tests/python/test_update_mcp_config.py, tests/smoke/test_installers.py, scripts/run_review_gate_regression_checks.py]
  modified: [V2/install.sh, V2/install.ps1, V2/install.bat]
key-decisions:
  - "Used one explicit REVIEW_GATE_SMOKE contract across all installers and defaulted skip gates in smoke mode so automated checks never touch real package managers, Cursor installs, or user profiles."
  - "Kept the new installer coverage in stdlib unittest and subprocess so the phase stayed low-friction and reused the shipped shell entrypoints directly."
  - "Made the repo-root runner invoke the already-established 04-01, 04-02, and 04-03 suites instead of creating a second disconnected verification path."
patterns-established:
  - "Installer smoke runs redirect HOME/USERPROFILE plus the install root through REVIEW_GATE_TEST_HOME and REVIEW_GATE_TEST_INSTALL_DIR while preserving the real copy and MCP-config mutation flow."
  - "Repo-root regression commands may provide suite-local environment such as PYTHONPATH when an existing test harness requires it, without changing production runtime code."
requirements-completed: [QUAL-03]
duration: 4min
completed: 2026-04-02
---

# Phase 4 Plan 03: Installer smoke mode and repo-root regression runner summary

**Shared installer smoke mode, update_mcp_config fixture coverage, and one repo-root command that runs the full Phase 4 regression set before release**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-02T21:56:59Z
- **Completed:** 2026-04-02T22:01:08Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Added the same smoke-mode contract to `V2/install.sh`, `V2/install.ps1`, and `V2/install.bat`, redirecting temp home and install roots while skipping dependency, extension-install, server-smoke, and interactive pause side effects in smoke runs.
- Added stdlib fixture coverage for `V2/update_mcp_config.py` plus installer smoke tests that validate copied assets, backup-file behavior, and merged MCP config contents in isolated temp roots.
- Added `scripts/run_review_gate_regression_checks.py` so maintainers can run the Phase 04 Python server suite, Node extension suite, and installer/config suite from one repo-root command.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add a shared non-destructive smoke-mode contract to all supported installers** - `d8181d5` (`fix`)
2. **Task 2: Add config-helper fixtures and installer smoke tests** - `d50b366` (`test`)
3. **Task 3: Add one repo-root release-check command that runs the full Phase 4 regression set** - `337dde9` (`feat`)

**Plan metadata:** Pending final docs commit created after summary/state updates

## Files Created/Modified

- `V2/install.sh` - Adds REVIEW_GATE_SMOKE path redirection plus skip gates for dependency installs, server smoke, and extension-install side effects on POSIX.
- `V2/install.ps1` - Mirrors the shared smoke contract for PowerShell, including temp profile redirection and cross-platform smoke execution under `pwsh`.
- `V2/install.bat` - Mirrors the shared smoke contract for batch, including smoke-safe pause suppression and redirected temp profile paths.
- `tests/python/test_update_mcp_config.py` - Exercises merge/remove CLI behavior, path injection, invalid JSON handling, and missing template-server failures.
- `tests/smoke/test_installers.py` - Runs installers in isolated temp roots, asserts copied runtime assets and merged MCP config, and skips unavailable Windows shells explicitly.
- `scripts/run_review_gate_regression_checks.py` - Lists and runs the Phase 04 Python, Node, and installer suites in one fixed order from the repo root.

## Decisions Made

- Reused the shipped installer scripts directly in smoke mode instead of introducing wrapper scripts or CI-only harness code.
- Treated the shared smoke env contract as the stable seam for both POSIX and Windows installers so the smoke suite can run the same high-level workflow everywhere.
- Kept the repo-root regression runner intentionally thin and delegated to the existing suite commands from 04-01, 04-02, and 04-03.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wired the Python loader path into the repo-root regression runner**
- **Found during:** Task 3 (Add one repo-root release-check command that runs the full Phase 4 regression set)
- **Issue:** The initial repo-root runner invoked `tests/python/test_review_gate_v2_mcp.py` without the `tests/python` import path that the existing Phase 04-01 harness expects, so `review_gate_test_loader` failed to import.
- **Fix:** Added suite-local `PYTHONPATH` handling for the Python suites and flushed suite header lines before subprocess output so the runner stays readable.
- **Files modified:** `scripts/run_review_gate_regression_checks.py`
- **Verification:** `python3 scripts/run_review_gate_regression_checks.py --list` and `python3 scripts/run_review_gate_regression_checks.py`
- **Committed in:** `337dde9`

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** The fix was required for the repo-root command to execute the already-shipped Python harness correctly. No scope creep.

## Issues Encountered

- The repository `.gitignore` ignores new `test_*` files, so `tests/python/test_update_mcp_config.py` and `tests/smoke/test_installers.py` had to be staged intentionally with `git add -f`.
- Windows smoke execution was not available in this environment because neither `pwsh`/`powershell.exe` nor `cmd.exe` is installed, so the smoke suite skipped those subtests explicitly while still proving the POSIX path end-to-end.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 04 is now complete: maintainers can run `python3 scripts/run_review_gate_regression_checks.py` to exercise the Python server, Node extension, and installer/config regressions together before release work.

Phase 05 can now focus on the canonical release surface and documentation knowing QUAL-03 has a concrete repo-root verification command behind it.

## Self-Check: PASSED

- Found `.planning/phases/04-automated-hardening-verification/04-03-SUMMARY.md`
- Found task commit `d8181d5`
- Found task commit `d50b366`
- Found task commit `337dde9`

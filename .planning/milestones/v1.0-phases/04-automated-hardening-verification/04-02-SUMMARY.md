---
phase: 04-automated-hardening-verification
plan: "02"
subsystem: testing
tags: [node:test, vscode-extension, regression, ipc, cursor]
requires:
  - phase: "02-02"
    provides: "Explicit busy and cancelled session outcomes plus attachment response envelopes for active popup sessions"
  - phase: "03-04"
    provides: "Authenticated initial trigger proof and runtime-scoped path validation for the extension IPC contract"
provides:
  - "A built-in Node loader that stubs the vscode host and fake webview panel state for extension runtime tests"
  - "A narrow __testHooks seam that resets singleton extension state without introducing a second runtime architecture"
  - "node:test regression coverage for signed trigger intake, busy routing, popup cancellation, and attachment response persistence"
affects: [QUAL-02, cursor-extension, automated-verification, release-consistency]
tech-stack:
  added: []
  patterns: [stubbed vscode loader, resettable extension test seam, node:test temp-session harness]
key-files:
  created: [tests/node/load-extension.js, tests/node/extension.runtime.test.js]
  modified: [V2/cursor-extension/extension.js]
key-decisions:
  - "Kept the production extension monolithic and exposed only a narrow __testHooks seam instead of adding rewire-style tooling or module splits."
  - "Ran the regression harness against real session files with a stubbed vscode surface so popup and IPC behavior stay close to production."
  - "Resolved runtime-path validation against realpaths so the existing hardening still works on macOS where /tmp resolves through a symlink."
patterns-established:
  - "Node extension tests load extension.js under a unique REVIEW_GATE_USER_ID and capture webview/output side effects through a fake vscode host."
  - "Extension session regressions assert busy/cancelled/attachment behavior through session files and fake webview messages rather than Cursor UI automation."
requirements-completed: [QUAL-02]
duration: 10 min
completed: 2026-04-02
---

# Phase 4 Plan 02: Built-in Node extension regression harness

**Built-in node:test coverage for authenticated trigger intake, busy and cancelled popup outcomes, and attachment response persistence in the shipped Cursor extension**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-02T21:37:30Z
- **Completed:** 2026-04-02T21:47:53Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added a resettable `__testHooks` seam in [`V2/cursor-extension/extension.js`](/Users/lakshmanturlapati/Documents/Codes/Review%20Gate/V2/cursor-extension/extension.js) so repo-local tests can drive the shipped extension helpers under a stubbed `vscode` module.
- Created [`tests/node/load-extension.js`](/Users/lakshmanturlapati/Documents/Codes/Review%20Gate/tests/node/load-extension.js) to fake panels, output channels, dialogs, and command registration using only built-in Node modules.
- Added [`tests/node/extension.runtime.test.js`](/Users/lakshmanturlapati/Documents/Codes/Review%20Gate/tests/node/extension.runtime.test.js) coverage for valid versus forged/stale trigger proof, busy session routing, popup cancellation, and uploaded image response writing.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add a minimal deterministic test seam to the single-file extension** - `68eaa14` (fix)
2. **Task 2: Add built-in Node tests for trigger proof intake, popup lifecycle, session routing, and attachment handling** - `6219b6d` (test)

**Plan metadata:** Pending final docs commit created after summary/state updates

## Files Created/Modified
- `V2/cursor-extension/extension.js` - Added the resettable `__testHooks` seam, tracked runtime timers for deterministic cleanup, and fixed symlink-safe runtime path validation discovered by the new tests.
- `tests/node/load-extension.js` - Loads the shipped extension under a stubbed `vscode` module with fake panels, output channels, and open-dialog behavior.
- `tests/node/extension.runtime.test.js` - Exercises signed trigger intake, busy-session handling, popup disposal, and attachment-backed response writing with `node:test`.

## Decisions Made

- Kept the seam narrow by exporting only the runtime helpers and reset logic the harness needs, rather than exposing internal UI state or introducing new production modules.
- Used a stubbed `vscode` host plus real temp-session files so the suite validates the hardened Phase 2 and Phase 3 contracts without needing Cursor automation.
- Fixed the temp-root validation bug in production once the harness proved that `/tmp` symlink resolution broke legitimate runtime paths on macOS.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Made runtime path validation symlink-safe for macOS /tmp**
- **Found during:** Task 2 (Add built-in Node tests for trigger proof intake, popup lifecycle, session routing, and attachment handling)
- **Issue:** `assertSafeRuntimePath(...)` compared `/tmp/...` session paths against the realpathed runtime root, so valid files were rejected as escaping the Review Gate runtime on macOS where `/tmp` resolves to `/private/tmp`.
- **Fix:** Validated the realpath-resolved chain target inside the runtime root while preserving the existing symlink rejection on actual runtime path components.
- **Files modified:** `V2/cursor-extension/extension.js`
- **Verification:** `node --check V2/cursor-extension/extension.js` and `node --test tests/node/*.test.js`
- **Committed in:** `6219b6d`

---

**Total deviations:** 1 auto-fixed (Rule 1: bug)
**Impact on plan:** The fix was required for the planned Node harness to execute against the hardened runtime on macOS. No scope creep.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 04-03 can build installer smoke checks and a repo-root release verification command on top of both Phase 04 regression harnesses.

The shipped extension’s popup and session contract now has repeatable repo-local coverage without adding a heavyweight JS test framework or real Cursor UI automation.

## Self-Check: PASSED

- Found `.planning/phases/04-automated-hardening-verification/04-02-SUMMARY.md`
- Found task commit `68eaa14`
- Found task commit `6219b6d`

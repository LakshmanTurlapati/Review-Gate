---
phase: 04-automated-hardening-verification
plan: "01"
subsystem: testing
tags: [python, unittest, mcp, ipc, regression]
requires:
  - phase: 02-session-routing-reliability
    provides: session-scoped trigger, acknowledgement, response, and recovery outcomes used by the shipped Python server
  - phase: 03-scoped-ipc-security
    provides: authenticated session envelopes, signed initial triggers, and runtime-path hardening
provides:
  - stdlib-only loader for importing `V2/review_gate_v2_mcp.py` without installed MCP or Faster-Whisper dependencies
  - isolated runtime-root and speech-monitor seams for Python-only server tests
  - regression coverage for signed trigger creation, acknowledgement outcomes, wrong-session cleanup, response matching, and timeout behavior
affects: [04-02-automated-extension-verification, release-consistency, QUAL-01]
tech-stack:
  added: []
  patterns: [stdlib-only import seam, isolated runtime-root patching, async session-file regression tests]
key-files:
  created: [tests/python/review_gate_test_loader.py, tests/python/test_review_gate_v2_mcp.py]
  modified: [tests/python/review_gate_test_loader.py]
key-decisions:
  - "Kept production code untouched and moved the import seam into `tests/python/review_gate_test_loader.py` with stubbed MCP and Whisper modules."
  - "Patched `get_temp_path()` only inside the loader's isolated runtime helper so macOS `/tmp` symlink validation does not force production-code changes."
  - "Drove coverage through real session files and `IsolatedAsyncioTestCase` instead of launching Cursor or mocking the server wait loops."
patterns-established:
  - "Python import seam: tests load `V2/review_gate_v2_mcp.py` only through `load_review_gate_module()`."
  - "Server regression pattern: each test gets a unique `REVIEW_GATE_USER_ID`, a private temp root, and a disabled speech monitor before instantiating `ReviewGateServer`."
requirements-completed: [QUAL-01]
duration: 3min
completed: 2026-04-02
---

# Phase 4 Plan 01: Automated Python verification for the hardened Review Gate server

**Stdlib-only Review Gate MCP regression harness covering signed triggers, authenticated session envelopes, and timeout cleanup without launching Cursor**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-02T21:42:27Z
- **Completed:** 2026-04-02T21:45:18Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added one supported stdlib-only import seam for `V2/review_gate_v2_mcp.py` that stubs MCP and Whisper modules, generates unique `REVIEW_GATE_USER_ID` values, and disables speech-monitor startup in tests.
- Added Python `unittest` coverage for signed trigger creation, acknowledgement success and recovery outcomes, wrong-session cleanup, attachment formatting, and timeout behavior.
- Proved the committed server contract from Phases 2 and 3 can be regression-tested locally without a real Cursor process, a real MCP install, or Faster-Whisper model downloads.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create a stdlib-only loader for importing the Review Gate server in tests** - `5434341` (`test`)
2. **Task 2: Add regression coverage for trigger proof, acknowledgement outcomes, response matching, and timeout cleanup** - `7fadd78` (`test`)

**Plan metadata:** Pending final docs commit created after summary/state updates

## Files Created/Modified
- `tests/python/review_gate_test_loader.py` - Stubs external Python dependencies, patches runtime isolation for tests, and disables background speech monitoring.
- `tests/python/test_review_gate_v2_mcp.py` - Exercises real session files against `_trigger_cursor_popup_immediately()`, `_wait_for_extension_acknowledgement()`, and `_wait_for_user_input()`.

## Decisions Made
- Kept all behavior changes in the test harness so the shipped server module stayed unchanged.
- Treated runtime-path hardening as part of the contract being tested; the harness moved tests to a private temp root instead of weakening the server validation.
- Used real JSON session envelopes and filesystem polling inside tests so the assertions match the production contract from Phases 2 and 3.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Patched the test runtime root away from macOS `/tmp` symlinks**
- **Found during:** Task 2 (Add regression coverage for trigger proof, acknowledgement outcomes, response matching, and timeout cleanup)
- **Issue:** `ReviewGateServer()` initialization failed under tests because runtime-path hardening rejects `/tmp` when it resolves through a symlink on this macOS environment.
- **Fix:** Added `isolated_review_gate_runtime()` to patch `get_temp_path()` to a private non-symlink temp root during tests.
- **Files modified:** `tests/python/review_gate_test_loader.py`, `tests/python/test_review_gate_v2_mcp.py`
- **Verification:** `python3 - <<'PY' ... load_review_gate_module() ... PY` and `python3 -m unittest discover -s tests/python -p 'test_review_gate_v2_mcp.py' -v`
- **Committed in:** `7fadd78`

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking)
**Impact on plan:** The fix stayed inside the harness and was necessary to execute the planned regression suite on the current macOS runtime. No production scope creep.

## Issues Encountered
- The repo `.gitignore` ignores `test_*`, so `tests/python/test_review_gate_v2_mcp.py` had to be staged intentionally with `git add -f`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase `04-02` can reuse the Python loader and session-file testing pattern for additional runtime verification without adding heavyweight tooling.
- QUAL-01 now has repeatable repo-local Python coverage for the hardened server contract before release work continues.

## Self-Check: PASSED

- Found `.planning/phases/04-automated-hardening-verification/04-01-SUMMARY.md`
- Found task commit `5434341`
- Found task commit `7fadd78`

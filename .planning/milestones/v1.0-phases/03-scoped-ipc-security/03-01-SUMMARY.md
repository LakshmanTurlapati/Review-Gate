---
phase: 03-scoped-ipc-security
plan: "01"
subsystem: infra
tags: [cursor, mcp, ipc, security, temp-files, vscode-extension, python]
requires:
  - phase: 02-session-routing-reliability
    provides: session-scoped trigger, acknowledgement, response, busy, cancel, and speech ownership flow from Phase 2
provides:
  - per-user Review Gate runtime roots under `review-gate-v2/<user>/` shared by the Python server and Cursor extension
  - session-owned IPC, speech, and audio artifacts under `sessions/<trigger_id>/` with stale directory sweeps
  - whole-session cleanup after terminal MCP outcomes and manual-popup cleanup without the shared temp audit log
affects: [03-02-PLAN.md, 03-03-PLAN.md, 04-automated-hardening-verification, SEC-01]
tech-stack:
  added: []
  patterns: [per-user runtime root, session-directory IPC, whole-session cleanup]
key-files:
  created: [.planning/phases/03-scoped-ipc-security/03-01-SUMMARY.md]
  modified: [V2/review_gate_v2_mcp.py, V2/cursor-extension/extension.js]
key-decisions:
  - "Kept the Phase 2 filename contract intact while relocating active artifacts into `review-gate-v2/<user>/sessions/<trigger_id>/`."
  - "Made whole-session directory cleanup the terminal cleanup unit, with the Python server owning MCP-session teardown and the extension owning manual-session and stale-session cleanup."
  - "Removed shared temp user-input audit logging instead of relocating it, while keeping MCP liveness checks on a runtime-local `review_gate_v2.log`."
patterns-established:
  - "Runtime root pattern: both runtimes derive the same sanitized per-user temp subtree before creating session files."
  - "Session cleanup pattern: stale sweeps and terminal outcomes delete entire session directories rather than unlinking individual IPC files."
requirements-completed: [SEC-01]
duration: 5min
completed: 2026-04-02
---

# Phase 3 Plan 01: Scoped IPC Security Summary

**Per-user runtime roots with session-owned trigger, response, speech, and audio artifacts under `review-gate-v2/<user>/sessions/<trigger_id>/`**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-02T20:32:31Z
- **Completed:** 2026-04-02T20:37:51Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Added matching per-user runtime-root helpers in the Python MCP server and Cursor extension, while preserving the Phase 2 trigger, acknowledgement, response, and speech filename contract.
- Refactored the Python server to sweep stale session directories, clean up whole MCP sessions after terminal outcomes, and keep active IPC files under the session subtree.
- Refactored the extension to discover triggers under the runtime subtree, keep speech JSON and audio files in the owning session directory, and stop writing raw user input to `review_gate_user_inputs.log`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Introduce one per-user Review Gate runtime root and per-session directory contract in both runtimes** - `9fc4254` (`chore`)
2. **Task 2: Refactor the Python MCP server around session directories and whole-session cleanup** - `8205a80` (`fix`)
3. **Task 3: Refactor the extension to keep attachments, speech artifacts, and response files inside the owning session directory** - `b8f3349` (`fix`)

## Files Created/Modified
- `V2/review_gate_v2_mcp.py` - Added the shared per-user runtime root, session-directory helpers, whole-session cleanup, and stale directory sweeps for MCP-side IPC and speech handling.
- `V2/cursor-extension/extension.js` - Added the matching runtime-root and session-directory helpers, trigger discovery under `sessions/*/`, session-owned audio paths, manual-session cleanup, and removed shared temp user-input logging.
- `.planning/phases/03-scoped-ipc-security/03-01-SUMMARY.md` - Captures plan execution details, decisions, verification, and completion metadata for Plan 03-01.

## Decisions Made
- Preserved the public `review_gate_chat` tool surface, Phase 2 busy/cancel semantics, and single-popup UX by changing only the storage layout, not the transport or popup ownership model.
- Kept runtime status monitoring file-based, but moved the watched `review_gate_v2.log` into the per-user runtime root so trigger discovery and MCP liveness use the same storage subtree.
- Let the server own terminal cleanup for MCP-managed sessions so response or cancellation envelopes remain readable long enough for the MCP caller to consume them.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Verification

- `python3 -m py_compile V2/review_gate_v2_mcp.py`
- `node --check V2/cursor-extension/extension.js`
- `rg -n 'get_runtime_root|_session_dir|_session_glob|getRuntimeRoot|getSessionDir|listPendingTriggerFiles|processPendingTriggers' V2/review_gate_v2_mcp.py V2/cursor-extension/extension.js`
- `! rg -n 'review_gate_user_inputs\.log' V2/cursor-extension/extension.js`
- Source confirmation: active trigger, acknowledgement, response, speech, and audio artifacts now resolve under the shared `review-gate-v2/<user>/sessions/<trigger_id>/` runtime subtree.

## Next Phase Readiness

- Ready for `03-02-PLAN.md` to add authenticated envelope validation and atomic write policy on top of the new runtime-root and session-directory contract.
- `03-03-PLAN.md` can now harden webview assets and DOM safety without also having to reason about broad temp-root IPC exposure.

## Self-Check: PASSED

- Found summary file: `.planning/phases/03-scoped-ipc-security/03-01-SUMMARY.md`
- Found task commits: `9fc4254`, `8205a80`, `b8f3349`

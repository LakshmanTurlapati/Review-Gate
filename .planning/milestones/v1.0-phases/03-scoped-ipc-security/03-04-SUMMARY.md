---
phase: 03-scoped-ipc-security
plan: "04"
subsystem: infra
tags: [ipc, security, cursor, mcp, tempfile]
requires:
  - phase: "03-02"
    provides: "Authenticated session envelopes, atomic JSON IPC writes, and status heartbeat metadata shared by the MCP server and extension"
  - phase: "03-03"
    provides: "The hardened single-file popup flow that the new initial-trigger gate now protects"
provides:
  - "Redacted runtime diagnostics that keep prompt text, response text, and attachment metadata out of stderr and the Cursor output channel"
  - "Runtime-secret-backed HMAC proof on initial MCP trigger envelopes before the extension accepts a new session"
  - "Heartbeat pid, server-state, and freshness checks that preserve existing busy, cancel, timeout, and success flows after proof succeeds"
affects: [SEC-01, SEC-02, 04-automated-verification, cursor-extension, mcp-server]
tech-stack:
  added: []
  patterns: [redacted runtime diagnostics, HMAC-authenticated trigger envelopes, heartbeat-backed trigger validation]
key-files:
  created: []
  modified: [V2/review_gate_v2_mcp.py, V2/cursor-extension/extension.js]
key-decisions:
  - "Kept the Phase 2/03-02 session envelope contract intact and added proof only to the initial trigger so busy, cancel, timeout, and response handling did not need a new transport."
  - "Bound trigger acceptance to both a runtime-secret HMAC and the live review_gate_status.json pid/server_state so stale trigger files are rejected before the popup claims MCP ownership."
  - "Normalized remaining diagnostics down to trigger ids, counts, and status metadata instead of removing operational logging entirely."
patterns-established:
  - "Initial-trigger proof contract: trigger_signature plus trigger_issued_at ride on the top-level trigger envelope and are verified before handleReviewGateToolCall(...) runs."
  - "Redaction contract: extension output and Python stderr keep only trigger ids, counts, and lifecycle states while user payloads stay inside per-session files and popup UI."
requirements-completed: [SEC-01, SEC-02]
duration: 10 min
completed: 2026-04-02
---

# Phase 3 Plan 04: Redacted diagnostics and authenticated initial MCP trigger intake

**Redacted Review Gate runtime diagnostics and added runtime-secret HMAC proof so the extension rejects stale or forged first triggers before claiming a new MCP popup session**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-02T21:10:00Z
- **Completed:** 2026-04-02T21:19:58Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Removed the remaining extension output-channel and Python stderr leakage of prompt bodies, response text, attachment names, selected-file lists, and attachment metadata.
- Added a runtime-owned `review_gate_runtime_secret` and signed initial trigger envelopes with `trigger_signature` plus `trigger_issued_at`.
- Required the extension to validate trigger freshness, HMAC proof, and live heartbeat pid/server_state before it can open the popup or claim `activeMcpSession`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove the remaining non-session diagnostic leakage from the server and extension** - `0f047f1` (fix)
2. **Task 2: Require live server-backed proof before the extension accepts a new MCP trigger** - `df54a47` (fix)

**Plan metadata:** Pending final docs commit created after summary/state updates

## Files Created/Modified
- `V2/review_gate_v2_mcp.py` - Redacted remaining stderr diagnostics, created the runtime secret helper, and signed initial trigger envelopes with HMAC proof metadata.
- `V2/cursor-extension/extension.js` - Removed residual output-channel leakage and added runtime-secret, freshness, and heartbeat validation before new MCP popup sessions are accepted.

## Decisions Made

- Kept the temp-file transport and existing Phase 2/03-02 session envelope contract unchanged after the initial trigger is accepted, because the verification gap was only at first-trigger trust.
- Used the existing `review_gate_status.json` heartbeat as the live liveness source for trigger pid and state validation instead of inventing a new coordination file.
- Required `trigger_issued_at` to match the signed top-level trigger timestamp so the freshness window is bound to signed data instead of an unsigned side field.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Restored silent offline heartbeat polling after the shared status reader refactor**
- **Found during:** Task 2 (Require live server-backed proof before the extension accepts a new MCP trigger)
- **Issue:** Reusing the stricter heartbeat reader in `checkMcpStatus()` would have logged a missing-heartbeat error every poll when the MCP server was simply offline.
- **Fix:** Kept the shared validated heartbeat reader for proof checks, but restored the old silent `status file missing => inactive` path inside `checkMcpStatus()`.
- **Files modified:** `V2/cursor-extension/extension.js`
- **Verification:** `node --check V2/cursor-extension/extension.js` plus the full plan verification suite passed after the silent-offline branch was restored.
- **Committed in:** `df54a47`

---

**Total deviations:** 1 auto-fixed (Rule 1: bug)
**Impact on plan:** The fix preserved the pre-existing offline semantics while keeping the new trigger-proof gate intact. No scope creep.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 3’s remaining verifier gaps are closed: diagnostics stay redacted and the extension now rejects stale or forged initial triggers before mutating MCP popup state.

Phase 4 can add automated regression coverage around the proof payload, freshness window, heartbeat validation, and redacted logging behavior without changing the runtime contract again.

## Self-Check: PASSED

- Found `.planning/phases/03-scoped-ipc-security/03-04-SUMMARY.md`
- Found task commit `0f047f1`
- Found task commit `df54a47`

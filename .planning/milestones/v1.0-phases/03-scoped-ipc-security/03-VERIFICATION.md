---
phase: 03-scoped-ipc-security
verified: 2026-04-02T21:26:25Z
status: human_needed
score: 3/3 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 1/3
  gaps_closed:
    - "User feedback, attachment metadata, and speech transcripts are written only to scoped per-session locations and cleaned up after handoff."
    - "Review Gate rejects malformed or unauthenticated local IPC messages without altering the active session state."
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Live Cursor round-trip with image and speech"
    expected: "Popup renders under the hardened CSP, image upload and speech transcription still work, response returns to Cursor, and the session directory is removed after handoff."
    why_human: "Requires the live Cursor extension host, webview runtime, SoX, microphone permissions, and real filesystem timing."
  - test: "Forged and stale IPC rejection"
    expected: "Forged or stale trigger files are rejected before popup state changes, and malformed or wrong-session ack/response/speech envelopes are ignored without taking over the active session."
    why_human: "Requires concurrent local-process interaction against the live extension and server loop."
---

# Phase 3: Scoped IPC Security Verification Report

**Phase Goal:** Local Review Gate IPC protects sensitive user data and rejects untrusted messages by default.
**Verified:** 2026-04-02T21:26:25Z
**Status:** human_needed
**Re-verification:** Yes - after 03-04 gap closure

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | User feedback, attachment metadata, and speech transcripts are written only to scoped per-session locations and cleaned up after handoff. | ✓ VERIFIED | Both runtimes derive trigger, acknowledgement, response, speech, and audio paths from `review-gate-v2/<user>/sessions/<trigger_id>/...`; whole-session cleanup is implemented in `_cleanup_session_directory(...)` and `cleanupSessionDirectory(...)`; the old shared temp logs are gone; extension-side `logUserInput(...)` now emits only counts and trigger IDs. |
| 2 | Review Gate rejects malformed or unauthenticated local IPC messages without altering the active session state. | ✓ VERIFIED | Initial trigger intake now requires `trigger_signature`, `trigger_issued_at`, runtime-secret HMAC validation, freshness, and a live `review_gate_status.json` pid/server-state match before `handleReviewGateToolCall(...)` or `activeMcpSession` can be reached; follow-up acknowledgement, response, and speech envelopes are still validated by `session_token` and `protocol_version`. |
| 3 | The popup interface loads required assets locally and avoids unsafe HTML injection patterns. | ✓ VERIFIED | The webview uses a nonce CSP, extension-owned SVG data URIs, serialized popup config, `createElement(...)`, `textContent`, and explicit event listeners. No CDN, `innerHTML`, or inline `onclick` path remains. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `V2/review_gate_v2_mcp.py` | Session-scoped storage, cleanup, authenticated envelopes, runtime-secret trigger proof, redacted heartbeat/status writes | ✓ VERIFIED | `get_runtime_root`, `_session_file`, `_cleanup_session_directory`, `_validate_session_envelope`, `_load_runtime_secret`, `_build_initial_trigger_signature`, `_trigger_cursor_popup_immediately`, and `_write_status_heartbeat` are implemented and wired. |
| `V2/cursor-extension/extension.js` | Matching session-scoped storage, cleanup, authenticated trigger intake, redacted diagnostics, strict popup hardening | ✓ VERIFIED | `getRuntimeRoot`, `getSessionFilePath`, `writeJsonAtomically`, `validateSessionEnvelope`, `validateInitialTriggerEnvelope`, `processTriggerFile`, `logUserInput`, `checkMcpStatus`, and the hardened webview HTML are implemented and wired. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `V2/review_gate_v2_mcp.py` | `V2/cursor-extension/extension.js` | Shared runtime root and session-directory contract | ✓ WIRED | Manual verification: `_session_file(...)` and `getSessionFilePath(...)` both resolve under `review-gate-v2/<user>/sessions/<trigger_id>/...`. `gsd-tools` reported a helper-based false negative for `03-01-PLAN.md`. |
| `V2/review_gate_v2_mcp.py` | `V2/cursor-extension/extension.js` | Session-token and protocol-version envelope validation for ack, response, and speech IPC | ✓ WIRED | `gsd-tools verify key-links` passed for `03-04-PLAN.md`, and both runtimes enforce `protocol_version` plus `session_token` before consuming follow-up envelopes. |
| `V2/review_gate_v2_mcp.py` | `V2/cursor-extension/extension.js` | Initial trigger proof before popup/session mutation | ✓ WIRED | `processTriggerFile(...)` validates the envelope, then calls `validateInitialTriggerEnvelope(...)`, and only afterwards can `handleReviewGateToolCall(...)` open the popup. Static ordering check passed. |
| `V2/review_gate_v2_mcp.py` | `V2/cursor-extension/extension.js` | Redacted heartbeat/status surface for MCP liveness | ✓ WIRED | Manual verification: `_write_status_heartbeat(...)` writes `review_gate_status.json`, and `checkMcpStatus()` reads that file through `readMcpStatusHeartbeat()`. `gsd-tools` reported a constant-based false negative for `03-02-PLAN.md`. |
| `V2/cursor-extension/extension.js` | Cursor webview runtime | Nonce CSP, local assets, and DOM-safe rendering | ✓ WIRED | `gsd-tools verify key-links` passed for `03-03-PLAN.md`: CSP, local SVG data URIs, and DOM node construction are present in the shipped popup. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `V2/review_gate_v2_mcp.py` | `user_input`, `_last_attachments` | `_wait_for_user_input()` reads `review_gate_response_<trigger_id>.json` via `_read_json_file()` and `_validate_session_envelope()` | Yes | ✓ FLOWING |
| `V2/review_gate_v2_mcp.py` | `transcription` | `_process_speech_request()` transcribes the session audio file and writes `review_gate_speech_response_<trigger_id>.json` | Yes | ✓ FLOWING |
| `V2/cursor-extension/extension.js` | `validatedTriggerData`, `activeMcpSession` | `processTriggerFile()` reads the session-scoped trigger, validates HMAC plus heartbeat, then opens the popup | Yes | ✓ FLOWING |
| `V2/cursor-extension/extension.js` | Popup message and image preview nodes | Serialized popup config plus DOM construction in `addMessage(...)` and `createImagePreviewNode(...)` | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Python server parses after Phase 3 hardening | `python3 -m py_compile V2/review_gate_v2_mcp.py` | Command succeeded | ✓ PASS |
| Cursor extension parses after Phase 3 hardening | `node --check V2/cursor-extension/extension.js` | Command succeeded | ✓ PASS |
| 03-04 artifact contract exists and is substantive | `node .../gsd-tools.cjs verify artifacts .planning/phases/03-scoped-ipc-security/03-04-PLAN.md` | `2/2` artifacts passed | ✓ PASS |
| 03-04 key links for initial-trigger proof and redacted diagnostics are wired | `node .../gsd-tools.cjs verify key-links .planning/phases/03-scoped-ipc-security/03-04-PLAN.md` | `3/3` links verified | ✓ PASS |
| Trigger proof gate precedes popup state changes | `python3 - <<'PY' ... processTriggerFile ordering assertion ... PY` | `validateInitialTriggerEnvelope(...)` occurs before `handleReviewGateToolCall(...)` and before `activeMcpSession` assignment | ✓ PASS |
| Redacted extension logging avoids payload content | `python3 - <<'PY' ... logUserInput assertion ... PY` | Counts-only logging confirmed; no raw input text, attachment filenames, or MIME types in `logUserInput(...)` | ✓ PASS |
| Popup hardening contract is intact | `node .../gsd-tools.cjs verify key-links .planning/phases/03-scoped-ipc-security/03-03-PLAN.md` | `3/3` links verified | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| SEC-01 | `03-01-PLAN.md`, `03-02-PLAN.md`, `03-04-PLAN.md` | User feedback, attachment metadata, and speech transcripts are stored only in scoped per-session locations and cleaned up after handoff. | ✓ SATISFIED | Session files and audio live under the runtime-owned session subtree; shared temp logs were removed; redacted diagnostics emit counts rather than payload text; whole-session cleanup remains wired in both runtimes. |
| SEC-02 | `03-02-PLAN.md`, `03-04-PLAN.md` | Review Gate rejects unauthenticated or malformed local IPC messages from other local processes. | ✓ SATISFIED | Initial triggers now require runtime-secret HMAC proof, freshness, and live-heartbeat pid/state checks before popup/session mutation; follow-up ack, response, and speech envelopes remain token-validated and path-safe. |
| SEC-03 | `03-03-PLAN.md` | The popup UI loads its assets without requiring external CDNs or unsafe HTML injection patterns. | ✓ SATISFIED | CSP, nonce-scoped script, local SVG data URIs, serialized config, and DOM-safe rendering are present; CDN and `innerHTML` checks passed. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `V2/review_gate_v2_mcp.py` | - | None blocking SEC-01/SEC-02/SEC-03 | - | No stub, placeholder, or unsafe fallback pattern remains in the phase-modified runtime file. |
| `V2/cursor-extension/extension.js` | - | None blocking SEC-01/SEC-02/SEC-03 | - | No blocker-level placeholder, CDN dependency, or unsafe HTML assembly pattern remains in the phase-modified runtime file. |

### Human Verification Required

### 1. Live Cursor Round-Trip With Image And Speech

**Test:** Start Cursor with the installed extension and MCP server, trigger `review_gate_chat`, attach an image, record a short speech sample, and submit the response.
**Expected:** The popup renders under the nonce CSP, image upload and speech transcription still work, the response returns to Cursor, and the session directory under `review-gate-v2/<user>/sessions/<trigger_id>/` is removed after handoff.
**Why human:** Requires the live Cursor extension host, webview runtime, SoX, microphone permissions, and real filesystem timing.

### 2. Forged And Stale IPC Rejection

**Test:** While one Review Gate session is active, write a forged or stale trigger file plus malformed or wrong-session acknowledgement, response, and speech envelopes into the runtime tree from a second local process.
**Expected:** The extension rejects the forged or stale trigger before popup takeover, ignores malformed follow-up envelopes, and leaves the active session unchanged.
**Why human:** Requires concurrent local-process interaction against the live extension and server loop.

### Residual Risk

Automated verification now supports SEC-01, SEC-02, and SEC-03. The remaining risk is operational rather than structural: live Cursor/SoX behavior is still untested in this turn, and the initial-trigger proof relies on a per-user runtime secret plus heartbeat metadata rather than OS-isolated credential storage. That means the phase now rejects malformed and unauthenticated IPC by default, but it does not attempt to solve full same-user local compromise.

---

_Verified: 2026-04-02T21:26:25Z_
_Verifier: Claude (gsd-verifier)_

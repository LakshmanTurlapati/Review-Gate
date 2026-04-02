---
phase: 03-scoped-ipc-security
verified: 2026-04-02T21:07:16Z
status: gaps_found
score: 1/3 must-haves verified
gaps:
  - truth: "User feedback, attachment metadata, and speech transcripts are written only to scoped per-session locations and cleaned up after handoff."
    status: partial
    reason: "Active IPC files are session-scoped and cleaned, but attachment metadata and prompt-related text still reach non-session diagnostic surfaces in the extension output channel and Python stderr."
    artifacts:
      - path: "V2/cursor-extension/extension.js"
        issue: "Attachment filename, size, MIME type, and image IDs are still logged through logUserInput for paste, drag-drop, and remove events."
      - path: "V2/review_gate_v2_mcp.py"
        issue: "Prompt text, file-review instructions, and attachment filenames are still logged to stderr in several handlers."
    missing:
      - "Stop logging prompt text and attachment metadata outside the session directory lifecycle."
      - "Reduce diagnostics to trigger ids, status transitions, counts, and file basenames only where strictly needed."
  - truth: "Review Gate rejects malformed or unauthenticated local IPC messages without altering the active session state."
    status: partial
    reason: "Acknowledgement, response, and speech envelopes are validated against an active session contract, but initial trigger acceptance only checks schema, path, and a non-empty session_token."
    artifacts:
      - path: "V2/cursor-extension/extension.js"
        issue: "processTriggerFile accepts a new trigger before the extension has any independently authenticated session contract for that trigger."
    missing:
      - "Authenticate the initial trigger origin beyond shape and runtime-path validation, or narrow the stated trust boundary to same-user local processes and update the requirement accordingly."
---

# Phase 3: Scoped IPC Security Verification Report

**Phase Goal:** Local Review Gate IPC protects sensitive user data and rejects untrusted messages by default.
**Verified:** 2026-04-02T21:07:16Z
**Status:** gaps_found
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | User feedback, attachment metadata, and speech transcripts are written only to scoped per-session locations and cleaned up after handoff. | ✗ FAILED | Session files and audio now live under `review-gate-v2/<user>/sessions/<trigger_id>/` and are cleaned up by whole-session removal in both runtimes, but attachment metadata and prompt text still escape to non-session diagnostics in `V2/cursor-extension/extension.js` and `V2/review_gate_v2_mcp.py`. |
| 2 | Review Gate rejects malformed or unauthenticated local IPC messages without altering the active session state. | ✗ FAILED | Follow-up acknowledgement, response, and speech envelopes are contract-validated, but new trigger acceptance in the extension is only schema/path validated. Inference from code: the extension has no independently known secret or server identity check before opening a popup for a new trigger. |
| 3 | The popup interface loads required assets locally and avoids unsafe HTML injection patterns. | ✓ VERIFIED | The webview uses a nonce-based CSP, inline SVG data URIs for icons, serialized config, and DOM-safe rendering helpers without `innerHTML` or CDN references. |

**Score:** 1/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `V2/review_gate_v2_mcp.py` | Per-session runtime root, cleanup, envelope validation, atomic JSON writes, redacted status heartbeat | ✓ VERIFIED | `get_runtime_root`, `_session_file`, `_cleanup_session_directory`, `_validate_session_envelope`, `_write_json_atomically`, and `review_gate_status.json` heartbeat are implemented and used. |
| `V2/cursor-extension/extension.js` | Matching runtime helpers, cleanup, envelope validation, atomic writes, status-file monitoring, strict popup hardening | ✓ VERIFIED | `getRuntimeRoot`, `getSessionDir`, `cleanupSessionDirectory`, `validateSessionEnvelope`, `writeJsonAtomically`, `checkMcpStatus`, strict CSP, local SVG assets, and DOM-safe preview rendering are implemented and wired. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `V2/review_gate_v2_mcp.py` | `V2/cursor-extension/extension.js` | Shared runtime root and session directory contract | ✓ WIRED | Both runtimes derive paths from `review-gate-v2/<user>/sessions/<trigger_id>/...`; the helper-based implementation caused a false negative in the regex-based `gsd-tools` key-link check. |
| `V2/review_gate_v2_mcp.py` | `V2/cursor-extension/extension.js` | `protocol_version` and `session_token` on acknowledgement, response, and speech envelopes | ✓ WIRED | Follow-up envelopes are validated before acknowledgement, response, and speech state changes on both sides. |
| `V2/review_gate_v2_mcp.py` | `V2/cursor-extension/extension.js` | Initial trigger acceptance | ⚠️ PARTIAL | The extension validates trigger shape, runtime path, source, system, and editor, but it does not authenticate initial trigger origin beyond those checks. |
| `V2/review_gate_v2_mcp.py` | `V2/cursor-extension/extension.js` | `review_gate_status.json` heartbeat | ✓ WIRED | The server writes redacted heartbeat JSON and the extension reads it for liveness; the filename constant caused a false negative in the regex-based `gsd-tools` key-link check. |
| `V2/cursor-extension/extension.js` | Cursor webview runtime | Nonce CSP, local assets, and DOM-safe rendering | ✓ WIRED | The webview HTML, icons, and image previews are rendered through the hardened CSP and DOM APIs. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `V2/review_gate_v2_mcp.py` | `user_input`, `_last_attachments` | `_wait_for_user_input()` reads `review_gate_response_<trigger_id>.json` via `_read_json_file()` and `_validate_session_envelope()` | Yes | ✓ FLOWING |
| `V2/review_gate_v2_mcp.py` | `transcription` | `_process_speech_request()` transcribes the session audio file and writes `review_gate_speech_response_<trigger_id>.json` | Yes | ✓ FLOWING |
| `V2/cursor-extension/extension.js` | `triggerData`, `activeMcpSession` | `listPendingTriggerFiles()` and `processTriggerFile()` read session-scoped trigger JSON from the runtime root | Yes | ✓ FLOWING |
| `V2/cursor-extension/extension.js` | Popup content and image preview nodes | Serialized popup config plus DOM node construction in the webview script | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Python server parses after Phase 3 changes | `python3 -m py_compile V2/review_gate_v2_mcp.py` | Command succeeded | ✓ PASS |
| Cursor extension parses after Phase 3 changes | `node --check V2/cursor-extension/extension.js` | Command succeeded | ✓ PASS |
| Popup hardening is present in source | `node - <<'NODE' ... NODE` static assertion for CSP, nonce, no CDN, no `innerHTML`, DOM-safe preview | All checks returned `true` | ✓ PASS |
| Python IPC hardening helpers are present in source | `python3 - <<'PY' ... PY` static assertion for runtime root, session cleanup, envelope validation, atomic write, status file | All checks returned `True` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| SEC-01 | `03-01-PLAN.md`, `03-02-PLAN.md` | User feedback, attachment metadata, and speech transcripts are stored only in scoped per-session locations and cleaned up after handoff. | ✗ BLOCKED | Session-scoped IPC and cleanup are implemented, but attachment metadata and prompt-related text are still logged outside the session subtree in extension output-channel diagnostics and Python stderr. |
| SEC-02 | `03-02-PLAN.md` | Review Gate rejects unauthenticated or malformed local IPC messages from other local processes. | ✗ BLOCKED | Malformed and mismatched follow-up envelopes are rejected, but initial trigger acceptance is not independently authenticated before popup state changes. This is an inference from the extension's trigger-validation flow. |
| SEC-03 | `03-03-PLAN.md` | The popup UI loads its assets without requiring external CDNs or unsafe HTML injection patterns. | ✓ SATISFIED | The popup uses nonce-based CSP, local inline SVG icon assets, serialized config, `createElement`, and `textContent`, with no `innerHTML` or CDN dependency found. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `V2/cursor-extension/extension.js` | 1302 | Output-channel logging of pasted image filename, size, and MIME type | 🛑 Blocker | Stores attachment metadata outside the scoped session directory and cleanup path. |
| `V2/cursor-extension/extension.js` | 1305 | Output-channel logging of drag-drop image filename, size, and MIME type | 🛑 Blocker | Same storage-boundary leak as above. |
| `V2/review_gate_v2_mcp.py` | 877 | Stderr logging of quick-review prompt text | ⚠️ Warning | Keeps prompt content in a non-session diagnostic surface. |
| `V2/review_gate_v2_mcp.py` | 921 | Stderr logging of file-review instruction text | ⚠️ Warning | Keeps prompt content in a non-session diagnostic surface. |
| `V2/review_gate_v2_mcp.py` | 797 | Stderr logging of attachment filename when returning image content | ⚠️ Warning | Keeps attachment metadata in a non-session diagnostic surface. |

### Human Verification Required

Minimum UAT is still required even after the automated review because this phase changes live Cursor popup behavior, speech flow, and concurrent local IPC behavior.

### 1. Live MCP Round-Trip With Image And Speech

**Test:** Launch Cursor with the extension and MCP server, trigger `review_gate_chat`, attach an image, record a short speech sample, and submit the response.
**Expected:** The popup renders correctly under the hardened CSP, the response returns to Cursor, and the session directory under `review-gate-v2/<user>/sessions/<trigger_id>/` is removed after handoff.
**Why human:** Requires the live Cursor extension host, webview, SoX/microphone, and real filesystem timing.

### 2. Injection-Rejection Spot Check

**Test:** While one Review Gate session is active, write malformed and wrong-token acknowledgement, response, and speech JSON files into that session directory, then try a forged trigger from a second local process.
**Expected:** Malformed and wrong-token follow-up envelopes are ignored without changing the active session; forged-trigger behavior should confirm the intended same-user trust boundary before SEC-02 is signed off.
**Why human:** Requires concurrent local-process interaction against the live extension loop.

### Gaps Summary

Phase 3 materially improves Review Gate: active IPC is session-scoped, whole-session cleanup exists, follow-up IPC envelopes are token-validated, JSON writes are atomic, the status surface is redacted, and the popup no longer depends on CDN assets or unsafe HTML rendering.

The phase still does not satisfy SEC-01 and SEC-02 as written. Sensitive metadata and prompt text still escape to non-session diagnostic surfaces, and initial trigger acceptance is only path/schema checked rather than independently authenticated. SEC-03 is satisfied automatically from code inspection and spot-checks.

---

_Verified: 2026-04-02T21:07:16Z_
_Verifier: Claude (gsd-verifier)_

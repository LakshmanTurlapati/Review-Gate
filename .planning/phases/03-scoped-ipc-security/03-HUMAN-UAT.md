---
status: partial
phase: 03-scoped-ipc-security
source: [03-VERIFICATION.md]
started: 2026-04-02T21:26:25Z
updated: 2026-04-02T21:26:25Z
---

## Current Test

Awaiting live Cursor validation for the hardened popup runtime, image or speech round-trip, and forged or stale IPC rejection.

## Tests

### 1. Live Cursor round-trip with image and speech
expected: popup renders under the hardened CSP, image upload and speech transcription still work, response returns to Cursor, and the per-session runtime directory is removed after handoff.
result: pending

### 2. Forged and stale IPC rejection
expected: forged or stale trigger files are rejected before popup takeover, and malformed or wrong-session acknowledgement, response, and speech envelopes do not alter the active session.
result: pending

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps

None yet.

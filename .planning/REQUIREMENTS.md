# Requirements: Review Gate

**Defined:** 2026-04-02
**Core Value:** Keep the human and agent in the same working loop until the human says the task is complete.

## v1 Requirements

### Installation

- [ ] **INST-01**: User can run the macOS/Linux installer without shell parsing failures from dependency version specifiers.
- [ ] **INST-02**: User can install Review Gate on default macOS without requiring GNU `timeout` or manual script patching.
- [x] **INST-03**: User can install Review Gate on Windows without losing unrelated MCP server entries in the user's MCP configuration.
- [x] **INST-04**: User can install the current V2 rule and current VSIX artifact without following stale file names or wrong rule paths.

### Session Reliability

- [x] **SESS-01**: User can complete a Review Gate popup round-trip without another in-flight session overwriting the active trigger or response state.
- [x] **SESS-02**: User receives responses only for the active Review Gate session, without generic fallback files leaking stale or unrelated input.
- [x] **SESS-03**: User gets clear recovery behavior for timed-out or failed popup interactions instead of silent stalls.

### Privacy and Security

- [x] **SEC-01**: User feedback, attachment metadata, and speech transcripts are stored only in scoped per-session locations and cleaned up after handoff.
- [x] **SEC-02**: Review Gate rejects unauthenticated or malformed local IPC messages from other local processes.
- [ ] **SEC-03**: The popup UI loads its assets without requiring external CDNs or unsafe HTML injection patterns.

### Verification and Release

- [ ] **QUAL-01**: Maintainer can run automated tests for the Python server's trigger, acknowledgement, response, and timeout behavior.
- [ ] **QUAL-02**: Maintainer can run automated tests for the Cursor extension's popup lifecycle, session routing, and attachment handling.
- [ ] **QUAL-03**: Maintainer can run repeatable smoke checks for supported installers and confirm MCP configuration merge behavior.
- [ ] **REL-01**: Maintainer can produce one canonical VSIX artifact and documentation that matches the shipped version and supported rule file.

## v2 Requirements

### Product Expansion

- **TOOL-01**: Cursor can access additional Review Gate MCP tools beyond `review_gate_chat` when those tools are intentionally supported and tested.
- **UX-01**: User can manage multiple Review Gate conversations or queued review sessions safely.
- **DIST-01**: User can install Review Gate through a reproducible package or marketplace release channel instead of manual artifact handling.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Hosted Review Gate backend | Current product value is local-first and does not require remote infrastructure |
| Non-Cursor editor support | The existing runtime is tightly coupled to Cursor/VS Code APIs and Cursor rule behavior |
| Net-new creative UX surfaces beyond the popup loop | Current milestone is focused on hardening existing V2 behavior first |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INST-01 | Phase 1 | Pending |
| INST-02 | Phase 1 | Pending |
| INST-03 | Phase 1 | Complete |
| INST-04 | Phase 1 | Complete |
| SESS-01 | Phase 2 | Complete |
| SESS-02 | Phase 2 | Complete |
| SESS-03 | Phase 2 | Complete |
| SEC-01 | Phase 3 | Complete |
| SEC-02 | Phase 3 | Complete |
| SEC-03 | Phase 3 | Pending |
| QUAL-01 | Phase 4 | Pending |
| QUAL-02 | Phase 4 | Pending |
| QUAL-03 | Phase 4 | Pending |
| REL-01 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-02*
*Last updated: 2026-04-02 after Phase 3 Plan 01*

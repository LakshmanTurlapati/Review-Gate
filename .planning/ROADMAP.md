# Roadmap: Review Gate

## Overview

This brownfield roadmap hardens the shipped Review Gate V2 loop in the order most likely to reduce user-facing breakage: correct installation first, then deterministic session handling, then scoped local IPC security, then automated verification, and finally a canonical release surface that keeps artifacts and documentation aligned with what is actually supported.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Installation Integrity** - Make cross-platform installation use current assets and preserve existing user configuration.
- [x] **Phase 2: Session Routing Reliability** - Ensure the active Review Gate request owns its trigger, response, and recovery path.
- [x] **Phase 3: Scoped IPC Security** - Restrict local IPC and transient storage to authenticated, per-session behavior.
- [ ] **Phase 4: Automated Hardening Verification** - Add repeatable automated checks across server, extension, and installer flows.
- [ ] **Phase 5: Canonical Release Surface** - Make shipped artifacts and docs match one supported runtime path.

## Phase Details

### Phase 1: Installation Integrity
**Goal**: Users can install the current Review Gate V2 safely on supported platforms without breaking existing Cursor MCP configuration.
**Depends on**: Nothing (first phase)
**Requirements**: INST-01, INST-02, INST-03, INST-04
**Success Criteria** (what must be TRUE):
  1. User can run the macOS/Linux installer without shell parsing failures caused by dependency version specifiers.
  2. User can install on default macOS without needing GNU `timeout` or manual script edits.
  3. User can install on Windows without unrelated MCP server entries being removed from the user's Cursor MCP configuration.
  4. User installs the current V2 rule and current VSIX artifact from filenames and paths that match the shipped repository contents.
**Plans**: TBD

### Phase 2: Session Routing Reliability
**Goal**: Users can complete Review Gate popup round-trips without concurrent or stale sessions corrupting the active exchange.
**Depends on**: Phase 1
**Requirements**: SESS-01, SESS-02, SESS-03
**Success Criteria** (what must be TRUE):
  1. User can complete a popup round-trip without another in-flight session overwriting the active trigger or response state.
  2. User receives responses only for the active Review Gate session, with no stale or unrelated fallback-file content leaking into the exchange.
  3. User gets a clear timeout or failure recovery path when popup handoff fails instead of a silent stall.
**Plans**: 2 plans
Plans:
- [x] 02-01-PLAN.md - Make the temp-file protocol strictly session-scoped and remove generic or backup routing paths from the active MCP flow.
- [x] 02-02-PLAN.md - Add explicit busy, timeout, cancel, and stale-cleanup recovery so one popup session cannot silently corrupt another.

### Phase 3: Scoped IPC Security
**Goal**: Local Review Gate IPC protects sensitive user data and rejects untrusted messages by default.
**Depends on**: Phase 2
**Requirements**: SEC-01, SEC-02, SEC-03
**Success Criteria** (what must be TRUE):
  1. User feedback, attachment metadata, and speech transcripts are written only to scoped per-session locations and cleaned up after handoff.
  2. Review Gate rejects malformed or unauthenticated local IPC messages without altering the active session state.
  3. The popup interface loads required assets locally and avoids unsafe HTML injection patterns.
**Plans**: 4 plans
Plans:
- [x] 03-01-PLAN.md - Move active IPC, attachment, and speech artifacts into Review Gate-owned per-session runtime directories with whole-session cleanup.
- [x] 03-02-PLAN.md - Require authenticated envelope validation, atomic JSON writes, and redacted status or log surfaces for the active IPC path.
- [x] 03-03-PLAN.md - Harden the popup webview with local assets, strict CSP, and DOM-safe rendering paths.
- [x] 03-04-PLAN.md - Close the verification blockers by redacting residual diagnostics and requiring live server-backed proof before the extension accepts a new MCP trigger.
**UI hint**: yes

### Phase 4: Automated Hardening Verification
**Goal**: Maintainers can run automated regression checks for the shipped Review Gate runtime before release.
**Depends on**: Phase 3
**Requirements**: QUAL-01, QUAL-02, QUAL-03
**Success Criteria** (what must be TRUE):
  1. Maintainer can run automated tests for Python server trigger creation, acknowledgement handling, response matching, and timeout behavior.
  2. Maintainer can run automated tests for Cursor extension popup lifecycle, session routing, and attachment handling.
  3. Maintainer can run repeatable smoke checks for supported installers, including MCP configuration merge behavior.
**Plans**: TBD

### Phase 5: Canonical Release Surface
**Goal**: Maintainers can ship one authoritative Review Gate release whose docs and artifacts match the actual supported runtime.
**Depends on**: Phase 4
**Requirements**: REL-01
**Success Criteria** (what must be TRUE):
  1. Maintainer can produce or identify one canonical VSIX artifact for the shipped version without duplicate committed alternatives.
  2. Installation and release docs reference the shipped version, supported runtime surface, and correct V2 rule file.
  3. Users and maintainers no longer need to guess which artifact, version string, or rule path is supported for release.
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Installation Integrity | 4/4 | Complete | 2026-04-02 |
| 2. Session Routing Reliability | 2/2 | Complete | 2026-04-02 |
| 3. Scoped IPC Security | 4/4 | Complete | 2026-04-02 |
| 4. Automated Hardening Verification | 0/TBD | Not started | - |
| 5. Canonical Release Surface | 0/TBD | Not started | - |

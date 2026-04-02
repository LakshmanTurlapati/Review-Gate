# Review Gate

## What This Is

Review Gate is a local-first companion for Cursor IDE that keeps an AI task open until the human explicitly completes it. V2 pairs a Cursor rule, a Python MCP server, and a Cursor extension popup so users can continue an in-progress request with text, images, and optional voice input instead of starting a new request each time.

## Core Value

Keep the human and agent in the same working loop until the human says the task is complete.

## Current State

Review Gate v1.0 shipped on 2026-04-02. The shipped V2 path now has corrected cross-platform installers, deterministic popup session routing, scoped authenticated local IPC, repo-root regression coverage, and a manifest-backed canonical release surface rooted at `V2/review-gate-v2-2.7.3.vsix`.

## Next Milestone Goals

- Close the deferred native macOS and Windows installer smoke checks captured during Phase 1.
- Run the deferred live Cursor popup and security UAT from Phases 2 and 3.
- Decide whether the next milestone continues stabilization or starts product-expansion work such as additional tools, safer multi-session UX, or a reproducible distribution channel.

## Requirements

### Validated

- ✓ User can open the Review Gate popup manually inside Cursor with a command and keyboard shortcut. - existing
- ✓ Cursor can call the `review_gate_chat` MCP tool and receive popup feedback through the local MCP server. - existing
- ✓ User can send text and image feedback through the V2 popup, and the server returns that context to Cursor. - existing
- ✓ Speech-to-text is supported on local setups with SoX and Faster-Whisper available. - existing
- ✓ Installers and uninstallers exist for macOS/Linux/Windows, along with MCP config and rule setup docs. - existing
- ✓ Windows install and uninstall preserve unrelated Cursor MCP server entries while updating only `review-gate-v2`. - validated in Phase 1
- ✓ Runtime scripts and user-facing docs now point to the current V2 rule file and 2.7.3 VSIX artifact set. - validated in Phase 1
- ✓ Active MCP popup exchanges now use session-scoped trigger, acknowledgement, and response files instead of shared fallback routes. - validated in Phase 2
- ✓ Overlapping or abandoned popup sessions now return explicit busy, cancelled, or timeout outcomes instead of silently rebinding the active exchange. - validated in Phase 2
- ✓ Active IPC, speech, and audio artifacts now live under Review Gate-owned per-session runtime directories with whole-session cleanup. - validated in Phase 3
- ✓ Initial trigger intake now requires runtime-secret proof, authenticated follow-up envelopes, and popup rendering without external assets or unsafe HTML assembly. - validated in Phase 3
- ✓ Maintainers can now run automated Python server, Node extension, and installer/config regression suites from the repo root before release. - validated in Phase 4
- ✓ Release metadata, installers, docs, and regression checks now align on one canonical Review Gate V2 artifact path and supported rule file. - validated in Phase 5

### Active

- [ ] Complete native macOS and Windows install smoke validation for the corrected Phase 1 installer flows.
- [ ] Complete live Cursor popup validation for the new Phase 2 busy/cancel/timeout routing behavior.
- [ ] Complete live Cursor security validation for the hardened Phase 3 image, speech, and forged-IPC rejection flows.

### Out of Scope

- Hosted or cloud-backed Review Gate services - current product is explicitly local-first and workstation-scoped.
- Non-Cursor editor integrations - the current runtime, docs, and rules are built around Cursor/VS Code extension APIs.
- Major net-new UX surfaces beyond the existing popup loop - current priority is reliability and maintainability of the shipped V2 experience.

## Context

- The repository contains two generations of the product: the original terminal-driven rule in `ReviewGate.mdc` and the MCP-based V2 implementation under `V2/`.
- V2 is implemented as a monolithic Python MCP server in `V2/review_gate_v2_mcp.py`, a monolithic Cursor extension host/webview in `V2/cursor-extension/extension.js`, and platform-specific install/uninstall scripts in `V2/install.*` and `V2/uninstall.*`.
- v1.0 closed the original hardening roadmap: installer/runtime correctness issues are addressed, automated regression coverage exists, and the duplicate committed VSIX surface has been removed.
- The next milestone can build on a verified release baseline instead of continuing basic stabilization work in the critical V2 path.

## Constraints

- **Platform**: Must keep working on macOS, Windows, and Linux - the repo already ships platform-specific install paths and markets cross-platform support.
- **Runtime**: Must integrate with Cursor IDE and MCP over local processes - the product value depends on the Cursor rule + extension + MCP loop.
- **Architecture**: Remains local-first with no backend or auth layer - current workflows rely on local files, local audio capture, and local transcription.
- **Dependencies**: Voice support depends on SoX, Python, and Faster-Whisper - installer and UX changes must degrade cleanly when speech prerequisites are missing.
- **Security**: User prompts, attachments, and transcripts can contain sensitive local data - IPC and logging changes must reduce exposure in shared temp locations.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Treat Review Gate V2 as the primary product surface | The repo and README position V2 as the recommended path, while V1 is legacy compatibility | - Pending |
| Use brownfield initialization with validated existing capabilities | The codebase already ships end-to-end functionality that should be preserved instead of modeled as greenfield ideas | - Pending |
| Prioritize hardening, verification, and release hygiene before new feature expansion | The codebase map surfaced installer bugs, protocol fragility, and zero automated regression coverage | - Pending |
| Standardize installers on `ReviewGateV2.mdc`, `review-gate-v2-2.7.3.vsix`, and targeted MCP config mutation | Phase 1 needed one consistent supported runtime surface before session hardening work could safely build on it | ✓ Good |
| Standardize active popup routing on trigger-scoped temp files with explicit busy and cancel outcomes | Phase 2 needed deterministic session ownership before security hardening or test automation could be trusted | ✓ Good |
| Harden local IPC in layers: scoped runtime directories first, authenticated envelopes second, popup CSP and DOM safety third, then a final proof gate for initial triggers | Phase 3 needed to close both storage exposure and trust-boundary gaps without replacing the transport or redesigning the extension | ✓ Good |
| Keep verification low-friction with stdlib Python, built-in Node test tooling, and smoke-mode installers instead of adopting heavyweight test infrastructure first | Phase 4 needed repeatable coverage that matches the current repo and can run immediately on developer machines | ✓ Good |
| Centralize release metadata in `V2/release-manifest.json` and treat `V2/review-gate-v2-2.7.3.vsix` as the only supported shipped artifact | Phase 5 needed to eliminate duplicate release surfaces before the milestone could be considered shippable | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `$gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-02 after v1.0 milestone*

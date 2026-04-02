# AGENTS

This repository's generated project guide lives in `CLAUDE.md`.

Use `CLAUDE.md` as the primary reference for:
- project context
- stack and architecture notes
- GSD workflow expectations

## Project

**Review Gate**

Review Gate is a local-first companion for Cursor IDE that keeps an AI task open until the human explicitly completes it. The current roadmap treats V2 as the primary product surface and focuses on installation correctness, session reliability, IPC security, automated verification, and release consistency.

## Workflow

Before making file changes, start work through a GSD command so planning artifacts and execution context stay in sync.

Preferred entry points:
- `/gsd:quick` for small fixes and docs work
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

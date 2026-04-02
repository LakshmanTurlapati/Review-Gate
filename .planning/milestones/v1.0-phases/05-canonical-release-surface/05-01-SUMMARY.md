---
phase: 05-canonical-release-surface
plan: "01"
subsystem: release
tags: [release, packaging, manifest, vsix]
requires:
  - phase: "04-03"
    provides: "One repo-root regression entrypoint and smoke-mode installer contract ready for release-surface narrowing"
provides:
  - "A repo-owned release manifest that defines the version, canonical VSIX path, supported rule file, and extension source directory in one place"
  - "A canonical Python packaging helper that validates manifest drift and packages the extension into `V2/` instead of the extension workspace"
  - "A root-only committed VSIX surface with generated `V2/cursor-extension/*.vsix` outputs kept untracked"
affects: [REL-01, installers, docs, packaging]
tech-stack:
  added: [json, zipfile, argparse, subprocess]
  patterns: [manifest-driven packaging, canonical root artifact, generated-workspace ignore rule]
key-files:
  created: [V2/release-manifest.json, scripts/package_review_gate_vsix.py]
  modified: [V2/cursor-extension/package.json, .gitignore]
key-decisions:
  - "Made `V2/release-manifest.json` the single repo-owned source of truth for Review Gate release metadata."
  - "Kept `npm run package` rooted in `V2/cursor-extension/` for maintainer ergonomics, but delegated the actual packaging path to the repo-level Python helper."
  - "Removed the committed workspace VSIX entirely so `V2/cursor-extension/` stays a build workspace rather than a second release surface."
patterns-established:
  - "Release metadata flows through `scripts/package_review_gate_vsix.py --field ...` for downstream scripts instead of hardcoded filenames."
  - "Canonical packaging writes only to `V2/review-gate-v2-<version>.vsix`."
requirements-completed: [REL-01]
duration: 1 session
completed: 2026-04-02
---

# Phase 5 Plan 01: Canonical release manifest and single packaging path

**Established one manifest-backed release contract, rewired packaging to it, and removed the duplicate committed workspace VSIX.**

## Accomplishments

- Added `V2/release-manifest.json` as the only repo-owned definition of version, canonical VSIX path, rule path, and extension source directory.
- Added `scripts/package_review_gate_vsix.py` so maintainers can print manifest fields, validate drift with `--check`, and package the extension back into `V2/`.
- Replaced the direct `vsce package` script with a manifest-backed `npm run package` path and removed the duplicate committed `V2/cursor-extension/review-gate-v2-2.7.3.vsix`.

## Task Commits

1. **Task 1: Create the canonical release manifest and packaging helper** - `037faa2` (`feat`)
2. **Task 2: Remove the duplicate committed workspace VSIX and keep it untracked** - `7eda60a` (`chore`)

## Files Created/Modified

- `V2/release-manifest.json` - Single source of truth for version, artifact basename, canonical VSIX path, rule path, and extension source directory.
- `scripts/package_review_gate_vsix.py` - Manifest helper that supports `--field`, `--check`, and canonical packaging into `V2/`.
- `V2/cursor-extension/package.json` - Delegates `npm run package` and `npm run package:check` to the canonical helper.
- `.gitignore` - Keeps generated `V2/cursor-extension/*.vsix` outputs untracked.
- `V2/cursor-extension/review-gate-v2-2.7.3.vsix` - Deleted so the workspace no longer exposes a second committed release artifact.

## Verification

- `python3 scripts/package_review_gate_vsix.py --check`
- `python3 scripts/package_review_gate_vsix.py --field canonical_vsix_path`
- `test ! -e V2/cursor-extension/review-gate-v2-2.7.3.vsix`
- `git check-ignore -q --no-index V2/cursor-extension/review-gate-v2-2.7.3.vsix`

## Next Phase Readiness

The installers can now consume one manifest-driven contract instead of repeating version strings, VSIX basenames, and rule names independently.

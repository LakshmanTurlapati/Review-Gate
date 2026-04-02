---
phase: 05-canonical-release-surface
plan: "03"
subsystem: docs-and-testing
tags: [docs, regression, release, runner]
requires:
  - phase: "05-01"
    provides: "Canonical release manifest and helper-backed packaging contract"
  - phase: "05-02"
    provides: "Installers and smoke coverage already narrowed to the root-only artifact"
provides:
  - "Public docs that point to one canonical artifact path, one supported rule file, and one packaging command"
  - "A dedicated release-surface regression suite covering manifest, docs, installers, and packaged VSIX metadata"
  - "A repo-root regression runner that includes release-surface validation by default"
affects: [REL-01, docs, regression-runner]
tech-stack:
  added: [unittest, zipfile]
  patterns: [release-surface regression suite, manifest-to-doc parity checks, default repo-root release validation]
key-files:
  created: [tests/python/test_release_surface.py]
  modified: [V2/INSTALLATION.md, readme.md, scripts/run_review_gate_regression_checks.py]
key-decisions:
  - "Kept the existing repo-root runner as the single release-check entrypoint and extended it rather than creating a second release script."
  - "Made the release-surface suite assert both positive alignment and negative absence of the deleted workspace VSIX path."
patterns-established:
  - "Release guidance must mention the manifest helper and canonical root artifact together so docs cannot drift away from the supported packaging contract."
requirements-completed: [REL-01]
duration: 1 session
completed: 2026-04-02
---

# Phase 5 Plan 03: Canonical release docs and final regression gate

**Aligned public release guidance to the canonical artifact story and added a release-surface regression suite to the existing repo-root runner.**

## Accomplishments

- Updated `V2/INSTALLATION.md` and `readme.md` so both documents describe one authoritative VSIX path, one supported rule file, and the manifest-backed packaging command.
- Added `tests/python/test_release_surface.py` to verify manifest/package metadata alignment, root-VSIX presence, duplicate-workspace-VSIX absence, installer references, and doc references.
- Extended `scripts/run_review_gate_regression_checks.py` so `release-surface` is a first-class suite and part of the default full run.

## Task Commits

1. **Task 1: Align public release guidance and expose the release runner suite** - `206be96` (`docs`)
2. **Task 2: Add dedicated release-surface regression coverage** - `21f05d4` (`test`)

## Files Created/Modified

- `V2/INSTALLATION.md` - Canonical install and maintainer packaging guidance for the root artifact.
- `readme.md` - Public release story aligned to the same canonical artifact and rule path.
- `scripts/run_review_gate_regression_checks.py` - Adds `release-surface` to the default repo-root regression run.
- `tests/python/test_release_surface.py` - End-to-end release-surface assertions for manifest, VSIX, installers, and docs.

## Verification

- `python3 -m unittest tests/python/test_release_surface.py -v`
- `python3 scripts/run_review_gate_regression_checks.py --suite release-surface`
- `python3 scripts/run_review_gate_regression_checks.py`

## Next Phase Readiness

Phase 5 closes the milestone by making the shipped artifact, installer contract, documentation, and regression entrypoint agree on one supported Review Gate release surface.

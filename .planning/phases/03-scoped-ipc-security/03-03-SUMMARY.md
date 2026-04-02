---
phase: 03-scoped-ipc-security
plan: "03"
subsystem: ui
tags: [webview, csp, vscode-extension, security]
requires:
  - phase: "03-02"
    provides: "Authenticated session envelopes and runtime-scoped IPC paths for the popup handoff"
provides:
  - "Strict nonce-based CSP for the Review Gate popup webview"
  - "Extension-owned inline SVG icon assets with no CDN dependency"
  - "DOM-safe image preview rendering for popup attachments"
affects: [04-automated-verification, popup-ui, release-consistency]
tech-stack:
  added: []
  patterns: [nonce-based webview CSP, inline SVG data URI icon masks, DOM-safe rendering helpers]
key-files:
  created: []
  modified: [V2/cursor-extension/extension.js]
key-decisions:
  - "Kept the popup in the existing single-file extension structure and hardened it in place to minimize release risk."
  - "Serialized popup config once into the nonce-allowed script and applied dynamic values through DOM-safe APIs instead of raw HTML interpolation."
patterns-established:
  - "Webview scripts receive host state through serialized config objects rather than direct string interpolation in markup."
  - "Popup controls and affordance icons use extension-owned inline SVG assets so the webview works without external asset hosts."
requirements-completed: [SEC-03]
duration: 10 min
completed: 2026-04-02
---

# Phase 3 Plan 03: Popup CSP and DOM-safe Review Gate webview

**Review Gate’s popup now runs under a nonce-based CSP, ships its own inline SVG icons, and renders attachment previews through DOM APIs instead of HTML injection**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-02T20:52:00Z
- **Completed:** 2026-04-02T21:02:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added a strict `Content-Security-Policy` meta tag that uses `webview.cspSource` for styles and images plus a generated script nonce for the popup runtime.
- Removed the Font Awesome CDN dependency and replaced popup icons and drag-drop affordances with extension-owned inline SVG data assets.
- Reworked attachment preview rendering so filenames, buttons, and image metadata are built with `createElement`, `textContent`, and explicit event listeners.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add a strict webview CSP and remove external asset loading from the popup HTML** - `50141ff` (fix)
2. **Task 2: Replace unsafe HTML assembly with DOM-safe rendering helpers** - `9c4ce45` (fix)

Plan metadata was committed separately after summary/state updates.

## Files Created/Modified
- `V2/cursor-extension/extension.js` - Hardened the popup webview HTML generation, CSP, icon assets, and attachment preview rendering.

## Decisions Made

- Kept the popup in `V2/cursor-extension/extension.js` instead of introducing new modules because the plan explicitly favored the lowest-risk single-file hardening path.
- Used CSS mask-based inline SVG data URIs for icon rendering so the popup preserves the existing look without requiring a local asset pipeline or external stylesheet.
- Applied popup title, labels, and placeholder state from serialized script config so user-controlled strings do not get injected directly into the initial HTML markup.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Rejected non-image data URLs before preview rendering**
- **Found during:** Task 2 (Replace unsafe HTML assembly with DOM-safe rendering helpers)
- **Issue:** Moving preview rendering to DOM APIs still left a path where malformed or unexpected `data:` payloads could be assigned to the preview image source.
- **Fix:** Added `isSafeImageDataUrl(...)` and only render previews when the payload matches an `image/*` base64 data URL.
- **Files modified:** `V2/cursor-extension/extension.js`
- **Verification:** `node --check V2/cursor-extension/extension.js` plus the final DOM-safety grep suite passed with the validator in place.
- **Committed in:** `9c4ce45`

---

**Total deviations:** 1 auto-fixed (Rule 2: missing critical functionality)
**Impact on plan:** The extra validation tightened the same SEC-03 surface without expanding scope or changing popup UX.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 3’s remaining popup trust gaps are closed: the webview now loads only extension-owned assets, enforces a strict CSP, and avoids dynamic HTML injection paths for attachment previews.

Phase 4 can build automated verification around the hardened popup surface without needing to account for CDN reachability or `innerHTML`-based rendering behavior. Live Cursor popup UAT remains the only external confirmation still tracked outside this plan.

## Self-Check: PASSED

- Found `.planning/phases/03-scoped-ipc-security/03-03-SUMMARY.md`
- Found task commit `50141ff`
- Found task commit `9c4ce45`

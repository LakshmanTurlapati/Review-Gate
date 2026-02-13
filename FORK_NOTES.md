# Review Gate Fork - Enhancements

Fork of [Review Gate V2](https://github.com/LakshmanTurlapati/Review-Gate) with multi-window routing, AI message display, and trigger deduplication fixes.

## Changes (v2.8.0)

### 1. Multi-Window Routing Fix (NEW)

**Problem:** When multiple Cursor IDE windows are open, each extension instance polls the same `/tmp/review_gate_trigger.json` file. Whichever window polls first "wins" and shows the popup — often the wrong window.

**Solution:** Workspace-scoped trigger file routing using MD5 hash of the workspace path.

- MCP server (`review_gate_v2_mcp.py`): Hashes `os.getcwd()` to generate a `workspace_id`. Writes trigger files to `review_gate_trigger_{workspace_id}.json` (plus generic fallback for backward compat).
- Extension (`extension.js`): Hashes `vscode.workspace.workspaceFolders[0]` path with the same algorithm. Polls for workspace-scoped trigger files first, and validates `workspace_id` on generic trigger files.
- Result: Each Cursor window only picks up triggers from its own MCP server.

### 2. AI Message Display Fix

**Problem:** AI messages from MCP `review_gate_chat` tool calls were not displayed in the popup — only user responses were visible.

**Root Cause:** The `case 'ready'` block suppressed messages when `mcpIntegration` was true.

**Fix:**
- Always display messages when present
- New `'ai'` message type with robot emoji and blue styling
- Distinct visual appearance from user and system messages

### 3. Single Session Panel

- All Review Gate interactions go to one panel (stable `getChatId()`)
- No more spawning of multiple popup windows per session

### 4. Trigger Deduplication

- `processedTriggerIds` Set tracks processed trigger IDs
- Prevents duplicate popups from backup trigger files
- Auto-evicts old IDs after 60 seconds

## Files Changed

| File | Changes |
|------|---------|
| `V2/review_gate_v2_mcp.py` | Workspace ID generation, scoped trigger files |
| `V2/cursor-extension/extension.js` | Workspace-scoped polling, AI messages, dedup |
| `V2/cursor-extension/package.json` | Version bump to 2.8.0 |
| `FORK_NOTES.md` | This documentation |

## Installation

```bash
cd V2/cursor-extension
# Install the pre-built VSIX:
code --install-extension review-gate-v2-2.8.0.vsix
```

## Original Project

- Repository: https://github.com/LakshmanTurlapati/Review-Gate
- Author: Lakshman Turlapati
- License: MIT

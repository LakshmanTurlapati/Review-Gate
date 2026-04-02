#!/bin/bash

# Review Gate V2 - Uninstaller Script
# Author: Lakshman Turlapati

set -e

# Enhanced colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
WHITE='\033[1;37m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Enhanced logging functions
log_error() { echo -e "${RED}ERROR: $1${NC}"; }
log_success() { echo -e "${GREEN}SUCCESS: $1${NC}"; }
log_info() { echo -e "${YELLOW}INFO: $1${NC}"; }
log_progress() { echo -e "${CYAN}PROGRESS: $1${NC}"; }
log_warning() { echo -e "${YELLOW}WARNING: $1${NC}"; }
log_step() { echo -e "${WHITE}$1${NC}"; }
log_header() { echo -e "${BLUE}$1${NC}"; }

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

log_header "Review Gate V2 - Uninstaller"
log_header "============================="
echo ""

read -p "$(echo -e ${YELLOW}WARNING: Are you sure you want to uninstall Review Gate V2? [y/N]: ${NC})" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "Uninstallation cancelled"
    exit 0
fi

log_progress "Removing Review Gate V2..."

# Remove installation directory
REVIEW_GATE_DIR="$HOME/cursor-extensions/review-gate-v2"
if [[ -d "$REVIEW_GATE_DIR" ]]; then
    rm -rf "$REVIEW_GATE_DIR"
    log_success "Removed installation directory"
fi

# Remove MCP configuration
CURSOR_MCP_FILE="$HOME/.cursor/mcp.json"
if [[ -f "$CURSOR_MCP_FILE" ]]; then
    # Create backup
    MCP_BACKUP_FILE="$CURSOR_MCP_FILE.backup"
    cp "$CURSOR_MCP_FILE" "$MCP_BACKUP_FILE"

    if python3 "$SCRIPT_DIR/update_mcp_config.py" remove --config "$CURSOR_MCP_FILE" --server-name review-gate-v2; then
        log_success "Removed review-gate-v2 from MCP configuration (backup created)"
    else
        cp "$MCP_BACKUP_FILE" "$CURSOR_MCP_FILE"
        log_error "Failed to update MCP configuration safely"
        log_info "Original MCP configuration restored from backup"
        exit 1
    fi
fi

# Remove global rule - Cross-platform directory detection
if [[ "$(uname)" == "Darwin" ]]; then
    CURSOR_RULES_DIR="$HOME/Library/Application Support/Cursor/User/rules"
elif [[ "$(uname)" == "Linux" ]]; then
    CURSOR_RULES_DIR="$HOME/.config/Cursor/User/rules"
fi

RULE_FILENAME="ReviewGateV2.mdc"
RULE_FILE="$CURSOR_RULES_DIR/$RULE_FILENAME"
if [[ -n "$CURSOR_RULES_DIR" ]] && [[ -f "$RULE_FILE" ]]; then
    rm "$RULE_FILE"
    log_success "Removed global rule: $RULE_FILE"
fi

# Clean up temp files from both old (/tmp) and new (system temp) locations
rm -f /tmp/review_gate_* /tmp/mcp_response* 2>/dev/null || true
TEMP_DIR=$(python3 -c 'import tempfile; print(tempfile.gettempdir())' 2>/dev/null || echo "/tmp")
rm -f "$TEMP_DIR"/review_gate_* "$TEMP_DIR"/mcp_response* 2>/dev/null || true
log_success "Cleaned up temporary files"

# Try automated extension removal
EXTENSION_REMOVED=false
if command -v cursor &> /dev/null; then
    log_progress "Attempting automated extension removal..."
    if cursor --uninstall-extension review-gate-v2 >/dev/null 2>&1; then
        log_success "Extension removed automatically via command line"
        EXTENSION_REMOVED=true
    else
        log_warning "Automated removal failed, manual steps required"
    fi
fi

echo ""
if [[ "$EXTENSION_REMOVED" == false ]]; then
    log_header "Manual Steps Required:"
    log_step "1. Open Cursor IDE"
    log_step "2. Go to Extensions (Cmd+Shift+X or Ctrl+Shift+X)"
    log_step "3. Find 'Review Gate V2' and uninstall it"
    log_step "4. Restart Cursor"
    echo ""
fi

log_success "Review Gate V2 uninstallation complete!"
log_header "========================================="
echo ""
log_header "What was removed:"
log_step "   - Installation directory: $REVIEW_GATE_DIR"
log_step "   - MCP server configuration entry"
log_step "   - Global rule file: $RULE_FILE"
log_step "   - Temporary files from system directories"
if [[ "$EXTENSION_REMOVED" == true ]]; then
    log_step "   - Cursor extension (removed automatically)"
else
    log_step "   - Cursor extension (manual removal required)"
fi
echo ""
log_header "What remains (if any):"
log_step "   - SoX installation (keep if needed for other apps)"
log_step "   - Python virtual environment dependencies"
log_step "   - Configuration backups (preserved for safety)"
echo ""
if [[ "$EXTENSION_REMOVED" == false ]]; then
    log_info "Extension must be removed manually from Cursor"
else
    log_success "All components removed successfully!"
fi

#!/bin/bash

# Review Gate V2 - One-Click Installation Script
# Author: Lakshman Turlapati
# This script installs Review Gate V2 globally for Cursor IDE

set -e  # Exit on any error

# Enhanced colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
WHITE='\033[1;37m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Logging functions
log_error() { echo -e "${RED}ERROR: $1${NC}"; }
log_success() { echo -e "${GREEN}SUCCESS: $1${NC}"; }
log_info() { echo -e "${YELLOW}INFO: $1${NC}"; }
log_progress() { echo -e "${CYAN}PROGRESS: $1${NC}"; }
log_warning() { echo -e "${YELLOW}WARNING: $1${NC}"; }
log_step() { echo -e "${WHITE}$1${NC}"; }

run_with_timeout() {
    local timeout_seconds="$1"
    shift

    if command -v gtimeout &> /dev/null; then
        gtimeout "${timeout_seconds}s" "$@"
        return $?
    fi

    if command -v timeout &> /dev/null; then
        timeout "${timeout_seconds}s" "$@"
        return $?
    fi

    python3 - "$timeout_seconds" "$@" <<'PY'
import subprocess
import sys

timeout_seconds = float(sys.argv[1])
command = sys.argv[2:]

try:
    completed = subprocess.run(command, timeout=timeout_seconds, check=False)
except subprocess.TimeoutExpired:
    sys.exit(124)
except FileNotFoundError:
    sys.exit(127)

sys.exit(completed.returncode)
PY
}

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo -e "${BLUE}Review Gate V2 - One-Click Installation${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Detect operating system
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    PACKAGE_MANAGER="apt-get"
    INSTALL_CMD="sudo $PACKAGE_MANAGER install -y"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    PACKAGE_MANAGER="brew"
    INSTALL_CMD="$PACKAGE_MANAGER install"
else
    log_error "Unsupported operating system: $OSTYPE"
    log_info "This script is designed for Linux and macOS"
    exit 1
fi

log_success "Detected OS: $OS"

# Only install Homebrew on macOS
if [[ "$OS" == "macos" ]]; then
    if ! command -v brew &> /dev/null; then
        log_progress "Installing Homebrew (macOS package manager)..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        log_success "Homebrew already installed"
    fi
fi

# Install SoX for speech-to-text
log_progress "Installing SoX for speech-to-text..."
if ! command -v sox &> /dev/null; then
    if [[ "$OS" == "linux" ]]; then
        sudo apt-get update
        $INSTALL_CMD sox
    else
        $INSTALL_CMD sox
    fi
else
    log_success "SoX already installed"
fi

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is required but not installed"
    log_info "Please install Python 3 and run this script again"
    exit 1
else
    log_success "Python 3 found: $(python3 --version)"
fi

TEMP_DIR=$(python3 -c 'import tempfile; print(tempfile.gettempdir())')
SOX_TEST_FILE="$TEMP_DIR/sox_test_$$.wav"

# Validate SoX installation and microphone access
log_progress "Validating SoX and microphone setup..."
if command -v sox &> /dev/null; then
    SOX_VERSION=$(sox --version 2>&1 | head -n1)
    log_success "SoX found: $SOX_VERSION"
    
    # Test microphone access (quick test)
    log_progress "Testing microphone access..."
    if run_with_timeout 3 sox -d -r 16000 -c 1 "$SOX_TEST_FILE" trim 0 0.1 2>/dev/null; then
        rm -f "$SOX_TEST_FILE"
        log_success "Microphone access test successful"
    else
        rm -f "$SOX_TEST_FILE"
        log_warning "Microphone test failed - speech features may not work"
        log_info "Common fixes:"
        log_step "   - Grant microphone permissions to Terminal/iTerm"
        log_step "   - Check System Preferences > Security & Privacy > Microphone"
        log_step "   - Make sure no other apps are using the microphone"
    fi
else
    log_error "SoX installation failed"
    log_info "Speech-to-text features will be disabled"
    if [[ "$OS" == "macos" ]]; then
        log_info "Try: brew install sox"
    else
        log_info "Try: sudo apt-get install sox"
    fi
fi

# Create global Cursor extensions directory
CURSOR_EXTENSIONS_DIR="$HOME/cursor-extensions"
REVIEW_GATE_DIR="$CURSOR_EXTENSIONS_DIR/review-gate-v2"

log_progress "Creating global installation directory..."
mkdir -p "$REVIEW_GATE_DIR"

# Copy MCP server files
log_progress "Copying MCP server files..."
cp "$SCRIPT_DIR/review_gate_v2_mcp.py" "$REVIEW_GATE_DIR/"
cp "$SCRIPT_DIR/requirements_simple.txt" "$REVIEW_GATE_DIR/"

# Create Python virtual environment
log_progress "Creating Python virtual environment..."
cd "$REVIEW_GATE_DIR"

# Install python3-venv on Linux if needed
if [[ "$OS" == "linux" ]]; then
    if ! dpkg -s python3-venv >/dev/null 2>&1; then
        log_progress "Installing Python virtual environment support..."
        sudo apt-get update
        sudo apt-get install -y python3-venv
    fi
fi

python3 -m venv venv
VENV_PYTHON="$REVIEW_GATE_DIR/venv/bin/python"

# Activate virtual environment and install dependencies
log_progress "Installing Python dependencies..."
source venv/bin/activate
"$VENV_PYTHON" -m pip install --upgrade pip

# Install dependencies with better error handling
log_progress "Installing core dependencies (mcp, pillow)..."
"$VENV_PYTHON" -m pip install "mcp>=1.9.2" "Pillow>=10.0.0" "asyncio" "typing-extensions>=4.14.0"

# Install faster-whisper with platform-specific handling
log_progress "Installing faster-whisper for speech-to-text..."
if "$VENV_PYTHON" -m pip install "faster-whisper>=1.0.0"; then
    log_success "faster-whisper installed successfully"
else
    log_warning "faster-whisper installation failed - trying alternative approach"
    # Try installing without CUDA dependencies for CPU-only
    if "$VENV_PYTHON" -m pip install "faster-whisper>=1.0.0" --no-deps; then
        "$VENV_PYTHON" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
        log_success "faster-whisper installed with CPU-only dependencies"
    else
        log_error "faster-whisper installation failed"
        log_info "Speech-to-text will be disabled"
        log_info "You can manually install later: \"$VENV_PYTHON\" -m pip install \"faster-whisper>=1.0.0\""
    fi
fi

deactivate

log_success "Python environment created and dependencies installed"

# Create MCP configuration
CURSOR_MCP_FILE="$HOME/.cursor/mcp.json"
log_progress "Configuring MCP servers..."
mkdir -p "$HOME/.cursor"

# Backup existing MCP configuration if it exists
if [[ -f "$CURSOR_MCP_FILE" ]]; then
    BACKUP_FILE="$CURSOR_MCP_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    log_info "Backing up existing MCP configuration to: $BACKUP_FILE"
    cp "$CURSOR_MCP_FILE" "$BACKUP_FILE"
    
    # Check if the existing config is valid JSON (simplified)
    if ! python3 -c "import json; json.load(open('$CURSOR_MCP_FILE'))" >/dev/null 2>&1; then
        log_warning "Existing MCP config has invalid JSON format"
        log_info "Creating new configuration file"
        HAS_EXISTING_SERVERS=false
    else
        log_success "Found existing MCP configuration, will merge servers"
        HAS_EXISTING_SERVERS=true
    fi
else
    log_info "Creating new MCP configuration file"
    HAS_EXISTING_SERVERS=false
fi

# Create simplified MCP configuration
log_progress "Configuring MCP servers..."

# Create the new configuration using a simple Python script
python3 -c "
import json
import os

config_file = '$CURSOR_MCP_FILE'
review_gate_dir = '$REVIEW_GATE_DIR'
has_existing = $([[ "$HAS_EXISTING_SERVERS" == "true" ]] && echo "True" || echo "False")

# Read existing config if available
existing_servers = {}
if has_existing and os.path.exists(config_file):
    try:
        with open(config_file, 'r') as f:
            existing_config = json.load(f)
            existing_servers = existing_config.get('mcpServers', {})
            # Remove review-gate-v2 if it exists (we'll add the new one)
            existing_servers.pop('review-gate-v2', None)
    except:
        existing_servers = {}

# Add Review Gate V2 configuration
existing_servers['review-gate-v2'] = {
    'command': os.path.join(review_gate_dir, 'venv/bin/python'),
    'args': [os.path.join(review_gate_dir, 'review_gate_v2_mcp.py')],
    'env': {
        'PYTHONPATH': review_gate_dir,
        'PYTHONUNBUFFERED': '1',
        'REVIEW_GATE_MODE': 'cursor_integration'
    }
}

# Write the configuration
config = {'mcpServers': existing_servers}
os.makedirs(os.path.dirname(config_file), exist_ok=True)
with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)
"

if [[ $? -eq 0 ]]; then
    log_success "MCP configuration updated successfully"
else
    log_error "Failed to update MCP configuration"
    exit 1
fi

# Validate the generated configuration
if python3 -c "import json; json.load(open('$CURSOR_MCP_FILE'))" >/dev/null 2>&1; then
    log_success "MCP configuration file created at: $CURSOR_MCP_FILE"
    
    # Count configured servers (simplified)
    SERVER_COUNT=$(python3 -c "import json; print(len(json.load(open('$CURSOR_MCP_FILE')).get('mcpServers', {})))")
    log_step "Total MCP servers configured: $SERVER_COUNT"
    log_step "  - review-gate-v2 (Review Gate V2)"
else
    log_error "Generated MCP configuration is invalid"
    if [[ -f "$BACKUP_FILE" ]]; then
        log_progress "Restoring from backup..."
        cp "$BACKUP_FILE" "$CURSOR_MCP_FILE"
        log_success "Backup restored"
    else
        log_error "No backup available, installation failed"
        exit 1
    fi
fi

# Test MCP server
log_progress "Testing MCP server..."
cd "$REVIEW_GATE_DIR"
MCP_TEST_LOG="$TEMP_DIR/mcp_test.log"
run_with_timeout 5 "$VENV_PYTHON" "$REVIEW_GATE_DIR/review_gate_v2_mcp.py" > "$MCP_TEST_LOG" 2>&1 || true

if grep -q "Review Gate 2.0 server initialized" "$MCP_TEST_LOG"; then
    log_success "MCP server test successful"
else
    log_warning "MCP server test inconclusive (may be normal)"
fi
rm -f "$MCP_TEST_LOG"

# Install Cursor extension
EXTENSION_FILE="$SCRIPT_DIR/cursor-extension/review-gate-v2-2.7.3.vsix"
if [[ -f "$EXTENSION_FILE" ]]; then
    log_progress "Installing Cursor extension..."
    
    # Copy extension to installation directory
    cp "$EXTENSION_FILE" "$REVIEW_GATE_DIR/"
    
    # Try automated installation first
    EXTENSION_INSTALLED=false
    if command -v cursor &> /dev/null; then
        log_progress "Attempting automated extension installation..."
        if cursor --install-extension "$EXTENSION_FILE" >/dev/null 2>&1; then
            log_success "Extension installed automatically via command line"
            EXTENSION_INSTALLED=true
        else
            log_warning "Automated installation failed, falling back to manual method"
        fi
    fi
    
    # If automated installation failed, provide manual instructions
    if [[ "$EXTENSION_INSTALLED" == false ]]; then
        echo -e "${BLUE}MANUAL EXTENSION INSTALLATION REQUIRED:${NC}"
        log_info "Please complete the extension installation manually:"
        log_step "1. Open Cursor IDE"
        log_step "2. Press Cmd+Shift+P (or Ctrl+Shift+P on Linux)"
        log_step "3. Type 'Extensions: Install from VSIX'"
        log_step "4. Select: $REVIEW_GATE_DIR/review-gate-v2-2.7.3.vsix"
        log_step "5. Restart Cursor when prompted"
        echo ""
        
        # Try to open Cursor if available
        if command -v cursor &> /dev/null; then
            log_progress "Opening Cursor IDE..."
            cursor . &
        elif [[ -d "/Applications/Cursor.app" ]]; then
            log_progress "Opening Cursor IDE..."
            open -a "Cursor" . &
        else
            log_info "Please open Cursor IDE manually"
        fi
    fi
else
    log_error "Extension file not found: $EXTENSION_FILE"
    log_info "Please ensure the extension is built in cursor-extension/ directory"
    log_info "Or install manually from the Cursor Extensions marketplace"
fi

# Install global rule (optional) - Cross-platform directory detection
if [[ "$OS" == "macos" ]]; then
    CURSOR_RULES_DIR="$HOME/Library/Application Support/Cursor/User/rules"
elif [[ "$OS" == "linux" ]]; then
    CURSOR_RULES_DIR="$HOME/.config/Cursor/User/rules"
fi

if [[ -f "$SCRIPT_DIR/ReviewGate.mdc" ]] && [[ -n "$CURSOR_RULES_DIR" ]]; then
    log_progress "Installing global rule..."
    mkdir -p "$CURSOR_RULES_DIR"
    cp "$SCRIPT_DIR/ReviewGate.mdc" "$CURSOR_RULES_DIR/"
    log_success "Global rule installed to: $CURSOR_RULES_DIR"
elif [[ -f "$SCRIPT_DIR/ReviewGate.mdc" ]]; then
    log_warning "Could not determine Cursor rules directory for this platform"
    log_info "Global rule available at: $SCRIPT_DIR/ReviewGate.mdc"
fi

# Clean up any existing temp files
log_progress "Cleaning up temporary files..."
TEMP_DIR=$(python3 -c 'import tempfile; print(tempfile.gettempdir())')
rm -f "$TEMP_DIR"/review_gate_* "$TEMP_DIR"/mcp_response* 2>/dev/null || true

echo ""
log_success "Review Gate V2 Installation Complete!"
echo -e "${GREEN}=======================================${NC}"
echo ""
echo -e "${BLUE}Installation Summary:${NC}"
log_step "   - MCP Server: $REVIEW_GATE_DIR"
log_step "   - MCP Config: $CURSOR_MCP_FILE"
log_step "   - Extension: $REVIEW_GATE_DIR/review-gate-v2-2.7.3.vsix"
log_step "   - Global Rule: $CURSOR_RULES_DIR/ReviewGate.mdc"
echo ""
echo -e "${BLUE}Testing Your Installation:${NC}"
log_step "1. Restart Cursor completely"
log_step "2. Press Cmd+Shift+R to test manual trigger"
log_step "3. Or ask Cursor Agent: 'Use the review_gate_chat tool'"
echo ""
echo -e "${BLUE}Speech-to-Text Features:${NC}"
log_step "   - Click microphone icon in popup"
log_step "   - Speak clearly for 2-3 seconds"
log_step "   - Click stop to transcribe"
echo ""
echo -e "${BLUE}Image Upload Features:${NC}"
log_step "   - Click camera icon in popup"
log_step "   - Select images (PNG, JPG, etc.)"
log_step "   - Images are included in response"
echo ""
echo -e "${BLUE}Troubleshooting:${NC}"
log_step "   - Logs: tail -f $(python3 -c 'import tempfile; print(tempfile.gettempdir())')/review_gate_v2.log"
log_step "   - Test SoX: sox --version"
log_step "   - Browser Console: F12 in Cursor"
echo ""
log_success "Enjoy your voice-activated Review Gate!"

# Final verification
log_progress "Final verification..."
if [[ -f "$REVIEW_GATE_DIR/review_gate_v2_mcp.py" ]] && \
   [[ -f "$CURSOR_MCP_FILE" ]] && \
   [[ -d "$REVIEW_GATE_DIR/venv" ]]; then
    log_success "All components installed successfully"
    exit 0
else
    log_error "Some components may not have installed correctly"
    log_info "Please check the installation manually"
    exit 1
fi

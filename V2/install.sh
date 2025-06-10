#!/bin/bash

# Review Gate V2 - One-Click Installation Script
# Author: Lakshman Turlapati
# This script installs Review Gate V2 globally for Cursor IDE

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo -e "${BLUE}🚀 Review Gate V2 - One-Click Installation${NC}"
echo -e "${BLUE}===========================================${NC}"
echo ""

# Detect OS
OS_TYPE="Unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="Linux"
    # Check for WSL
    if grep -qE "(Microsoft|WSL)" /proc/version &> /dev/null; then
        OS_TYPE="WSL"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macOS"
fi

echo -e "${GREEN}✅ Detected Operating System: $OS_TYPE${NC}"

if [[ "$OS_TYPE" == "Unknown" ]]; then
    echo -e "${RED}❌ This script supports macOS, Linux, and WSL only${NC}"
    exit 1
fi

# Install dependencies based on OS
install_dependencies() {
    echo -e "${YELLOW}🎤 Checking for SoX (for speech-to-text)...${NC}"
    if command -v sox &> /dev/null; then
        echo -e "${GREEN}✅ SoX already installed${NC}"
        return
    fi

    if [[ "$OS_TYPE" == "macOS" ]]; then
        # Check if Homebrew is installed
        if ! command -v brew &> /dev/null; then
            echo -e "${YELLOW}📦 Installing Homebrew...${NC}"
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        echo -e "${YELLOW}🎤 Installing SoX...${NC}"
        brew install sox
    elif [[ "$OS_TYPE" == "Linux" || "$OS_TYPE" == "WSL" ]]; then
        # Check for package manager
        if command -v apt-get &> /dev/null; then
            echo -e "${YELLOW}📦 Using apt-get to install SoX...${NC}"
            sudo apt-get update && sudo apt-get install -y sox
        elif command -v dnf &> /dev/null; then
            echo -e "${YELLOW}📦 Using dnf to install SoX...${NC}"
            sudo dnf install -y sox
        elif command -v yum &> /dev/null; then
            echo -e "${YELLOW}📦 Using yum to install SoX...${NC}"
            sudo yum install -y sox
        elif command -v pacman &> /dev/null; then
            echo -e "${YELLOW}📦 Using pacman to install SoX...${NC}"
            sudo pacman -S --noconfirm sox
        else
            echo -e "${RED}❌ Could not find a supported package manager (apt-get, dnf, yum, pacman)${NC}"
            echo -e "${YELLOW}💡 Please install 'sox' manually and re-run the script.${NC}"
            exit 1
        fi
    fi

    if command -v sox &> /dev/null; then
        echo -e "${GREEN}✅ SoX installed successfully${NC}"
    else
        echo -e "${RED}❌ SoX installation failed.${NC}"
        exit 1
    fi
}

# Install dependencies
install_dependencies

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is required but not installed${NC}"
    echo -e "${YELLOW}💡 Please install Python 3 and run this script again${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Python 3 found: $(python3 --version)${NC}"
fi

# Create global Cursor extensions directory
CURSOR_EXTENSIONS_DIR="$HOME/cursor-extensions"
REVIEW_GATE_DIR="$CURSOR_EXTENSIONS_DIR/review-gate-v2"

echo -e "${YELLOW}📁 Creating global installation directory...${NC}"
mkdir -p "$REVIEW_GATE_DIR"

# Copy MCP server files
echo -e "${YELLOW}📋 Copying MCP server files...${NC}"
cp "$SCRIPT_DIR/review_gate_v2_mcp.py" "$REVIEW_GATE_DIR/"
cp "$SCRIPT_DIR/requirements_simple.txt" "$REVIEW_GATE_DIR/"

# Create Python virtual environment
echo -e "${YELLOW}🐍 Creating Python virtual environment...${NC}"
cd "$REVIEW_GATE_DIR"
python3 -m venv venv

# Activate virtual environment and install dependencies
echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements_simple.txt
deactivate

echo -e "${GREEN}✅ Python environment created and dependencies installed${NC}"

# Create MCP configuration
CURSOR_MCP_FILE="$HOME/.cursor/mcp.json"
echo -e "${YELLOW}⚙️ Configuring MCP servers...${NC}"
mkdir -p "$HOME/.cursor"

# Backup existing MCP configuration if it exists
if [[ -f "$CURSOR_MCP_FILE" ]]; then
    BACKUP_FILE="$CURSOR_MCP_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}💾 Backing up existing MCP configuration to: $BACKUP_FILE${NC}"
    cp "$CURSOR_MCP_FILE" "$BACKUP_FILE"
    
    # Check if the existing config is valid JSON
    if ! python3 -m json.tool "$CURSOR_MCP_FILE" > /dev/null 2>&1; then
        echo -e "${RED}⚠️ Existing MCP config has invalid JSON format${NC}"
        echo -e "${YELLOW}💡 Creating new configuration file${NC}"
        EXISTING_SERVERS="{}"
    else
        # Read existing servers
        EXISTING_SERVERS=$(python3 -c "
import json
try:
    with open('$CURSOR_MCP_FILE', 'r') as f:
        config = json.load(f)
    servers = config.get('mcpServers', {})
    # Remove review-gate-v2 if it exists (we'll add the new one)
    servers.pop('review-gate-v2', None)
    print(json.dumps(servers, indent=2))
except Exception as e:
    print('{}')
" 2>/dev/null)
        
        if [[ "$EXISTING_SERVERS" == "{}" ]]; then
            echo -e "${YELLOW}📝 No existing MCP servers found or failed to parse${NC}"
        else
            echo -e "${GREEN}✅ Found existing MCP servers, merging configurations${NC}"
        fi
    fi
else
    echo -e "${YELLOW}📝 Creating new MCP configuration file${NC}"
    EXISTING_SERVERS="{}"
fi

# Generate merged MCP config
USERNAME=$(whoami)
python3 -c '
import json
import sys

# Parse existing servers from arguments
try:
    existing_servers = json.loads(sys.argv[1])
except json.JSONDecodeError:
    existing_servers = {}

review_gate_dir = sys.argv[2]
cursor_mcp_file = sys.argv[3]

# Add Review Gate V2 server
existing_servers["review-gate-v2"] = {
    "command": f"{review_gate_dir}/venv/bin/python",
    "args": [f"{review_gate_dir}/review_gate_v2_mcp.py"],
    "env": {
        "PYTHONPATH": review_gate_dir,
        "PYTHONUNBUFFERED": "1",
        "REVIEW_GATE_MODE": "cursor_integration"
    }
}

# Create final config
config = {"mcpServers": existing_servers}

# Write to file
with open(cursor_mcp_file, "w") as f:
    json.dump(config, f, indent=2)

print("MCP configuration updated successfully")
' "$EXISTING_SERVERS" "$REVIEW_GATE_DIR" "$CURSOR_MCP_FILE"

# Validate the generated configuration
if python3 -m json.tool "$CURSOR_MCP_FILE" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ MCP configuration updated successfully at: $CURSOR_MCP_FILE${NC}"
    
    # Show summary of configured servers
    TOTAL_SERVERS=$(python3 -c "
import json
with open('$CURSOR_MCP_FILE', 'r') as f:
    config = json.load(f)
servers = config.get('mcpServers', {})
print(f'Total MCP servers configured: {len(servers)}')
for name in servers.keys():
    print(f'  • {name}')
" 2>/dev/null)
    echo -e "${BLUE}$TOTAL_SERVERS${NC}"
else
    echo -e "${RED}❌ Generated MCP configuration is invalid${NC}"
    if [[ -f "$BACKUP_FILE" ]]; then
        echo -e "${YELLOW}🔄 Restoring from backup...${NC}"
        cp "$BACKUP_FILE" "$CURSOR_MCP_FILE"
        echo -e "${GREEN}✅ Backup restored${NC}"
    else
        echo -e "${RED}❌ No backup available, installation failed${NC}"
        exit 1
    fi
fi

# Test MCP server
echo -e "${YELLOW}🧪 Testing MCP server...${NC}"
cd "$REVIEW_GATE_DIR"
source venv/bin/activate
TEMP_DIR=$(python3 -c 'import tempfile; print(tempfile.gettempdir())')
timeout 5s python review_gate_v2_mcp.py > "$TEMP_DIR/mcp_test.log" 2>&1 || true
deactivate

if grep -q "Review Gate 2.0 server initialized" "$TEMP_DIR/mcp_test.log"; then
    echo -e "${GREEN}✅ MCP server test successful${NC}"
else
    echo -e "${YELLOW}⚠️ MCP server test inconclusive (may be normal)${NC}"
fi
rm -f "$TEMP_DIR/mcp_test.log"

# Install Cursor extension
EXTENSION_FILE="$SCRIPT_DIR/cursor-extension/review-gate-v2-2.6.3.vsix"
if [[ -f "$EXTENSION_FILE" ]]; then
    echo -e "${YELLOW}🔌 Installing Cursor extension...${NC}"
    
    # Copy extension to installation directory
    cp "$EXTENSION_FILE" "$REVIEW_GATE_DIR/"
    
    echo -e "${BLUE}📋 MANUAL STEP REQUIRED:${NC}"
    echo -e "${YELLOW}Please complete the extension installation manually:${NC}"
    echo -e "1. Open Cursor IDE"
    echo -e "2. Press Cmd+Shift+P (macOS) or Ctrl+Shift+P (Linux/WSL)"
    echo -e "3. Type 'Extensions: Install from VSIX'"
    echo -e "4. Select: $REVIEW_GATE_DIR/review-gate-v2-2.6.3.vsix"
    echo -e "5. Restart Cursor when prompted"
    echo ""
    
    # Try to open Cursor if available
    if [[ "$OS_TYPE" == "macOS" ]]; then
        if command -v cursor &> /dev/null; then
            echo -e "${YELLOW}🚀 Opening Cursor IDE...${NC}"
            cursor . &
        elif [[ -d "/Applications/Cursor.app" ]]; then
            echo -e "${YELLOW}🚀 Opening Cursor IDE...${NC}"
            open -a "Cursor" . &
        else
            echo -e "${YELLOW}💡 Please open Cursor IDE manually${NC}"
        fi
    else # Linux/WSL
         if command -v cursor &> /dev/null; then
            echo -e "${YELLOW}🚀 Opening Cursor IDE...${NC}"
            cursor . &
         else
            echo -e "${YELLOW}💡 Please open Cursor IDE manually${NC}"
         fi
    fi
else
    echo -e "${RED}❌ Extension file not found: $EXTENSION_FILE${NC}"
    echo -e "${YELLOW}💡 Please install the extension manually from the Cursor Extensions marketplace${NC}"
fi

# Install global rule (optional)
if [[ -f "$SCRIPT_DIR/ReviewGateV2.mdc" ]]; then
    echo -e "${YELLOW}📜 Installing global rule...${NC}"
    
    # Determine OS-specific rules directory
    if [[ "$OS_TYPE" == "macOS" ]]; then
        CURSOR_RULES_DIR="$HOME/Library/Application Support/Cursor/User/rules"
    else # Linux or WSL
        CURSOR_RULES_DIR="$HOME/.config/cursor/rules"
    fi

    mkdir -p "$CURSOR_RULES_DIR"
    cp "$SCRIPT_DIR/ReviewGateV2.mdc" "$CURSOR_RULES_DIR/"
    echo -e "${GREEN}✅ Global rule installed to $CURSOR_RULES_DIR${NC}"
fi

# Clean up any existing temp files
echo -e "${YELLOW}🧹 Cleaning up temporary files...${NC}"
TEMP_DIR=$(python3 -c 'import tempfile; print(tempfile.gettempdir())')
rm -f "$TEMP_DIR"/review_gate_* "$TEMP_DIR"/mcp_response* 2>/dev/null || true

echo ""
echo -e "${GREEN}🎉 Review Gate V2 Installation Complete!${NC}"
echo -e "${GREEN}=======================================${NC}"
echo ""
echo -e "${BLUE}📍 Installation Summary:${NC}"
echo -e "   • MCP Server: $REVIEW_GATE_DIR"
echo -e "   • MCP Config: $CURSOR_MCP_FILE"
echo -e "   • Extension: $REVIEW_GATE_DIR/review-gate-v2-2.5.2.vsix"
if [[ -n "$CURSOR_RULES_DIR" && -f "$CURSOR_RULES_DIR/ReviewGateV2.mdc" ]]; then
    echo -e "   • Global Rule: $CURSOR_RULES_DIR/ReviewGateV2.mdc"
fi
echo ""
echo -e "${BLUE}🧪 Testing Your Installation:${NC}"
echo -e "1. Restart Cursor completely"

# Provide OS-specific instructions
if [[ "$OS_TYPE" == "macOS" ]]; then
    echo -e "2. Press ${YELLOW}Cmd+Shift+R${NC} to test manual trigger"
else
    echo -e "2. Press ${YELLOW}Ctrl+Shift+R${NC} to test manual trigger"
fi
echo "3. Or ask Cursor Agent: 'Use the review_gate_chat tool'"

echo ""
if [[ "$OS_TYPE" == "WSL" ]]; then
    echo -e "${YELLOW}🖥️  WSL Note:${NC}"
    echo -e "   This script assumes you are running Cursor's GUI from within WSL (e.g., via WSLg)."
    echo -e "   The MCP server is configured to run inside your WSL environment."
fi

echo ""
echo -e "${BLUE}🔧 Troubleshooting:${NC}"
echo -e "   • Logs: ${YELLOW}tail -f $(python3 -c 'import tempfile; print(tempfile.gettempdir())')/review_gate_v2.log${NC}"
echo -e "   • Test SoX: ${YELLOW}sox --version${NC}"
echo -e "   • Browser Console: In Cursor, run 'Developer: Toggle Developer Tools' from the command palette."
echo ""
echo -e "${GREEN}✨ Enjoy your interactive Review Gate! ✨${NC}"

# Final verification
echo -e "${YELLOW}🔍 Final verification...${NC}"
if [[ -f "$REVIEW_GATE_DIR/review_gate_v2_mcp.py" ]] && \
   [[ -f "$CURSOR_MCP_FILE" ]] && \
   [[ -d "$REVIEW_GATE_DIR/venv" ]]; then
    echo -e "${GREEN}✅ All components installed successfully${NC}"
    exit 0
else
    echo -e "${RED}❌ Some components may not have installed correctly${NC}"
    echo -e "${YELLOW}💡 Please check the installation manually${NC}"
    exit 1
fi

echo "Installation script finished." 
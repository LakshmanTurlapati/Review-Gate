# Review Gate V2 - Windows PowerShell Installation Script
# Author: Lakshman Turlapati
# This script installs Review Gate V2 globally for Cursor IDE on Windows

# Enable strict error handling
$ErrorActionPreference = "Stop"

# Function to write colored output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-ColorOutput "🚀 Review Gate V2 - Windows Installation" "Cyan"
Write-ColorOutput "=========================================" "Cyan"
Write-Host ""

# Check if running on Windows
if ($PSVersionTable.Platform -and $PSVersionTable.Platform -ne "Win32NT") {
    Write-ColorOutput "❌ This script is designed for Windows only" "Red"
    exit 1
}

# Check for admin privileges for package manager installation
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-ColorOutput "⚠️ Administrator privileges recommended for package installations" "Yellow"
    Write-ColorOutput "💡 Some features may require manual installation" "Yellow"
}

# Check if Chocolatey is installed, if not install it
Write-ColorOutput "📦 Checking for Chocolatey package manager..." "Yellow"
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    if ($isAdmin) {
        Write-ColorOutput "📦 Installing Chocolatey..." "Yellow"
        try {
            Set-ExecutionPolicy Bypass -Scope Process -Force
            [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
            Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
            Write-ColorOutput "✅ Chocolatey installed successfully" "Green"
        } catch {
            Write-ColorOutput "❌ Failed to install Chocolatey automatically" "Red"
            Write-ColorOutput "💡 Please install Chocolatey manually from https://chocolatey.org/install" "Yellow"
            Write-ColorOutput "💡 Then run this script again" "Yellow"
            exit 1
        }
    } else {
        Write-ColorOutput "❌ Chocolatey not found and admin privileges required for installation" "Red"
        Write-ColorOutput "💡 Please install Chocolatey manually: https://chocolatey.org/install" "Yellow"
        Write-ColorOutput "💡 Or run this script as Administrator" "Yellow"
        exit 1
    }
} else {
    Write-ColorOutput "✅ Chocolatey already installed" "Green"
}

# Install SoX for speech-to-text
Write-ColorOutput "🎤 Installing SoX for speech-to-text..." "Yellow"
if (-not (Get-Command sox -ErrorAction SilentlyContinue)) {
    if ($isAdmin) {
        try {
            choco install sox -y
            Write-ColorOutput "✅ SoX installed successfully" "Green"
        } catch {
            Write-ColorOutput "⚠️ Failed to install SoX via Chocolatey" "Yellow"
            Write-ColorOutput "💡 Please install SoX manually from http://sox.sourceforge.net/" "Yellow"
        }
    } else {
        Write-ColorOutput "⚠️ Admin privileges required to install SoX" "Yellow"
        Write-ColorOutput "💡 Please install SoX manually or run as Administrator" "Yellow"
    }
} else {
    Write-ColorOutput "✅ SoX already installed" "Green"
}

# Check if Python 3 is available
Write-ColorOutput "🐍 Checking Python installation..." "Yellow"
if (-not (Get-Command python -ErrorAction SilentlyContinue) -and -not (Get-Command python3 -ErrorAction SilentlyContinue)) {
    Write-ColorOutput "❌ Python 3 is required but not installed" "Red"
    Write-ColorOutput "💡 Please install Python 3 from https://python.org or Microsoft Store" "Yellow"
    Write-ColorOutput "💡 Then run this script again" "Yellow"
    exit 1
} else {
    $pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }
    $pythonVersion = & $pythonCmd --version
    Write-ColorOutput "✅ Python found: $pythonVersion" "Green"
}

# Create global Cursor extensions directory
$CursorExtensionsDir = Join-Path $env:USERPROFILE "cursor-extensions"
$ReviewGateDir = Join-Path $CursorExtensionsDir "review-gate-v2"

Write-ColorOutput "📁 Creating global installation directory..." "Yellow"
New-Item -Path $ReviewGateDir -ItemType Directory -Force | Out-Null

# Copy MCP server files
Write-ColorOutput "📋 Copying MCP server files..." "Yellow"
$mcpServerSrc = Join-Path $ScriptDir "review_gate_v2_mcp.py"
$requirementsSrc = Join-Path $ScriptDir "requirements_simple.txt"

if (Test-Path $mcpServerSrc) {
    Copy-Item $mcpServerSrc $ReviewGateDir -Force
} else {
    Write-ColorOutput "❌ MCP server file not found: $mcpServerSrc" "Red"
    exit 1
}

if (Test-Path $requirementsSrc) {
    Copy-Item $requirementsSrc $ReviewGateDir -Force
} else {
    Write-ColorOutput "❌ Requirements file not found: $requirementsSrc" "Red"
    exit 1
}

# Create Python virtual environment
Write-ColorOutput "🐍 Creating Python virtual environment..." "Yellow"
Set-Location $ReviewGateDir
& $pythonCmd -m venv venv

# Activate virtual environment and install dependencies
Write-ColorOutput "📦 Installing Python dependencies..." "Yellow"
$venvActivate = Join-Path $ReviewGateDir "venv\Scripts\Activate.ps1"
$venvPython = Join-Path $ReviewGateDir "venv\Scripts\python.exe"

if (Test-Path $venvActivate) {
    & $venvActivate
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r (Join-Path $ReviewGateDir "requirements_simple.txt")
    deactivate
} else {
    Write-ColorOutput "❌ Failed to create virtual environment" "Red"
    exit 1
}

Write-ColorOutput "✅ Python environment created and dependencies installed" "Green"

# Create MCP configuration
$CursorMcpFile = Join-Path $env:USERPROFILE ".cursor\mcp.json"
Write-ColorOutput "⚙️ Configuring MCP servers..." "Yellow"
$CursorDir = Join-Path $env:USERPROFILE ".cursor"
New-Item -Path $CursorDir -ItemType Directory -Force | Out-Null

# Backup existing MCP configuration if it exists
if (Test-Path $CursorMcpFile) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupFile = "$CursorMcpFile.backup.$timestamp"
    Write-ColorOutput "💾 Backing up existing MCP configuration to: $BackupFile" "Yellow"
    Copy-Item $CursorMcpFile $BackupFile -Force
    
    # Check if the existing config is valid JSON
    try {
        $existingConfig = Get-Content $CursorMcpFile -Raw | ConvertFrom-Json
        $existingServers = $existingConfig.mcpServers
        if (-not $existingServers) {
            $existingServers = @{}
        }
        # Remove review-gate-v2 if it exists (we'll add the new one)
        if ($existingServers.PSObject.Properties.Name -contains "review-gate-v2") {
            $existingServers.PSObject.Properties.Remove("review-gate-v2")
        }
        Write-ColorOutput "✅ Found existing MCP servers, merging configurations" "Green"
    } catch {
        Write-ColorOutput "⚠️ Existing MCP config has invalid JSON format" "Yellow"
        Write-ColorOutput "💡 Creating new configuration file" "Yellow"
        $existingServers = @{}
    }
} else {
    Write-ColorOutput "📝 Creating new MCP configuration file" "Yellow"
    $existingServers = @{}
}

# Create merged MCP configuration
$reviewGateConfig = @{
    command = $venvPython
    args = @(Join-Path $ReviewGateDir "review_gate_v2_mcp.py")
    env = @{
        PYTHONPATH = $ReviewGateDir
        PYTHONUNBUFFERED = "1"
        REVIEW_GATE_MODE = "cursor_integration"
    }
}

# Add Review Gate to existing servers
$existingServers | Add-Member -MemberType NoteProperty -Name "review-gate-v2" -Value $reviewGateConfig -Force

# Create final configuration
$finalConfig = @{
    mcpServers = $existingServers
}

try {
    $finalConfig | ConvertTo-Json -Depth 10 | Set-Content $CursorMcpFile -Encoding UTF8
    Write-ColorOutput "✅ MCP configuration updated successfully at: $CursorMcpFile" "Green"
    
    # Show summary of configured servers
    $serverCount = $existingServers.PSObject.Properties.Name.Count
    Write-ColorOutput "Total MCP servers configured: $serverCount" "Cyan"
    foreach ($serverName in $existingServers.PSObject.Properties.Name) {
        Write-ColorOutput "  • $serverName" "Cyan"
    }
} catch {
    Write-ColorOutput "❌ Failed to create MCP configuration" "Red"
    if (Test-Path $BackupFile) {
        Write-ColorOutput "🔄 Restoring from backup..." "Yellow"
        Copy-Item $BackupFile $CursorMcpFile -Force
        Write-ColorOutput "✅ Backup restored" "Green"
    } else {
        Write-ColorOutput "❌ No backup available, installation failed" "Red"
        exit 1
    }
}

# Test MCP server
Write-ColorOutput "🧪 Testing MCP server..." "Yellow"
Set-Location $ReviewGateDir
try {
    $testJob = Start-Job -ScriptBlock {
        param($venvPython, $reviewGateDir)
        & $venvPython (Join-Path $reviewGateDir "review_gate_v2_mcp.py")
    } -ArgumentList $venvPython, $ReviewGateDir
    
    Start-Sleep -Seconds 5
    Stop-Job $testJob -ErrorAction SilentlyContinue
    $testOutput = Receive-Job $testJob -ErrorAction SilentlyContinue
    Remove-Job $testJob -Force -ErrorAction SilentlyContinue
    
    if ($testOutput -match "Review Gate 2.0 server initialized") {
        Write-ColorOutput "✅ MCP server test successful" "Green"
    } else {
        Write-ColorOutput "⚠️ MCP server test inconclusive (may be normal)" "Yellow"
    }
} catch {
    Write-ColorOutput "⚠️ MCP server test failed (may be normal)" "Yellow"
}

# Install Cursor extension
$ExtensionFile = Join-Path $ScriptDir "cursor-extension\review-gate-v2-2.6.3.vsix"
if (Test-Path $ExtensionFile) {
    Write-ColorOutput "🔌 Installing Cursor extension..." "Yellow"
    
    # Copy extension to installation directory
    Copy-Item $ExtensionFile $ReviewGateDir -Force
    
    Write-ColorOutput "📋 MANUAL STEP REQUIRED:" "Cyan"
    Write-ColorOutput "Please complete the extension installation manually:" "Yellow"
    Write-ColorOutput "1. Open Cursor IDE" "White"
    Write-ColorOutput "2. Press Ctrl+Shift+P" "White"
    Write-ColorOutput "3. Type 'Extensions: Install from VSIX'" "White"
    Write-ColorOutput "4. Select: $ReviewGateDir\review-gate-v2-2.6.3.vsix" "White"
    Write-ColorOutput "5. Restart Cursor when prompted" "White"
    Write-Host ""
    
    # Try to open Cursor if available
    $cursorPaths = @(
        "${env:ProgramFiles}\Cursor\Cursor.exe",
        "${env:LOCALAPPDATA}\Programs\cursor\Cursor.exe",
        "${env:ProgramFiles(x86)}\Cursor\Cursor.exe"
    )
    
    $cursorFound = $false
    foreach ($path in $cursorPaths) {
        if (Test-Path $path) {
            Write-ColorOutput "🚀 Opening Cursor IDE..." "Yellow"
            Start-Process $path -WorkingDirectory (Get-Location)
            $cursorFound = $true
            break
        }
    }
    
    if (-not $cursorFound) {
        Write-ColorOutput "💡 Please open Cursor IDE manually" "Yellow"
    }
} else {
    Write-ColorOutput "❌ Extension file not found: $ExtensionFile" "Red"
    Write-ColorOutput "💡 Please install the extension manually from the Cursor Extensions marketplace" "Yellow"
}

# Install global rule (optional)
$CursorRulesDir = Join-Path $env:APPDATA "Cursor\User\rules"
$ruleFile = Join-Path $ScriptDir "ReviewGate.mdc"
if (Test-Path $ruleFile) {
    Write-ColorOutput "📜 Installing global rule..." "Yellow"
    New-Item -Path $CursorRulesDir -ItemType Directory -Force | Out-Null
    Copy-Item $ruleFile $CursorRulesDir -Force
    Write-ColorOutput "✅ Global rule installed" "Green"
}

# Clean up any existing temp files
Write-ColorOutput "🧹 Cleaning up temporary files..." "Yellow"
$tempPath = [System.IO.Path]::GetTempPath()
Get-ChildItem $tempPath -Filter "review_gate_*" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem $tempPath -Filter "mcp_response*" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-ColorOutput "🎉 Review Gate V2 Installation Complete!" "Green"
Write-ColorOutput "=======================================" "Green"
Write-Host ""
Write-ColorOutput "📍 Installation Summary:" "Cyan"
Write-ColorOutput "   • MCP Server: $ReviewGateDir" "White"
Write-ColorOutput "   • MCP Config: $CursorMcpFile" "White"
Write-ColorOutput "   • Extension: $ReviewGateDir\review-gate-v2-2.6.3.vsix" "White"
Write-ColorOutput "   • Global Rule: $CursorRulesDir\ReviewGate.mdc" "White"
Write-Host ""
Write-ColorOutput "🧪 Testing Your Installation:" "Cyan"
Write-ColorOutput "1. Restart Cursor completely" "White"
Write-ColorOutput "2. Press Ctrl+Shift+R to test manual trigger" "Yellow"
Write-ColorOutput "3. Or ask Cursor Agent: 'Use the review_gate_chat tool'" "Yellow"
Write-Host ""
Write-ColorOutput "🎤 Speech-to-Text Features:" "Cyan"
Write-ColorOutput "   • Click microphone icon in popup" "White"
Write-ColorOutput "   • Speak clearly for 2-3 seconds" "White"
Write-ColorOutput "   • Click stop to transcribe" "White"
Write-Host ""
Write-ColorOutput "📷 Image Upload Features:" "Cyan"
Write-ColorOutput "   • Click camera icon in popup" "White"
Write-ColorOutput "   • Select images (PNG, JPG, etc.)" "White"
Write-ColorOutput "   • Images are included in response" "White"
Write-Host ""
Write-ColorOutput "🔧 Troubleshooting:" "Cyan"
Write-ColorOutput "   • Logs: Get-Content ([System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), 'review_gate_v2.log')) -Wait" "Yellow"
Write-ColorOutput "   • Test SoX: sox --version" "Yellow"
Write-ColorOutput "   • Browser Console: F12 in Cursor" "Yellow"
Write-Host ""
Write-ColorOutput "✨ Enjoy your voice-activated Review Gate! ✨" "Green"

# Final verification
Write-ColorOutput "🔍 Final verification..." "Yellow"
$mcpServerFile = Join-Path $ReviewGateDir "review_gate_v2_mcp.py"
$venvDir = Join-Path $ReviewGateDir "venv"

if ((Test-Path $mcpServerFile) -and (Test-Path $CursorMcpFile) -and (Test-Path $venvDir)) {
    Write-ColorOutput "✅ All components installed successfully" "Green"
    exit 0
} else {
    Write-ColorOutput "❌ Some components may not have installed correctly" "Red"
    Write-ColorOutput "💡 Please check the installation manually" "Yellow"
    exit 1
}
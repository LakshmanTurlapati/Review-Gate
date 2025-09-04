# Review Gate V2 - Windows PowerShell Installation Script
# Author: Lakshman Turlapati
# This script installs Review Gate V2 globally for Cursor IDE on Windows

# Enable strict error handling
$ErrorActionPreference = "Stop"

# Enhanced color logging functions
function Write-Error-Log { param([string]$Message) Write-Host "❌ $Message" -ForegroundColor Red }
function Write-Success-Log { param([string]$Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info-Log { param([string]$Message) Write-Host "ℹ️ $Message" -ForegroundColor Yellow }
function Write-Progress-Log { param([string]$Message) Write-Host "🔄 $Message" -ForegroundColor Cyan }
function Write-Warning-Log { param([string]$Message) Write-Host "⚠️ $Message" -ForegroundColor Yellow }
function Write-Step-Log { param([string]$Message) Write-Host "$Message" -ForegroundColor White }
function Write-Header-Log { param([string]$Message) Write-Host "$Message" -ForegroundColor Cyan }

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Header-Log "🚀 Review Gate V2 - Windows Installation"
Write-Header-Log "========================================="
Write-Host ""

# Check if running on Windows
if ($PSVersionTable.Platform -and $PSVersionTable.Platform -ne "Win32NT") {
    Write-Error-Log "This script is designed for Windows only"
    exit 1
}

# Check for admin privileges for package manager installation
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Warning-Log "Administrator privileges recommended for package installations"
    Write-Info-Log "Some features may require manual installation"
}

# Check if Scoop is installed, if not install it
Write-Progress-Log "Checking for Scoop package manager..."
if (-not (Get-Command scoop -ErrorAction SilentlyContinue)) {
    Write-Progress-Log "Installing Scoop..."
    try {
        Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
        Invoke-Expression (New-Object System.Net.WebClient).DownloadString('https://get.scoop.sh')
        Write-Success-Log "Scoop installed successfully"
    } catch {
        Write-Error-Log "Failed to install Scoop automatically"
        Write-Info-Log "Please install Scoop manually from https://scoop.sh"
        Write-Info-Log "Then run this script again"
        exit 1
    }
} else {
    Write-Success-Log "Scoop already installed"
}

# Install SoX for speech-to-text
Write-Progress-Log "Installing SoX for speech-to-text..."
if (-not (Get-Command sox -ErrorAction SilentlyContinue)) {
    try {
        scoop bucket add extras
        scoop install sox
        Write-Success-Log "SoX installed successfully"
    } catch {
        Write-Warning-Log "Failed to install SoX via Scoop"
        Write-Info-Log "Please install SoX manually from http://sox.sourceforge.net/"
    }
} else {
    Write-Success-Log "SoX already installed"
}

# Validate SoX installation and microphone access
Write-Progress-Log "Validating SoX and microphone setup..."
if (Get-Command sox -ErrorAction SilentlyContinue) {
    try {
        $soxVersion = & sox --version 2>$null | Select-Object -First 1
        Write-Success-Log "SoX found: $soxVersion"
        
        # Test microphone access (quick test)
        Write-Progress-Log "Testing microphone access..."
        $testFile = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "sox_test_$([System.Guid]::NewGuid().ToString('N').Substring(0,8)).wav")
        
        $testProcess = Start-Process -FilePath "sox" -ArgumentList @("-d", "-r", "16000", "-c", "1", $testFile, "trim", "0", "0.1") -WindowStyle Hidden -PassThru -Wait -NoNewWindow
        
        # Clean up test file
        if (Test-Path $testFile) {
            Remove-Item $testFile -Force -ErrorAction SilentlyContinue
        }
        
        if ($testProcess.ExitCode -eq 0) {
            Write-Success-Log "Microphone access test successful"
        } else {
            Write-Warning-Log "Microphone test failed - speech features may not work"
            Write-Info-Log "Common fixes:"
            Write-Step-Log "   • Grant microphone permissions to PowerShell/Terminal"
            Write-Step-Log "   • Check Windows Settings > Privacy > Microphone"
            Write-Step-Log "   • Make sure no other apps are using the microphone"
        }
    } catch {
        Write-Warning-Log "SoX validation error: $($_.Exception.Message)"
    }
} else {
    Write-Error-Log "SoX installation failed or not found"
    Write-Info-Log "Speech-to-text features will be disabled"
    Write-Info-Log "Try installing manually: scoop install sox"
}

# Check if Python 3 is available
Write-Progress-Log "Checking Python installation..."
if (-not (Get-Command python -ErrorAction SilentlyContinue) -and -not (Get-Command python3 -ErrorAction SilentlyContinue)) {
    Write-Error-Log "Python 3 is required but not installed"
    Write-Info-Log "Would you like to install Python 3 using Scoop? (y/n)"
    $userInput = Read-Host
    if ($userInput -eq "y") {
        Write-Progress-Log "Installing Python 3 using Scoop..."
        try {
            scoop install python
            Write-Success-Log "Python 3 installed successfully using Scoop"
        } catch {
            Write-Error-Log "Failed to install Python 3 via Scoop"
            Write-Info-Log "Please install Python 3 manually from https://python.org or Microsoft Store"
            Write-Info-Log "Then run this script again"
            exit 1
        }
    } else {
        Write-Info-Log "Please install Python 3 from https://python.org or Microsoft Store"
        Write-Info-Log "Then run this script again"
        exit 1
    }
} else {
    $pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }
    $testOutput = & $pythonCmd -c "print('hello world')"
    if ($testOutput -eq "hello world") {
        Write-Success-Log "Python found and working correctly"
    } else {
        Write-Error-Log "Python is installed but not working correctly"
        exit 1
    }
}

# Create global Cursor extensions directory
$CursorExtensionsDir = Join-Path $env:USERPROFILE "cursor-extensions"
$ReviewGateDir = Join-Path $CursorExtensionsDir "review-gate-v2"

Write-Progress-Log "Creating global installation directory..."
New-Item -Path $ReviewGateDir -ItemType Directory -Force | Out-Null

# Copy MCP server files
Write-Progress-Log "Copying MCP server files..."
$mcpServerSrc = Join-Path $ScriptDir "review_gate_v2_mcp.py"
$requirementsSrc = Join-Path $ScriptDir "requirements_simple.txt"

if (Test-Path $mcpServerSrc) {
    Copy-Item $mcpServerSrc $ReviewGateDir -Force
} else {
    Write-Error-Log "MCP server file not found: $mcpServerSrc"
    exit 1
}

if (Test-Path $requirementsSrc) {
    Copy-Item $requirementsSrc $ReviewGateDir -Force
} else {
    Write-Error-Log "Requirements file not found: $requirementsSrc"
    exit 1
}

# Create Python virtual environment
Write-Progress-Log "Creating Python virtual environment..."
Set-Location $ReviewGateDir

# Check if venv module is available
if (-not (Get-Command python -ErrorAction SilentlyContinue | Where-Object { $_.Source -like "*venv*" })) {
    Write-Warning-Log "venv module not found. Installing venv..."
    & $pythonCmd -m ensurepip
    & $pythonCmd -m pip install --upgrade pip
    & $pythonCmd -m pip install virtualenv
}

# Create virtual environment
& $pythonCmd -m venv venv

# Activate virtual environment and install dependencies
Write-Progress-Log "Installing Python dependencies..."
$venvActivate = Join-Path $ReviewGateDir "venv\Scripts\Activate.ps1"
$venvPython = Join-Path $ReviewGateDir "venv\Scripts\python.exe"

if (Test-Path $venvActivate) {
    & $venvActivate
    & $venvPython -m pip install --upgrade pip
    
    # Install core dependencies first
    Write-Progress-Log "Installing core dependencies (mcp, pillow)..."
    & $venvPython -m pip install mcp>=1.9.2 Pillow>=10.0.0 asyncio typing-extensions>=4.14.0
    
    # Install faster-whisper with error handling for Windows
    Write-Progress-Log "Installing faster-whisper for speech-to-text..."
    try {
        & $venvPython -m pip install faster-whisper>=1.0.0
        Write-Success-Log "faster-whisper installed successfully"
    } catch {
        Write-Warning-Log "faster-whisper installation failed - trying alternative approach"
        try {
            # Try CPU-only installation for Windows compatibility
            & $venvPython -m pip install faster-whisper>=1.0.0 --no-deps
            & $venvPython -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
            Write-Success-Log "faster-whisper installed with CPU-only dependencies"
        } catch {
            Write-Error-Log "faster-whisper installation failed"
            Write-Info-Log "Speech-to-text will be disabled"
            Write-Info-Log "Common fixes:"
            Write-Step-Log "   • Install Visual Studio Build Tools"
            Write-Step-Log "   • Or use Windows Subsystem for Linux (WSL)"
            Write-Step-Log "   • You can manually install later: pip install faster-whisper"
        }
    }
    
    deactivate
} else {
    Write-Error-Log "Failed to create virtual environment"
    exit 1
}

Write-Success-Log "Python environment created and dependencies installed"

# Create MCP configuration
$CursorMcpFile = Join-Path $env:USERPROFILE ".cursor\mcp.json"
Write-Progress-Log "Configuring MCP servers..."
$CursorDir = Join-Path $env:USERPROFILE ".cursor"
New-Item -Path $CursorDir -ItemType Directory -Force | Out-Null

# Backup existing MCP configuration if it exists
if (Test-Path $CursorMcpFile) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupFile = "$CursorMcpFile.backup.$timestamp"
    Write-Info-Log "Backing up existing MCP configuration to: $BackupFile"
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
        Write-Success-Log "Found existing MCP servers, merging configurations"
    } catch {
        Write-Warning-Log "Existing MCP config has invalid JSON format"
        Write-Info-Log "Creating new configuration file"
        $existingServers = @{}
    }
} else {
    Write-Info-Log "Creating new MCP configuration file"
    $existingServers = @{}
}

# Create simplified MCP configuration
Write-Progress-Log "Creating MCP configuration..."

# Use simplified approach - create basic config with just Review Gate V2
if (Test-Path $CursorMcpFile) {
    Write-Success-Log "Found existing MCP configuration, will merge servers"
    $hasExistingServers = $true
}
else {
    Write-Info-Log "Creating new MCP configuration file"
    $hasExistingServers = $false
}

# Create the configuration using simplified PowerShell approach
$pythonPath = $venvPython -replace '\\', '/'
$mcpScriptPath = (Join-Path $ReviewGateDir "review_gate_v2_mcp.py") -replace '\\', '/'
$reviewGateDirPath = $ReviewGateDir -replace '\\', '/'

$reviewGateServerConfig = @"
    "review-gate-v2": {
      "command": "$pythonPath",
      "args": ["$mcpScriptPath"],
      "env": {
        "PYTHONPATH": "$reviewGateDirPath",
        "PYTHONUNBUFFERED": "1",
        "REVIEW_GATE_MODE": "cursor_integration"
      }
    }
"@

# Create basic MCP configuration with Review Gate V2
$mcpConfig = @"
{
  "mcpServers": {
$reviewGateServerConfig
  }
}
"@

try {
    Set-Content -Path $CursorMcpFile -Value $mcpConfig -Encoding UTF8
    Write-Success-Log "MCP configuration updated successfully at: $CursorMcpFile"
    Write-Header-Log "Total MCP servers configured: 1"
    Write-Step-Log "  • review-gate-v2 (Review Gate V2)"
} catch {
    Write-Error-Log "Failed to create MCP configuration"
    if (Test-Path $BackupFile) {
        Write-Progress-Log "Restoring from backup..."
        Copy-Item $BackupFile $CursorMcpFile -Force
        Write-Success-Log "Backup restored"
    } else {
        Write-Error-Log "No backup available, installation failed"
        exit 1
    }
}

# Test MCP server
Write-Progress-Log "Testing MCP server..."
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
        Write-Success-Log "MCP server test successful"
    } else {
        Write-Warning-Log "MCP server test inconclusive (may be normal)"
    }
} catch {
    Write-Warning-Log "MCP server test failed (may be normal)"
}

# Install Cursor extension
$ExtensionFile = Join-Path $ScriptDir "cursor-extension\review-gate-v2-2.7.3.vsix"
if (Test-Path $ExtensionFile) {
    Write-Progress-Log "Installing Cursor extension..."
    
    # Copy extension to installation directory
    Copy-Item $ExtensionFile $ReviewGateDir -Force
    
    # Try automated installation first
    $ExtensionInstalled = $false
    $cursorPaths = @(
        "${env:ProgramFiles}\Cursor\resources\app\bin\cursor.cmd",
        "${env:LOCALAPPDATA}\Programs\cursor\resources\app\bin\cursor.cmd",
        "${env:ProgramFiles(x86)}\Cursor\resources\app\bin\cursor.cmd"
    )
    
    foreach ($cursorCmd in $cursorPaths) {
        if (Test-Path $cursorCmd) {
            Write-Progress-Log "Attempting automated extension installation..."
            try {
                & $cursorCmd --install-extension $ExtensionFile | Out-Null
                Write-Success-Log "Extension installed automatically via command line"
                $ExtensionInstalled = $true
                break
            } catch {
                Write-Warning-Log "Automated installation failed: $($_.Exception.Message)"
            }
        }
    }
    
    # If automated installation failed, provide manual instructions
    if (-not $ExtensionInstalled) {
        Write-Header-Log "MANUAL EXTENSION INSTALLATION REQUIRED:"
        Write-Info-Log "Please complete the extension installation manually:"
        Write-Step-Log "1. Open Cursor IDE"
        Write-Step-Log "2. Press Ctrl+Shift+P"
        Write-Step-Log "3. Type 'Extensions: Install from VSIX'"
        Write-Step-Log "4. Select: $ReviewGateDir\review-gate-v2-2.7.3.vsix"
        Write-Step-Log "5. Restart Cursor when prompted"
        Write-Host ""
        
        # Try to open Cursor if available
        $cursorExePaths = @(
            "${env:ProgramFiles}\Cursor\Cursor.exe",
            "${env:LOCALAPPDATA}\Programs\cursor\Cursor.exe",
            "${env:ProgramFiles(x86)}\Cursor\Cursor.exe"
        )
        
        $cursorFound = $false
        foreach ($path in $cursorExePaths) {
            if (Test-Path $path) {
                Write-Progress-Log "Opening Cursor IDE..."
                Start-Process $path -WorkingDirectory (Get-Location)
                $cursorFound = $true
                break
            }
        }
        
        if (-not $cursorFound) {
            Write-Info-Log "Please open Cursor IDE manually"
        }
    }
} else {
    Write-Error-Log "Extension file not found: $ExtensionFile"
    Write-Info-Log "Please ensure the extension is built in cursor-extension\ directory"
    Write-Info-Log "Or install manually from the Cursor Extensions marketplace"
}

# Install global rule (optional) - Windows-specific directory
$CursorRulesDir = Join-Path $env:APPDATA "Cursor\User\rules"
$ruleFile = Join-Path $ScriptDir "ReviewGate.mdc"
if (Test-Path $ruleFile) {
    Write-Progress-Log "Installing global rule..."
    New-Item -Path $CursorRulesDir -ItemType Directory -Force | Out-Null
    Copy-Item $ruleFile $CursorRulesDir -Force
    Write-Success-Log "Global rule installed to: $CursorRulesDir"
} elseif (Test-Path $ruleFile) {
    Write-Warning-Log "Could not determine Cursor rules directory"
    Write-Info-Log "Global rule available at: $ruleFile"
}

# Clean up any existing temp files
Write-Progress-Log "Cleaning up temporary files..."
$tempPath = [System.IO.Path]::GetTempPath()
Get-ChildItem $tempPath -Filter "review_gate_*" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem $tempPath -Filter "mcp_response*" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Success-Log "Review Gate V2 Installation Complete!"
Write-Header-Log "======================================="
Write-Host ""
Write-Header-Log "Installation Summary:"
Write-Step-Log "   • MCP Server: $ReviewGateDir"
Write-Step-Log "   • MCP Config: $CursorMcpFile"
Write-Step-Log "   • Extension: $ReviewGateDir\review-gate-v2-2.7.3.vsix"
Write-Step-Log "   • Global Rule: $CursorRulesDir\ReviewGate.mdc"
Write-Host ""
Write-Header-Log "Testing Your Installation:"
Write-Step-Log "1. Restart Cursor completely"
Write-Info-Log "2. Press Ctrl+Shift+R to test manual trigger"
Write-Info-Log "3. Or ask Cursor Agent: 'Use the review_gate_chat tool'"
Write-Host ""
Write-Header-Log "Speech-to-Text Features:"
Write-Step-Log "   • Click microphone icon in popup"
Write-Step-Log "   • Speak clearly for 2-3 seconds"
Write-Step-Log "   • Click stop to transcribe"
Write-Host ""
Write-Header-Log "Image Upload Features:"
Write-Step-Log "   • Click camera icon in popup"
Write-Step-Log "   • Select images (PNG, JPG, etc.)"
Write-Step-Log "   • Images are included in response"
Write-Host ""
Write-Header-Log "Troubleshooting:"
Write-Info-Log "   • Logs: Get-Content ([System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), 'review_gate_v2.log')) -Wait"
Write-Info-Log "   • Test SoX: sox --version"
Write-Info-Log "   • Browser Console: F12 in Cursor"
Write-Host ""
Write-Success-Log "Enjoy your voice-activated Review Gate!"

# Final verification
Write-Progress-Log "Final verification..."
$mcpServerFile = Join-Path $ReviewGateDir "review_gate_v2_mcp.py"
$venvDir = Join-Path $ReviewGateDir "venv"

if ((Test-Path $mcpServerFile) -and (Test-Path $CursorMcpFile) -and (Test-Path $venvDir)) {
    Write-Success-Log "All components installed successfully"
    exit 0
} else {
    Write-Error-Log "Some components may not have installed correctly"
    Write-Info-Log "Please check the installation manually"
    exit 1
}

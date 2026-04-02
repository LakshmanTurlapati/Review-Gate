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
$RepoRoot = Split-Path -Parent $ScriptDir
$ReleaseHelper = Join-Path $RepoRoot "scripts\package_review_gate_vsix.py"
$SmokeMode = $env:REVIEW_GATE_SMOKE -eq "1"
$SkipDepInstall = $SmokeMode -or ($env:REVIEW_GATE_SKIP_DEP_INSTALL -eq "1")
$SkipExtensionInstall = $SmokeMode -or ($env:REVIEW_GATE_SKIP_EXTENSION_INSTALL -eq "1")
$SkipServerSmoke = $SmokeMode -or ($env:REVIEW_GATE_SKIP_SERVER_SMOKE -eq "1")
$IsWindowsPlatform = (-not $PSVersionTable.Platform) -or ($PSVersionTable.Platform -eq "Win32NT")

Write-Header-Log "🚀 Review Gate V2 - Windows Installation"
Write-Header-Log "========================================="
Write-Host ""

# Check if running on Windows
if (-not $IsWindowsPlatform -and -not $SmokeMode) {
    Write-Error-Log "This script is designed for Windows only"
    exit 1
}

if ($SmokeMode) {
    if (-not $env:REVIEW_GATE_TEST_HOME) {
        Write-Error-Log "REVIEW_GATE_TEST_HOME is required when REVIEW_GATE_SMOKE=1"
        exit 1
    }
    if (-not $env:REVIEW_GATE_TEST_INSTALL_DIR) {
        Write-Error-Log "REVIEW_GATE_TEST_INSTALL_DIR is required when REVIEW_GATE_SMOKE=1"
        exit 1
    }

    $env:USERPROFILE = [System.IO.Path]::GetFullPath($env:REVIEW_GATE_TEST_HOME)
    $env:APPDATA = Join-Path $env:USERPROFILE "AppData\Roaming"
    $env:LOCALAPPDATA = Join-Path $env:USERPROFILE "AppData\Local"
    New-Item -Path $env:USERPROFILE -ItemType Directory -Force | Out-Null
    New-Item -Path $env:APPDATA -ItemType Directory -Force | Out-Null
    New-Item -Path $env:LOCALAPPDATA -ItemType Directory -Force | Out-Null
    Write-Info-Log "Smoke mode enabled with USERPROFILE redirected to: $env:USERPROFILE"
    Write-Info-Log "Smoke install root redirected to: $env:REVIEW_GATE_TEST_INSTALL_DIR"
}

# Check for admin privileges for package manager installation
if ($IsWindowsPlatform) {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isAdmin) {
        Write-Warning-Log "Administrator privileges recommended for package installations"
        Write-Info-Log "Some features may require manual installation"
    }
} elseif ($SmokeMode) {
    Write-Info-Log "Skipping Windows privilege checks in smoke mode"
}

# Check if Scoop is installed, if not install it
Write-Progress-Log "Checking for Scoop package manager..."
if ($SkipDepInstall) {
    Write-Info-Log "Skipping package-manager dependency installation"
} elseif (-not (Get-Command scoop -ErrorAction SilentlyContinue)) {
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
if ($SkipDepInstall) {
    Write-Info-Log "Skipping SoX installation in smoke mode"
} elseif (-not (Get-Command sox -ErrorAction SilentlyContinue)) {
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
if ($SkipDepInstall) {
    Write-Info-Log "Skipping SoX validation in smoke mode"
} elseif (Get-Command sox -ErrorAction SilentlyContinue) {
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

function Get-ReleaseField {
    param([string]$Field)

    $value = & $pythonCmd $ReleaseHelper --field $Field
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to read release metadata field '$Field'"
    }
    return $value.Trim()
}

# Create global Cursor extensions directory
if ($SmokeMode) {
    $ReviewGateDir = [System.IO.Path]::GetFullPath($env:REVIEW_GATE_TEST_INSTALL_DIR)
    $CursorExtensionsDir = Split-Path -Parent $ReviewGateDir
} else {
    $CursorExtensionsDir = Join-Path $env:USERPROFILE "cursor-extensions"
    $ReviewGateDir = Join-Path $CursorExtensionsDir "review-gate-v2"
}

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

# Create virtual environment, with a non-smoke fallback for older Python installs.
$venvCreated = $false
try {
    & $pythonCmd -m venv venv
    $venvCreated = $LASTEXITCODE -eq 0
} catch {
    $venvCreated = $false
}

if (-not $venvCreated -and -not $SkipDepInstall) {
    Write-Warning-Log "venv module bootstrap failed. Installing virtualenv..."
    & $pythonCmd -m ensurepip
    & $pythonCmd -m pip install --upgrade pip
    & $pythonCmd -m pip install virtualenv
    & $pythonCmd -m venv venv
    $venvCreated = $LASTEXITCODE -eq 0
}

if (-not $venvCreated) {
    Write-Error-Log "Failed to create virtual environment"
    exit 1
}

$venvDir = Join-Path $ReviewGateDir "venv"

# Activate virtual environment and install dependencies
$venvPython = @(
    (Join-Path $venvDir "Scripts\python.exe"),
    (Join-Path $venvDir "bin\python")
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($venvPython) {
    if ($SkipDepInstall) {
        Write-Info-Log "Skipping Python dependency installation"
    } else {
        Write-Progress-Log "Installing Python dependencies..."
        & $venvPython -m pip install --upgrade pip
        
        # Install core dependencies first
        Write-Progress-Log "Installing core dependencies (mcp, pillow)..."
        & $venvPython -m pip install "mcp>=1.9.2" "Pillow>=10.0.0" "asyncio" "typing-extensions>=4.14.0"
        
        # Install faster-whisper with error handling for Windows
        Write-Progress-Log "Installing faster-whisper for speech-to-text..."
        try {
            & $venvPython -m pip install "faster-whisper>=1.0.0"
            Write-Success-Log "faster-whisper installed successfully"
        } catch {
            Write-Warning-Log "faster-whisper installation failed - trying alternative approach"
            try {
                # Try CPU-only installation for Windows compatibility
                & $venvPython -m pip install "faster-whisper>=1.0.0" --no-deps
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
    }
} else {
    Write-Error-Log "Virtual environment Python executable not found"
    exit 1
}

Write-Success-Log "Python environment created and dependencies installed"

# Create MCP configuration
$CursorMcpFile = Join-Path $env:USERPROFILE ".cursor\mcp.json"
Write-Progress-Log "Configuring MCP servers..."
$CursorDir = Join-Path $env:USERPROFILE ".cursor"
New-Item -Path $CursorDir -ItemType Directory -Force | Out-Null
$HelperScript = Join-Path $ScriptDir "update_mcp_config.py"
$TemplateFile = Join-Path $ScriptDir "mcp.json"

if (-not (Test-Path $HelperScript)) {
    Write-Error-Log "MCP config helper not found: $HelperScript"
    exit 1
}

if (-not (Test-Path $TemplateFile)) {
    Write-Error-Log "MCP config template not found: $TemplateFile"
    exit 1
}

# Backup existing MCP configuration if it exists
$BackupFile = $null
$HadExistingMcpConfig = Test-Path $CursorMcpFile
if (Test-Path $CursorMcpFile) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupFile = "$CursorMcpFile.backup.$timestamp"
    Write-Info-Log "Backing up existing MCP configuration to: $BackupFile"
    Copy-Item $CursorMcpFile $BackupFile -Force
} else {
    Write-Info-Log "Creating new MCP configuration file"
}

# Run update_mcp_config.py merge to preserve existing MCP servers
Write-Progress-Log "Updating MCP configuration..."
try {
    & $pythonCmd $HelperScript merge `
        --config $CursorMcpFile `
        --template $TemplateFile `
        --server-name review-gate-v2 `
        --install-dir $ReviewGateDir `
        --python-cmd $venvPython

    if ($LASTEXITCODE -ne 0) {
        throw "update_mcp_config.py exited with code $LASTEXITCODE"
    }

    Write-Success-Log "MCP configuration updated successfully at: $CursorMcpFile"
} catch {
    Write-Error-Log "Failed to update MCP configuration: $($_.Exception.Message)"
    if (Test-Path $BackupFile) {
        Write-Progress-Log "Restoring from backup..."
        Copy-Item $BackupFile $CursorMcpFile -Force
        Write-Success-Log "Backup restored"
    } elseif (-not $HadExistingMcpConfig -and (Test-Path $CursorMcpFile)) {
        Remove-Item $CursorMcpFile -Force -ErrorAction SilentlyContinue
    } else {
        Write-Error-Log "No backup available for MCP configuration restore"
    }
    exit 1
}

# Test MCP server
Write-Progress-Log "Testing MCP server..."
Set-Location $ReviewGateDir
if ($SkipServerSmoke) {
    Write-Info-Log "Skipping MCP server smoke test"
} else {
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
}

# Install Cursor extension
if (-not (Test-Path $ReleaseHelper)) {
    Write-Error-Log "Release helper not found: $ReleaseHelper"
    exit 1
}

$ExtensionBaseName = Get-ReleaseField "artifact_basename"
$CanonicalVsixRepoPath = (Get-ReleaseField "canonical_vsix_path") -replace "/", [System.IO.Path]::DirectorySeparatorChar
$RuleRepoPath = (Get-ReleaseField "rule_path") -replace "/", [System.IO.Path]::DirectorySeparatorChar
$ExtensionFile = Join-Path $RepoRoot $CanonicalVsixRepoPath
$InstalledExtensionFile = Join-Path $ReviewGateDir $ExtensionBaseName
if (Test-Path $ExtensionFile) {
    Write-Progress-Log "Installing Cursor extension..."
    
    # Copy extension to installation directory
    Copy-Item $ExtensionFile $InstalledExtensionFile -Force
    
    # Try automated installation first
    $ExtensionInstalled = $false
    if ($SkipExtensionInstall) {
        Write-Info-Log "Skipping automated Cursor extension installation"
    } else {
        $cursorPaths = @(
            "${env:ProgramFiles}\Cursor\resources\app\bin\cursor.cmd",
            "${env:LOCALAPPDATA}\Programs\cursor\resources\app\bin\cursor.cmd",
            "${env:ProgramFiles(x86)}\Cursor\resources\app\bin\cursor.cmd"
        )
        
        foreach ($cursorCmd in $cursorPaths) {
            if (Test-Path $cursorCmd) {
                Write-Progress-Log "Attempting automated extension installation..."
                try {
                    & $cursorCmd --install-extension $InstalledExtensionFile | Out-Null
                    Write-Success-Log "Extension installed automatically via command line"
                    $ExtensionInstalled = $true
                    break
                } catch {
                    Write-Warning-Log "Automated installation failed: $($_.Exception.Message)"
                }
            }
        }
    }
    
    # If automated installation failed, provide manual instructions
    if (-not $ExtensionInstalled -and -not $SkipExtensionInstall) {
        Write-Header-Log "MANUAL EXTENSION INSTALLATION REQUIRED:"
        Write-Info-Log "Please complete the extension installation manually:"
        Write-Step-Log "1. Open Cursor IDE"
        Write-Step-Log "2. Press Ctrl+Shift+P"
        Write-Step-Log "3. Type 'Extensions: Install from VSIX'"
        Write-Step-Log "4. Select: $InstalledExtensionFile"
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
    Write-Error-Log "Canonical extension file not found: $ExtensionFile"
    Write-Info-Log "Package the canonical release artifact with: cd $ScriptDir\cursor-extension; npm run package"
    exit 1
}

# Install global rule (optional) - Windows-specific directory
$CursorRulesDir = Join-Path $env:APPDATA "Cursor\User\rules"
$RuleFileName = Split-Path -Leaf $RuleRepoPath
$RuleSourceFile = Join-Path $RepoRoot $RuleRepoPath
$InstalledRuleFile = Join-Path $CursorRulesDir $RuleFileName
if (Test-Path $RuleSourceFile) {
    Write-Progress-Log "Installing global rule..."
    New-Item -Path $CursorRulesDir -ItemType Directory -Force | Out-Null
    Copy-Item $RuleSourceFile $InstalledRuleFile -Force
    Write-Success-Log "Global rule installed to: $InstalledRuleFile"
} else {
    Write-Warning-Log "Global rule file not found: $RuleSourceFile"
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
Write-Step-Log "   • Extension: $InstalledExtensionFile"
Write-Step-Log "   • Global Rule: $InstalledRuleFile"
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

# OhSee Windows Service Setup Script
# This script sets up OhSee backend as a Windows service using NSSM

param(
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot "backend"
$ServiceName = "OhSeeBackend"

Write-Host "🔍 OhSee Windows Service Setup" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "❌ This script must be run as Administrator" -ForegroundColor Red
    Write-Host "   Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Handle uninstall
if ($Uninstall) {
    Write-Host "🗑️  Uninstalling OhSee service..." -ForegroundColor Yellow
    
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        sc.exe delete $ServiceName
        Write-Host "✓ Service uninstalled" -ForegroundColor Green
    } else {
        Write-Host "ℹ️  Service not found" -ForegroundColor Yellow
    }
    exit 0
}

# Check if backend directory exists
if (-not (Test-Path $BackendDir)) {
    Write-Host "❌ Error: Backend directory not found at $BackendDir" -ForegroundColor Red
    exit 1
}

# Find Python
$PythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonPath) {
    $PythonPath = (Get-Command python3 -ErrorAction SilentlyContinue).Source
}

if (-not $PythonPath) {
    Write-Host "❌ Error: Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Find uvicorn
$UvicornPath = (Get-Command uvicorn -ErrorAction SilentlyContinue).Source
if (-not $UvicornPath) {
    Write-Host "❌ Error: uvicorn not found. Please install: pip install uvicorn" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Found Python: $PythonPath" -ForegroundColor Green
Write-Host "✓ Found uvicorn: $UvicornPath" -ForegroundColor Green
Write-Host ""

# Check for NSSM
$NssmPath = (Get-Command nssm -ErrorAction SilentlyContinue).Source
if (-not $NssmPath) {
    Write-Host "⚠️  NSSM not found. Installing NSSM..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "NSSM (Non-Sucking Service Manager) is required to run OhSee as a Windows service." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Installation options:" -ForegroundColor Cyan
    Write-Host "  1. Using Chocolatey: choco install nssm" -ForegroundColor White
    Write-Host "  2. Using Scoop: scoop install nssm" -ForegroundColor White
    Write-Host "  3. Manual download: https://nssm.cc/download" -ForegroundColor White
    Write-Host ""
    
    $choice = Read-Host "Install NSSM using Chocolatey? (y/N)"
    if ($choice -eq 'y' -or $choice -eq 'Y') {
        # Check if Chocolatey is installed
        $ChocoPath = (Get-Command choco -ErrorAction SilentlyContinue).Source
        if (-not $ChocoPath) {
            Write-Host "Installing Chocolatey..." -ForegroundColor Yellow
            Set-ExecutionPolicy Bypass -Scope Process -Force
            [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
            Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        }
        
        choco install nssm -y
        $NssmPath = (Get-Command nssm -ErrorAction SilentlyContinue).Source
        
        if (-not $NssmPath) {
            Write-Host "❌ NSSM installation failed. Please install manually." -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "❌ NSSM is required. Please install it and run this script again." -ForegroundColor Red
        exit 1
    }
}

Write-Host "✓ Found NSSM: $NssmPath" -ForegroundColor Green
Write-Host ""

# Remove existing service if it exists
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "⚠️  Existing service found. Removing..." -ForegroundColor Yellow
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    & nssm remove $ServiceName confirm
    Start-Sleep -Seconds 2
}

# Install the service
Write-Host "📝 Installing OhSee service..." -ForegroundColor Cyan
& nssm install $ServiceName $UvicornPath "main:app" "--host" "0.0.0.0" "--port" "8000"

# Configure service
Write-Host "⚙️  Configuring service..." -ForegroundColor Cyan
& nssm set $ServiceName AppDirectory $BackendDir
& nssm set $ServiceName DisplayName "OhSee Backend"
& nssm set $ServiceName Description "OhSee AI Assistant Backend Service"
& nssm set $ServiceName Start SERVICE_AUTO_START
& nssm set $ServiceName AppStdout "$env:TEMP\ohsee-backend.log"
& nssm set $ServiceName AppStderr "$env:TEMP\ohsee-backend-error.log"

# Load .env file if it exists
$EnvFile = Join-Path $BackendDir ".env"
if (Test-Path $EnvFile) {
    Write-Host "✓ Found .env file, loading environment variables..." -ForegroundColor Green
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            & nssm set $ServiceName AppEnvironmentExtra "$key=$value"
        }
    }
}

# Start the service
Write-Host "🚀 Starting service..." -ForegroundColor Cyan
Start-Service -Name $ServiceName

# Check status
Start-Sleep -Seconds 3
$service = Get-Service -Name $ServiceName
if ($service.Status -eq 'Running') {
    Write-Host ""
    Write-Host "✅ OhSee backend is now running as a Windows service!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Service Status:" -ForegroundColor Cyan
    Write-Host "   • Service Name: $ServiceName" -ForegroundColor White
    Write-Host "   • Status: $($service.Status)" -ForegroundColor White
    Write-Host "   • Backend URL: http://localhost:8000" -ForegroundColor White
    Write-Host "   • Logs: $env:TEMP\ohsee-backend.log" -ForegroundColor White
    Write-Host "   • Errors: $env:TEMP\ohsee-backend-error.log" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "⚠️  Service may not have started. Status: $($service.Status)" -ForegroundColor Yellow
    Write-Host "   Check logs at: $env:TEMP\ohsee-backend-error.log" -ForegroundColor Yellow
    exit 1
}

# Ask about Task Scheduler wake
Write-Host "⏰ Task Scheduler Wake (Optional)" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Would you like information about enabling wake scheduling?" -ForegroundColor Yellow
Write-Host "This allows Windows to wake from sleep to run scheduled tasks." -ForegroundColor Yellow
Write-Host ""
$wakeChoice = Read-Host "Show wake scheduling information? (y/N)"

if ($wakeChoice -eq 'y' -or $wakeChoice -eq 'Y') {
    Write-Host ""
    Write-Host "📝 Windows Task Scheduler Wake Setup:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "The OhSee backend can create Task Scheduler entries that wake your computer." -ForegroundColor White
    Write-Host ""
    Write-Host "To enable wake scheduling:" -ForegroundColor Cyan
    Write-Host "  1. Open Task Scheduler (taskschd.msc)" -ForegroundColor White
    Write-Host "  2. Find OhSee-related tasks" -ForegroundColor White
    Write-Host "  3. Edit task → Conditions → Check 'Wake the computer to run this task'" -ForegroundColor White
    Write-Host ""
    Write-Host "⚠️  Note: Wake scheduling requires:" -ForegroundColor Yellow
    Write-Host "   • Administrator privileges" -ForegroundColor White
    Write-Host "   • Computer plugged in (recommended)" -ForegroundColor White
    Write-Host "   • Wake timers enabled in Power Options" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "ℹ️  Wake scheduling not configured." -ForegroundColor Yellow
    Write-Host "   Scheduled tasks will only run when your computer is awake." -ForegroundColor White
}

Write-Host ""
Write-Host "🎉 Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Cyan
Write-Host "  • View service:  Get-Service $ServiceName" -ForegroundColor White
Write-Host "  • Stop service:  Stop-Service $ServiceName" -ForegroundColor White
Write-Host "  • Start service: Start-Service $ServiceName" -ForegroundColor White
Write-Host "  • Restart:       Restart-Service $ServiceName" -ForegroundColor White
Write-Host "  • Uninstall:     .\setup-windows-service.ps1 -Uninstall" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Start the frontend: cd frontend && npm run dev" -ForegroundColor White
Write-Host "  2. Open http://localhost:5173" -ForegroundColor White
Write-Host "  3. Schedule tasks in the Tasks panel" -ForegroundColor White
Write-Host ""

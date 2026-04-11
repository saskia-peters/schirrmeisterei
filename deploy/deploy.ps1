# TicketSystem – one-command deployment script (Windows PowerShell)
#
# Prerequisites: Docker Desktop or Podman Desktop for Windows
#
# Usage:
#   .\deploy.ps1              Start the stack (generates .env on first run)
#   .\deploy.ps1 stop         Stop the stack
#   .\deploy.ps1 update       Pull latest images and restart
#   .\deploy.ps1 logs         Tail logs
#   .\deploy.ps1 status       Show container status

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "update", "logs", "status")]
    [string]$Command = "start"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# ── Detect container runtime ─────────────────────────────────────────────────

$COMPOSE = $null

if (Get-Command "docker" -ErrorAction SilentlyContinue) {
    $COMPOSE = "docker compose"
    Write-Host "Using: Docker ($COMPOSE)"
}
elseif (Get-Command "podman" -ErrorAction SilentlyContinue) {
    $COMPOSE = "podman compose"
    Write-Host "Using: Podman ($COMPOSE)"
}
else {
    Write-Error "Docker Desktop or Podman Desktop is required. Install one and try again."
    exit 1
}

function Invoke-Compose {
    param([string[]]$Args)
    $cmd = "$COMPOSE $($Args -join ' ')"
    Invoke-Expression $cmd
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

# ── Helper: generate random string ───────────────────────────────────────────

function New-RandomString {
    $bytes = New-Object byte[] 48
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return [Convert]::ToBase64String($bytes) -replace '[/+=]','' | ForEach-Object { $_.Substring(0, [Math]::Min(64, $_.Length)) }
}

# ── Generate .env on first run ────────────────────────────────────────────────

function Initialize-Env {
    if (Test-Path ".env") {
        Write-Host ".env already exists - skipping generation."
        return
    }

    Write-Host "Generating .env with random secrets..."
    $dbPass = New-RandomString
    $secretKey = New-RandomString
    $timestamp = Get-Date -Format "o"

    @"
# TicketSystem configuration - generated $timestamp
# Edit these values as needed, then restart with: .\deploy.ps1

# Database
POSTGRES_USER=ticketsystem
POSTGRES_PASSWORD=$dbPass
POSTGRES_DB=ticketsystem

# Application secret (used for JWT signing)
SECRET_KEY=$secretKey

# Ports exposed on the host
FRONTEND_PORT=8080
BACKEND_PORT=8000

# CORS allowed origins (JSON array)
ALLOWED_ORIGINS=["http://localhost:8080"]

# Max file upload size in MB
MAX_UPLOAD_SIZE_MB=10

# Image version tag (default: latest)
# TICKETSYSTEM_VERSION=latest
"@ | Set-Content -Path ".env" -Encoding UTF8

    Write-Host "Created .env - review it before first start if needed."
}

# ── Commands ──────────────────────────────────────────────────────────────────

function Start-Stack {
    Initialize-Env
    Write-Host "Pulling latest images..."
    Invoke-Compose @("pull")
    Write-Host "Starting TicketSystem..."
    Invoke-Compose @("up", "-d")
    Write-Host ""
    Write-Host "TicketSystem is starting up."

    $frontendPort = "8080"
    $backendPort = "8000"
    if (Test-Path ".env") {
        Get-Content ".env" | ForEach-Object {
            if ($_ -match "^FRONTEND_PORT=(.+)$") { $frontendPort = $Matches[1] }
            if ($_ -match "^BACKEND_PORT=(.+)$") { $backendPort = $Matches[1] }
        }
    }

    Write-Host "  Frontend: http://localhost:$frontendPort"
    Write-Host "  Backend:  http://localhost:$backendPort"
    Write-Host ""
    Write-Host "Default login: admin@example.com / admin  (change on first login)"
    Write-Host "Run '.\deploy.ps1 logs' to follow startup progress."
}

function Stop-Stack {
    Write-Host "Stopping TicketSystem..."
    Invoke-Compose @("down")
}

function Update-Stack {
    Write-Host "Pulling latest images..."
    Invoke-Compose @("pull")
    Write-Host "Restarting with new images..."
    Invoke-Compose @("up", "-d")
    Write-Host "Update complete."
}

function Show-Logs {
    Invoke-Compose @("logs", "-f")
}

function Show-Status {
    Invoke-Compose @("ps")
}

# ── Main ──────────────────────────────────────────────────────────────────────

switch ($Command) {
    "start"  { Start-Stack }
    "stop"   { Stop-Stack }
    "update" { Update-Stack }
    "logs"   { Show-Logs }
    "status" { Show-Status }
}

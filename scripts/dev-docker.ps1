#!/usr/bin/env pwsh
# Full Docker Development Stack
# Everything runs in Docker - no local dependency issues

param(
    [switch]$Build,
    [switch]$ResetData,
    [switch]$Stop,
    [switch]$Logs
)

$ErrorActionPreference = "Stop"

function Write-Header($text) {
    Write-Host "`n=== $text ===" -ForegroundColor Cyan
}

function Write-Step($text) {
    Write-Host "  → $text" -ForegroundColor Gray
}

function Write-Success($text) {
    Write-Host "  ✓ $text" -ForegroundColor Green
}

if ($Stop) {
    Write-Header "Stopping Development Stack"
    docker compose -f docker-compose.dev.yml down
    Write-Success "Stack stopped"
    exit 0
}

if ($Logs) {
    Write-Header "Showing Logs"
    docker compose -f docker-compose.dev.yml logs -f
    exit 0
}

Write-Header "Starting Full Docker Development Stack"

# Reset data if requested
if ($ResetData) {
    Write-Step "Resetting data volumes..."
    docker compose -f docker-compose.dev.yml down -v
}

# Build if requested or first run
if ($Build -or -not (docker images -q rowdyhacks-backend-dev 2>$null)) {
    Write-Step "Building backend image (first time may take 2-3 minutes)..."
    docker compose -f docker-compose.dev.yml build backend
}

# Start services
Write-Step "Starting all services..."
docker compose -f docker-compose.dev.yml up -d

# Wait for backend to be healthy
Write-Step "Waiting for backend to be ready..."
$attempts = 0
$maxAttempts = 60
while ($attempts -lt $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/monitoring/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop 2>$null
        if ($response.StatusCode -eq 200) {
            Write-Success "Backend is healthy!"
            break
        }
    } catch {}
    
    Start-Sleep -Milliseconds 1000
    $attempts++
    if ($attempts % 10 -eq 0) {
        Write-Host "    Still waiting... ($attempts/$maxAttempts)" -ForegroundColor Gray
    }
}

if ($attempts -eq $maxAttempts) {
    Write-Host "  ✗ Backend didn't become healthy in time. Check logs with -Logs flag" -ForegroundColor Red
    exit 1
}

Write-Header "Development Stack is Ready!"
Write-Host ""
Write-Host "  Services:" -ForegroundColor Yellow
Write-Host "    Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "    Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "    API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "    Database: localhost:5433 (PostgreSQL)" -ForegroundColor White
Write-Host "    Redis:    localhost:6379" -ForegroundColor White
Write-Host "    Qdrant:   localhost:6333" -ForegroundColor White
Write-Host ""
Write-Host "  Features:" -ForegroundColor Yellow
Write-Host "    ✓ Hot reload on both frontend and backend" -ForegroundColor Green
Write-Host "    ✓ Code changes reflect immediately" -ForegroundColor Green
Write-Host "    ✓ All services in Docker (no Windows dependency issues)" -ForegroundColor Green
Write-Host ""
Write-Host "  Commands:" -ForegroundColor Yellow
Write-Host "    View logs:   .\scripts\dev-docker.ps1 -Logs" -ForegroundColor White
Write-Host "    Stop:       .\scripts\dev-docker.ps1 -Stop" -ForegroundColor White
Write-Host "    Rebuild:    .\scripts\dev-docker.ps1 -Build" -ForegroundColor White
Write-Host "    Reset data: .\scripts\dev-docker.ps1 -ResetData" -ForegroundColor White

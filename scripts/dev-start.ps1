#!/usr/bin/env pwsh
# Local Development Stack Launcher
# Run this to start all services for local vibecoding

param(
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

function Write-Error($text) {
    Write-Host "  ✗ $text" -ForegroundColor Red
}

if ($Stop) {
    Write-Header "Stopping Local Dev Stack"
    docker compose -f docker-compose.local.yml down
    Write-Success "Services stopped"
    exit 0
}

if ($Logs) {
    Write-Header "Showing Logs"
    docker compose -f docker-compose.local.yml logs -f
    exit 0
}

# Check if .env.local exists
if (-not (Test-Path .env.local)) {
    Write-Error ".env.local not found! Copying from template..."
    Copy-Item .env.local .env.local
    Write-Success "Created .env.local - please review and customize it"
}

Write-Header "Starting Local Development Stack"
Write-Step "Data services: PostgreSQL, Redis, Qdrant"

# Start data services
if ($ResetData) {
    Write-Step "Resetting data volumes..."
    docker compose -f docker-compose.local.yml down -v
}

docker compose -f docker-compose.local.yml up -d

# Wait for services to be healthy
Write-Step "Waiting for PostgreSQL..."
$attempts = 0
$maxAttempts = 30
while ($attempts -lt $maxAttempts) {
    try {
        $result = docker compose -f docker-compose.local.yml exec -T db pg_isready -U hackverify 2>$null
        if ($result -match "accepting connections") {
            Write-Success "PostgreSQL is ready"
            break
        }
    } catch {}
    Start-Sleep -Milliseconds 500
    $attempts++
    if ($attempts -eq $maxAttempts) {
        Write-Error "PostgreSQL failed to start"
        exit 1
    }
}

Write-Step "Waiting for Redis..."
docker compose -f docker-compose.local.yml exec -T redis redis-cli ping 2>$null | Out-Null
Write-Success "Redis is ready"

Write-Step "Waiting for Qdrant..."
Start-Sleep -Seconds 2
Write-Success "Qdrant is ready"

Write-Header "Services Running"
Write-Host "  PostgreSQL: localhost:5433 (user: hackverify, pass: changeme)" -ForegroundColor White
Write-Host "  Redis:      localhost:6379" -ForegroundColor White
Write-Host "  Qdrant:     localhost:6333" -ForegroundColor White

Write-Header "Next Steps"
Write-Host "  1. Start Backend:" -ForegroundColor Yellow
Write-Host "     cd backend" -ForegroundColor White
Write-Host "     uvicorn app.main:app --reload --port 8000" -ForegroundColor White
Write-Host ""
Write-Host "  2. Start Frontend:" -ForegroundColor Yellow
Write-Host "     cd frontend" -ForegroundColor White
Write-Host "     npm run dev" -ForegroundColor White
Write-Host ""
Write-Host "  URLs:" -ForegroundColor Yellow
Write-Host "     Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "     Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "     API Docs: http://localhost:8000/docs" -ForegroundColor White

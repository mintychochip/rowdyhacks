# Local Development Startup Script
# Usage: .\scripts\dev.ps1

$ErrorActionPreference = "Stop"

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Hackathon Platform - Dev Mode" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
try {
    docker info | Out-Null
    Write-Host "Docker is running" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check for .env file
if (-not (Test-Path .env)) {
    Write-Host "WARNING: No .env file found. Copying from example..." -ForegroundColor Yellow
    if (Test-Path .env.example) {
        Copy-Item .env.example .env
        Write-Host "Created .env from example. Please edit it with your API keys." -ForegroundColor Yellow
    } else {
        @"
# Required for Clerk auth
HACKVERIFY_CLERK_SECRET_KEY=your_clerk_secret_key_here
VITE_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key_here

# Optional - for AI features
HACKVERIFY_LLM_API_KEY=your_poolside_or_openai_key_here
"@ | Out-File -FilePath .env -Encoding UTF8
        Write-Host "Created minimal .env file. Please add your Clerk keys." -ForegroundColor Yellow
    }
}

# Load environment variables from .env
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#][^=]*)=(.*)$') {
        $key = $matches[1]
        $value = $matches[2]
        [Environment]::SetEnvironmentVariable($key, $value, "Process")
    }
}

Write-Host ""
Write-Host "Starting services..." -ForegroundColor Cyan
Write-Host ""

# Start all services
docker-compose -f docker-compose.dev.yml up -d --build

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "Services started!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Hot reload enabled for both frontend and backend" -ForegroundColor Gray
Write-Host ""
Write-Host "Commands:" -ForegroundColor Cyan
Write-Host "  docker-compose -f docker-compose.dev.yml logs -f" -ForegroundColor Gray
Write-Host "  docker-compose -f docker-compose.dev.yml down" -ForegroundColor Gray
Write-Host ""

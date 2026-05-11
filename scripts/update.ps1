# update.ps1 — One-command update for OpenHack (Windows)
#
# Usage:
#   .\scripts\update.ps1                     # update production stack
#   .\scripts\update.ps1 -Dev                # update dev stack
#   .\scripts\update.ps1 -SkipPull           # skip git pull
#   .\scripts\update.ps1 -NoMigrate        # skip database migrations
#
# This script:
#   1. Pulls latest code from git (unless -SkipPull)
#   2. Pulls/builds latest Docker images
#   3. Runs pending database migrations
#   4. Restarts services with minimal downtime

param(
    [switch]$Dev,
    [switch]$SkipPull,
    [switch]$NoMigrate
)

$Mode = if ($Dev) { "dev" } else { "prod" }

function Say($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Ok($msg)  { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  ! $msg" -ForegroundColor Yellow }
function Err($msg) { Write-Host "  ✗ $msg" -ForegroundColor Red }

Say "OpenHack Update — mode: $Mode"
Write-Host ""

# ---------------------------------------------------------------------------
# 1. Preconditions
# ---------------------------------------------------------------------------
try {
    $null = Get-Command docker -ErrorAction Stop
    $null = docker info 2>$null
} catch {
    Err "Docker is not installed or not running."
    exit 1
}

try {
    $null = Get-Command git -ErrorAction Stop
} catch {
    Err "Git is not installed."
    exit 1
}

Ok "Docker and Git are available"

# ---------------------------------------------------------------------------
# 2. Git pull
# ---------------------------------------------------------------------------
if (-not $SkipPull) {
    Say "Pulling latest code..."
    try {
        git pull --ff-only | Out-Null
        $sha = git rev-parse --short HEAD
        Ok "Code updated to $sha"
    } catch {
        Err "Git pull failed. Resolve conflicts and re-run, or use -SkipPull."
        exit 1
    }
} else {
    Say "Skipping git pull (-SkipPull)"
}

# ---------------------------------------------------------------------------
# 3. Update Docker images / build
# ---------------------------------------------------------------------------
$ComposeFile = if ($Dev) { "docker-compose.dev.yml" } else { "docker-compose.yml" }

Say "Updating Docker images..."
if ($Dev) {
    docker compose -f $ComposeFile build --pull 2>$null
    if ($LASTEXITCODE -ne 0) { Warn "Some images could not be pulled; using cached layers" }
} else {
    docker compose -f $ComposeFile pull 2>$null
    if ($LASTEXITCODE -ne 0) { Warn "Some images could not be pulled; using cached layers" }
}
Ok "Images updated"

# ---------------------------------------------------------------------------
# 4. Restart services
# ---------------------------------------------------------------------------
Say "Restarting services..."
docker compose -f $ComposeFile up -d --remove-orphans | Out-Null
Ok "Services restarted"

# ---------------------------------------------------------------------------
# 5. Database migrations
# ---------------------------------------------------------------------------
if (-not $NoMigrate) {
    Say "Running database migrations..."
    Start-Sleep -Seconds 3

    $backendService = "backend"
    docker compose -f $ComposeFile ps $backendService 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        docker compose -f $ComposeFile exec -T $backendService alembic upgrade head 2>$null
        if ($LASTEXITCODE -ne 0) {
            Warn "Migration command failed. You may need to run it manually:"
            Write-Host "  docker compose -f $ComposeFile exec $backendService alembic upgrade head"
            exit 1
        }
        Ok "Migrations applied"
    } else {
        Warn "Backend service not found in compose. Skipping migrations."
    }
} else {
    Say "Skipping migrations (-NoMigrate)"
}

# ---------------------------------------------------------------------------
# 6. Health check
# ---------------------------------------------------------------------------
Say "Running health check..."
$healthy = $false
for ($i = 0; $i -lt 12; $i++) {
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:8000/api/monitoring/health" -UseBasicParsing -ErrorAction Stop
        Ok "Backend is healthy"
        $healthy = $true
        break
    } catch {
        Start-Sleep -Seconds 2
    }
}
if (-not $healthy) { Warn "Backend health check did not pass within 24s" }

if ($Dev) {
    Say "Checking frontend..."
    $feHealthy = $false
    for ($i = 0; $i -lt 12; $i++) {
        try {
            $null = Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -ErrorAction Stop
            Ok "Frontend is responding"
            $feHealthy = $true
            break
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    if (-not $feHealthy) { Warn "Frontend did not respond within 24s" }
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Say "Update complete!"
Write-Host ""
Write-Host "  Backend:  http://localhost:8000"
Write-Host "  Health:   http://localhost:8000/api/monitoring/health"
if ($Dev) {
    Write-Host "  Frontend: http://localhost:5173"
    Write-Host "  API Docs: http://localhost:8000/docs"
}
Write-Host ""

"""Docker Compose orchestration helpers for the OpenHack TUI installer."""

import asyncio
import secrets
import shutil
from pathlib import Path


def repo_root() -> Path:
    """Find the repository root by looking for docker-compose.yml."""
    current = Path.cwd()
    for _ in range(5):
        if (current / "docker-compose.yml").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return Path.cwd()


def has_docker() -> bool:
    return shutil.which("docker") is not None


def has_docker_compose() -> bool:
    return shutil.which("docker") is not None and shutil.which("docker-compose") is not None


def env_path() -> Path:
    return repo_root() / ".env"


def env_exists() -> bool:
    return env_path().exists()


def read_env() -> dict[str, str]:
    """Read existing .env into a dict."""
    result: dict[str, str] = {}
    path = env_path()
    if not path.exists():
        return result
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            result[key] = val
    return result


def write_env(updates: dict[str, str]) -> None:
    """Merge updates into existing .env or create new one from template."""
    existing = read_env()
    existing.update(updates)
    lines = []
    for key, val in existing.items():
        lines.append(f"{key}={val}")
    env_path().write_text("\n".join(lines) + "\n")


def generate_secret_key() -> str:
    return secrets.token_urlsafe(32)


async def run_command(*cmd: str, cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()


async def start_db_container() -> tuple[bool, str]:
    """Start only the db service via docker compose."""
    root = repo_root()
    rc, out, err = await run_command(
        "docker",
        "compose",
        "up",
        "-d",
        "db",
        cwd=str(root),
    )
    if rc != 0:
        return False, err or out
    # Wait for healthcheck
    for _ in range(30):
        rc2, _, _ = await run_command(
            "docker",
            "compose",
            "ps",
            "db",
            "--format",
            "{{.Health}}",
            cwd=str(root),
        )
        if rc2 == 0:
            break
        await asyncio.sleep(1)
    return True, "Database container started"


async def start_all_services() -> tuple[bool, str]:
    """Start all services via docker compose up -d."""
    root = repo_root()
    rc, out, err = await run_command(
        "docker",
        "compose",
        "up",
        "-d",
        "--remove-orphans",
        cwd=str(root),
    )
    if rc != 0:
        return False, err or out
    return True, "All services started"


async def build_frontend() -> tuple[bool, str]:
    """Build the frontend Docker image."""
    root = repo_root()
    rc, out, err = await run_command(
        "docker",
        "compose",
        "build",
        "frontend",
        cwd=str(root),
    )
    if rc != 0:
        return False, err or out
    return True, "Frontend built"


async def health_check() -> tuple[bool, str]:
    """Check if backend is healthy."""
    root = repo_root()
    for i in range(30):
        rc, out, err = await run_command(
            "curl",
            "-sf",
            "http://localhost:8000/api/monitoring/health",
        )
        if rc == 0:
            return True, out
        await asyncio.sleep(2)
    return False, "Backend health check timed out"


async def db_is_running() -> bool:
    """Check if the db container is already running."""
    root = repo_root()
    rc, out, _ = await run_command(
        "docker",
        "compose",
        "ps",
        "--services",
        "--filter",
        "status=running",
        cwd=str(root),
    )
    return rc == 0 and "db" in out.lower()

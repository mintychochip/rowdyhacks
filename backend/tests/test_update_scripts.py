"""Tests that update scripts exist and are valid."""

import platform
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_bash_update_script_exists():
    script = REPO_ROOT / "scripts" / "update.sh"
    assert script.exists(), "scripts/update.sh should exist"
    if platform.system() != "Windows":
        assert script.stat().st_mode & 0o111, "update.sh should be executable"


def test_bash_update_script_syntax():
    script = REPO_ROOT / "scripts" / "update.sh"
    content = script.read_text()
    assert "#!/usr/bin/env bash" in content
    assert "set -euo pipefail" in content
    assert "docker compose" in content
    assert "alembic upgrade head" in content
    assert "http://localhost:8000/api/monitoring/health" in content


def test_powershell_update_script_exists():
    script = REPO_ROOT / "scripts" / "update.ps1"
    assert script.exists(), "scripts/update.ps1 should exist"


def test_powershell_update_script_syntax():
    script = REPO_ROOT / "scripts" / "update.ps1"
    content = script.read_text()
    assert "param(" in content
    assert "docker compose" in content
    assert "alembic upgrade head" in content
    assert "http://localhost:8000/api/monitoring/health" in content


def test_update_script_help_flag():
    script = REPO_ROOT / "scripts" / "update.sh"
    content = script.read_text()
    assert "--dev" in content
    assert "--skip-pull" in content
    assert "--no-migrate" in content
    assert "-h|--help" in content

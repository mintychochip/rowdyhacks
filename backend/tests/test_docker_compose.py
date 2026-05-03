"""Integration tests validating docker-compose.yml structure and service dependencies."""

from pathlib import Path

import pytest

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


@pytest.fixture
def compose_config():
    """Load docker-compose.yml as a dict."""
    if not HAS_YAML:
        pytest.skip("pyyaml not installed")
    with open(COMPOSE_FILE) as f:
        return yaml.safe_load(f)


def test_compose_file_exists():
    """docker-compose.yml must exist at repo root."""
    assert COMPOSE_FILE.exists(), f"Missing {COMPOSE_FILE}"


@pytest.mark.skipif(not HAS_YAML, reason="pyyaml not installed")
class TestComposeStructure:
    def test_required_services_present(self, compose_config):
        """All required services must be defined."""
        services = compose_config.get("services", {})
        for svc in ["db", "redis", "backend", "frontend", "nginx"]:
            assert svc in services, f"Missing service: {svc}"

    def test_redis_service_has_healthcheck(self, compose_config):
        """Redis service must have a healthcheck for dependency ordering."""
        redis = compose_config["services"]["redis"]
        assert "healthcheck" in redis, "Redis service needs a healthcheck"

    def test_backend_depends_on_db_healthy(self, compose_config):
        """Backend must wait for DB to be healthy before starting."""
        backend = compose_config["services"]["backend"]
        deps = backend.get("depends_on", {})
        assert "db" in deps, "Backend must depend on db"
        assert deps["db"].get("condition") == "service_healthy"

    def test_backend_depends_on_redis_healthy(self, compose_config):
        """Backend must wait for Redis to be healthy before starting."""
        backend = compose_config["services"]["backend"]
        deps = backend.get("depends_on", {})
        assert "redis" in deps, "Backend must depend on redis"
        assert deps["redis"].get("condition") == "service_healthy"

    def test_backend_has_healthcheck(self, compose_config):
        """Backend must have a healthcheck so nginx can wait for it."""
        backend = compose_config["services"]["backend"]
        assert "healthcheck" in backend, "Backend needs a healthcheck for nginx dependency"

    def test_nginx_depends_on_backend_healthy(self, compose_config):
        """Nginx must wait for backend to be healthy."""
        nginx = compose_config["services"]["nginx"]
        deps = nginx.get("depends_on", {})
        assert "backend" in deps, "Nginx must depend on backend"
        assert deps["backend"].get("condition") == "service_healthy"

    def test_backend_has_redis_url(self, compose_config):
        """Backend environment must include HACKVERIFY_REDIS_URL."""
        backend = compose_config["services"]["backend"]
        env = backend.get("environment", {})
        if isinstance(env, list):
            env_keys = [e.split("=")[0] for e in env]
            assert "HACKVERIFY_REDIS_URL" in env_keys
        else:
            assert "HACKVERIFY_REDIS_URL" in env

    def test_volumes_defined(self, compose_config):
        """Named volumes must be declared."""
        volumes = compose_config.get("volumes", {})
        assert "postgres_data" in volumes
        assert "redis_data" in volumes

    def test_backend_port_binding(self, compose_config):
        """Backend should bind to localhost only."""
        backend = compose_config["services"]["backend"]
        ports = backend.get("ports", [])
        assert any("127.0.0.1:8000" in p for p in ports), "Backend should bind to 127.0.0.1:8000"

    def test_db_port_binding(self, compose_config):
        """DB should bind to localhost only."""
        db = compose_config["services"]["db"]
        ports = db.get("ports", [])
        assert any("127.0.0.1:" in p for p in ports), "DB should bind to localhost"

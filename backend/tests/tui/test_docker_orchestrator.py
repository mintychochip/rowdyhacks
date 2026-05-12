from cli.tui.docker_orchestrator import generate_secret_key, has_docker, repo_root


def test_generate_secret_key():
    key = generate_secret_key()
    assert len(key) >= 32


def test_repo_root_exists():
    root = repo_root()
    assert root.exists()
    assert (root / "docker-compose.yml").exists() or (root.parent / "docker-compose.yml").exists()


def test_has_docker():
    # Just smoke test that it doesn't crash
    result = has_docker()
    assert isinstance(result, bool)

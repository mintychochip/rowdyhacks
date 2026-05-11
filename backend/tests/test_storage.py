import pytest
from app.storage import StorageService


@pytest.fixture
def service():
    return StorageService()


def test_storage_service_exists(service):
    assert service is not None


def test_sanitize_filename(service):
    assert service._sanitize_filename("logo.png") == "logo.png"
    assert service._sanitize_filename("../../etc/passwd") == "passwd"
    assert service._sanitize_filename("my logo!@#.png") == "my_logo.png"
    assert service._sanitize_filename("") == "asset"


def test_sanitize_filename_path_traversal(service):
    assert service._sanitize_filename("../../../etc/shadow") == "shadow"

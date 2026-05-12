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


def test_build_public_base(service):
    # When s3_endpoint is empty, public base should be empty
    from app.config import settings

    if not settings.s3_endpoint:
        assert service._public_base == ""
    else:
        assert service._bucket in service._public_base


def test_generic_allowed_types_includes_markdown(service):
    assert "text/markdown" in service.GENERIC_ALLOWED_TYPES


def test_upload_generic_rejects_unknown_type(service):
    import asyncio
    from unittest.mock import MagicMock, AsyncMock

    file = MagicMock()
    file.content_type = "application/zip"
    file.filename = "archive.zip"
    file.read = AsyncMock(return_value=b"PK")

    with pytest.raises(ValueError, match="Unsupported file type"):
        asyncio.run(service.upload_generic(file=file, allowed_types={"text/plain"}, max_size=1024))

"""Resource page service backed by MinIO/S3 markdown files with YAML frontmatter."""

import asyncio
import logging
import re

import yaml
from botocore.exceptions import ClientError

from app.cache import cache_delete, cache_get, cache_set
from app.storage import StorageService

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"^[a-z0-9-]+$")


def parse_frontmatter(raw: bytes) -> tuple[dict, str]:
    """Parse YAML frontmatter and markdown body from raw bytes.

    Behavior:
    1. Decode bytes to UTF-8 text.
    2. Detect ``---`` delimiters at the top of the file.
    3. Parse the YAML block between delimiters via ``yaml.safe_load``.
    4. Return the metadata dict and the remaining markdown body.

    Raises: ValueError if the YAML frontmatter is malformed.
    Side Effects: None (read-only).
    """
    text = raw.decode("utf-8")
    if not text.startswith("---"):
        return {}, text

    end = text.find("---", 3)
    if end == -1:
        return {}, text

    fm_text = text[3:end].strip()
    body = text[end + 3 :].lstrip("\n")

    try:
        metadata = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML frontmatter: {e}") from e

    if not isinstance(metadata, dict):
        raise ValueError("YAML frontmatter must be a mapping")

    return metadata, body


def validate_resource(metadata: dict, slug: str) -> None:
    """Validate resource metadata and slug.

    Behavior:
    1. Ensure ``title`` exists and is a non-empty string.
    2. Ensure ``slug`` matches ``^[a-z0-9-]+$``.

    Raises: ValueError with a clear message on failure.
    Side Effects: None (read-only).
    """
    title = metadata.get("title")
    if not title or not isinstance(title, str) or not title.strip():
        raise ValueError(f"Resource '{slug}' missing required 'title' frontmatter")

    if not _SLUG_RE.match(slug):
        raise ValueError(f"Invalid slug '{slug}': must be lowercase alphanumeric + hyphens only")


async def list_resources() -> list[dict]:
    """List all resource pages from MinIO, parse frontmatter, validate, and cache.

    Behavior:
    1. Check the in-memory / Redis cache for ``resources:list``.
    2. If cached, return the stored list immediately.
    3. Otherwise list ``resources/*.md`` objects from S3.
    4. Parse frontmatter and validate each file.
    5. Build lightweight dicts mirroring the legacy ``ContentPage`` shape.
    6. Cache the result for 60 seconds and return it.

    Returns: List of dicts with keys: id, title, slug, content, tab_group,
    tab_group_order, sort_order, is_published, created_at, updated_at.

    Raises: None (invalid files are logged and skipped).
    Side Effects: Reads from S3; may write to cache.
    """
    cached = await cache_get("resources:list")
    if cached is not None:
        return cached

    storage = StorageService()
    objects = await storage.list_objects("resources/")

    results = []
    for obj in objects:
        key = obj["key"]
        if not key.endswith(".md"):
            continue

        slug = key[len("resources/") : -len(".md")]
        try:
            raw = await storage.get_object(key)
            metadata, body = parse_frontmatter(raw)
            validate_resource(metadata, slug)

            last_modified = obj["last_modified"]
            results.append(
                {
                    "id": slug,
                    "title": metadata["title"],
                    "slug": slug,
                    "content": body,
                    "tab_group": metadata.get("tab_group") or "General",
                    "tab_group_order": metadata.get("tab_group_order") or 0,
                    "sort_order": metadata.get("sort_order") or 0,
                    "is_published": True,
                    "created_at": last_modified,
                    "updated_at": last_modified,
                }
            )
        except Exception as e:
            logger.warning(f"Skipping resource {key}: {e}")
            continue

    results.sort(key=lambda r: (r["tab_group"], r["sort_order"]))
    await cache_set("resources:list", results, ttl_seconds=60)
    return results


async def get_resource(slug: str) -> dict:
    """Fetch a single resource page from MinIO by slug.

    Behavior:
    1. Build the S3 key ``resources/{slug}.md``.
    2. Download the object, parse frontmatter, and validate.
    3. Return a dict mirroring the legacy ``ContentPage`` shape.

    Raises:
        FileNotFoundError: If the object does not exist in S3.
        ValueError: If frontmatter is invalid.

    Side Effects: Reads from S3.
    """
    storage = StorageService()
    key = f"resources/{slug}.md"

    try:
        raw = await storage.get_object(key)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if error_code == "NoSuchKey":
            raise FileNotFoundError(f"Resource not found: {slug}") from e
        raise

    metadata, body = parse_frontmatter(raw)
    validate_resource(metadata, slug)

    # Get LastModified via HEAD for created_at / updated_at
    try:
        head = await asyncio.to_thread(
            storage._get_client().head_object,
            Bucket=storage._bucket,
            Key=key,
        )
        last_modified = head["LastModified"].isoformat()
    except Exception:
        last_modified = None

    return {
        "id": slug,
        "title": metadata["title"],
        "slug": slug,
        "content": body,
        "tab_group": metadata.get("tab_group") or "General",
        "tab_group_order": metadata.get("tab_group_order") or 0,
        "sort_order": metadata.get("sort_order") or 0,
        "is_published": True,
        "created_at": last_modified,
        "updated_at": last_modified,
    }


async def create_resource(
    slug: str,
    title: str,
    content: str,
    tab_group: str | None = None,
    sort_order: int | None = None,
    tab_group_order: int | None = None,
) -> dict:
    """Create a new resource markdown file in MinIO.

    Behavior:
    1. Validate the slug and title.
    2. Check for slug uniqueness via ``object_exists``.
    3. Build YAML frontmatter + markdown body.
    4. Upload to S3 via ``put_object``.
    5. Bust the resources list cache.

    Raises:
        ValueError: If slug or title is invalid.
        FileExistsError: If the slug already exists in S3.

    Side Effects: Writes to S3; may invalidate cache.
    """
    if not _SLUG_RE.match(slug):
        raise ValueError(f"Invalid slug '{slug}': must be lowercase alphanumeric + hyphens only")

    if not title or not isinstance(title, str) or not title.strip():
        raise ValueError("Title is required and must be a non-empty string")

    storage = StorageService()
    key = f"resources/{slug}.md"

    if await storage.object_exists(key):
        raise FileExistsError(f"Resource with slug '{slug}' already exists")

    frontmatter: dict[str, object] = {"title": title}
    if tab_group:
        frontmatter["tab_group"] = tab_group
    if sort_order is not None:
        frontmatter["sort_order"] = sort_order
    if tab_group_order is not None:
        frontmatter["tab_group_order"] = tab_group_order

    yaml_block = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True)
    body = f"---\n{yaml_block}---\n\n{content or ''}"

    await storage.put_object(
        key,
        body.encode("utf-8"),
        content_type="text/markdown; charset=utf-8",
    )
    await cache_delete("resources:list")

    return {
        "id": slug,
        "title": title,
        "slug": slug,
        "content": content or "",
        "tab_group": tab_group or "General",
        "tab_group_order": tab_group_order or 0,
        "sort_order": sort_order or 0,
        "is_published": True,
        "created_at": None,
        "updated_at": None,
    }


async def update_resource(
    slug: str,
    title: str,
    content: str,
    tab_group: str | None = None,
    sort_order: int | None = None,
    tab_group_order: int | None = None,
) -> dict:
    """Overwrite an existing resource markdown file in MinIO.

    Behavior:
    1. Validate the slug and title.
    2. Verify the object exists in S3.
    3. Build YAML frontmatter + markdown body.
    4. Upload to S3 via ``put_object``.
    5. Bust the resources list cache.

    Raises:
        ValueError: If slug or title is invalid.
        FileNotFoundError: If the resource does not exist in S3.

    Side Effects: Writes to S3; may invalidate cache.
    """
    if not _SLUG_RE.match(slug):
        raise ValueError(f"Invalid slug '{slug}': must be lowercase alphanumeric + hyphens only")

    if not title or not isinstance(title, str) or not title.strip():
        raise ValueError("Title is required and must be a non-empty string")

    storage = StorageService()
    key = f"resources/{slug}.md"

    if not await storage.object_exists(key):
        raise FileNotFoundError(f"Resource not found: {slug}")

    frontmatter: dict[str, object] = {"title": title}
    if tab_group:
        frontmatter["tab_group"] = tab_group
    if sort_order is not None:
        frontmatter["sort_order"] = sort_order
    if tab_group_order is not None:
        frontmatter["tab_group_order"] = tab_group_order

    yaml_block = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True)
    body = f"---\n{yaml_block}---\n\n{content or ''}"

    await storage.put_object(
        key,
        body.encode("utf-8"),
        content_type="text/markdown; charset=utf-8",
    )
    await cache_delete("resources:list")

    return {
        "id": slug,
        "title": title,
        "slug": slug,
        "content": content or "",
        "tab_group": tab_group or "General",
        "tab_group_order": tab_group_order or 0,
        "sort_order": sort_order or 0,
        "is_published": True,
        "created_at": None,
        "updated_at": None,
    }


async def delete_resource(slug: str) -> None:
    """Delete a resource markdown file from MinIO.

    Behavior:
    1. Build the S3 key ``resources/{slug}.md``.
    2. Delete the object via ``delete_object``.
    3. Bust the resources list cache.

    Raises: None (boto3 exceptions propagate; missing object is silently ignored).

    Side Effects: Removes an S3 object; may invalidate cache.
    """
    storage = StorageService()
    key = f"resources/{slug}.md"
    await storage.delete_object(key)
    await cache_delete("resources:list")

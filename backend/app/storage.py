"""Async S3/MinIO storage wrapper for asset uploads."""

import asyncio
import logging
import os
import re
import uuid

import boto3
from botocore.config import Config as BotoConfig
from fastapi import UploadFile

from app.config import settings

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}
MAX_FILE_SIZE = 2 * 1024 * 1024

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_-]+")


class StorageService:
    """Async wrapper for S3/MinIO file uploads with validation."""

    def __init__(self):
        """Initialize the storage service with lazy S3 client creation.

        Behavior:
        1. Set the target bucket and endpoint from application settings.
        2. Compute the public base URL prefix.
        3. Leave the boto3 client uninitialized (lazy creation on first use).

        Raises: None
        Side Effects: None (no network activity at init time).
        Dependencies: app.config.settings.
        Consumers: Route handlers and services that upload files.
        """
        self._client = None
        self._bucket = settings.s3_bucket
        self._endpoint = settings.s3_endpoint
        self._public_base = self._build_public_base()

    def _build_public_base(self) -> str:
        """Build the public asset URL prefix from the configured S3 endpoint.

        Behavior:
        1. Use ``s3_public_url`` if configured, otherwise fall back to ``s3_endpoint``.
        2. Strip trailing slashes from the URL.
        3. Return an empty string if no endpoint is configured.
        4. Otherwise return ``endpoint/bucket``.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: app.config.settings.s3_endpoint, app.config.settings.s3_public_url.
        Consumers: StorageService.__init__, StorageService.upload.
        """
        endpoint = (settings.s3_public_url or settings.s3_endpoint).rstrip("/")
        if not endpoint:
            return ""
        return f"{endpoint}/{self._bucket}"

    def _get_client(self):
        """Create and cache a boto3 S3 client.

        Behavior:
        1. Return the existing client if already initialized.
        2. Build a BotoConfig with retry and timeout settings.
        3. Instantiate a boto3 S3 client using the application settings.
        4. Cache the client on the instance and return it.

        Raises: None ( boto3 errors propagate on first use).
        Side Effects: Mutates ``self._client``.
        Dependencies: boto3.client, botocore.config.Config, app.config.settings.
        Consumers: StorageService.ensure_bucket, StorageService.upload.
        """
        if self._client is None:
            boto_cfg = BotoConfig(
                retries={"max_attempts": 2, "mode": "standard"},
                connect_timeout=5,
                read_timeout=10,
            )
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint or None,
                aws_access_key_id=settings.s3_access_key or None,
                aws_secret_access_key=settings.s3_secret_key or None,
                region_name=settings.s3_region,
                use_ssl=settings.s3_use_ssl,
                config=boto_cfg,
            )
        return self._client

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Remove unsafe characters from an uploaded filename.

        Behavior:
        1. Strip directory components with os.path.basename.
        2. Split the base name into stem and extension.
        3. Replace any non-alphanumeric characters (except hyphen and underscore) with underscores.
        4. Fall back to ``asset`` if the stem becomes empty.
        5. Reassemble and return the safe filename.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: os.path.basename, os.path.splitext, re.compile.
        Consumers: StorageService.upload.
        """
        base = os.path.basename(name)
        name_no_ext, ext = os.path.splitext(base)
        safe = _SAFE_NAME_RE.sub("_", name_no_ext).strip("_")
        if not safe:
            safe = "asset"
        return f"{safe}{ext}"

    async def ensure_bucket(self):
        """Create the configured S3 bucket if it does not already exist.

        Behavior:
        1. Obtain the boto3 S3 client.
        2. Issue a HEAD bucket request in a thread pool.
        3. If the bucket exists, return immediately.
        4. If the bucket is missing, log an info message and create it.

        Raises: None (boto3 exceptions are caught and logged).
        Side Effects: May create a new S3 bucket.
        Dependencies: boto3.client, asyncio.to_thread.
        Consumers: StorageService.upload.
        """
        s3 = self._get_client()
        try:
            await asyncio.to_thread(s3.head_bucket, Bucket=self._bucket)
        except Exception as e:
            logger.info(f"Bucket {self._bucket} not found, creating: {e}")
            await asyncio.to_thread(s3.create_bucket, Bucket=self._bucket)

    async def upload(self, file: UploadFile, folder: str = "assets") -> dict:
        """Validate and upload a file to S3/MinIO, returning its public URL.

        Behavior:
        1. Read the uploaded file contents into memory.
        2. Reject files larger than 2MB.
        3. Detect the MIME type (using python-magic if available).
        4. Reject files that are not in the allowed image type whitelist.
        5. Sanitize the original filename.
        6. Ensure the target bucket exists.
        7. Upload the object via boto3 in a thread pool.
        8. Return the S3 key and public URL.

        Raises: ValueError if the file is too large or the MIME type is unsupported.
        Side Effects: Reads the UploadFile stream; may create an S3 bucket; writes an S3 object.
        Dependencies: boto3.client, asyncio.to_thread, python-magic (optional), app.config.settings.
        Consumers: POST /api/upload and other file-upload route handlers.
        """
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise ValueError(f"File exceeds 2MB limit ({len(contents)} bytes)")

        detected = file.content_type or "application/octet-stream"
        try:
            import magic

            detected = magic.from_buffer(contents, mime=True)
        except Exception:
            pass

        # Normalize MIME type: strip charset suffixes
        detected = detected.split(";")[0].strip()

        if detected not in ALLOWED_IMAGE_TYPES:
            raise ValueError(f"Unsupported file type: {detected}. Allowed: {ALLOWED_IMAGE_TYPES}")

        safe_name = self._sanitize_filename(file.filename or "asset")
        object_key = f"{folder}/{uuid.uuid4().hex}-{safe_name}"

        await self.ensure_bucket()
        s3 = self._get_client()
        await asyncio.to_thread(
            s3.put_object,
            Bucket=self._bucket,
            Key=object_key,
            Body=contents,
            ContentType=detected,
        )

        url = f"{self._public_base}/{object_key}"
        return {"key": object_key, "url": url}

    async def list_objects(self, prefix: str = "") -> list[dict]:
        """List objects in the bucket with an optional prefix.

        Behavior:
        1. Obtain the boto3 S3 client.
        2. Issue ``list_objects_v2`` in a thread pool.
        3. Return a list of lightweight dicts with ``key``, ``size``, and ``last_modified``.

        Raises: None (boto3 exceptions propagate).
        Side Effects: None (read-only).
        Dependencies: boto3.client, asyncio.to_thread.
        Consumers: resource_service.list_resources.
        """
        s3 = self._get_client()
        response = await asyncio.to_thread(
            s3.list_objects_v2,
            Bucket=self._bucket,
            Prefix=prefix,
        )
        return [
            {
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
            }
            for obj in response.get("Contents", [])
        ]

    async def get_object(self, key: str) -> bytes:
        """Download an object from S3/MinIO and return its raw bytes.

        Behavior:
        1. Obtain the boto3 S3 client.
        2. Issue ``get_object`` in a thread pool.
        3. Read the response body in a thread pool.
        4. Return the raw bytes.

        Raises: botocore.exceptions.ClientError if the object does not exist.
        Side Effects: None (read-only).
        Dependencies: boto3.client, asyncio.to_thread.
        Consumers: resource_service.get_resource.
        """
        s3 = self._get_client()
        response = await asyncio.to_thread(
            s3.get_object,
            Bucket=self._bucket,
            Key=key,
        )
        return await asyncio.to_thread(response["Body"].read)

    async def object_exists(self, key: str) -> bool:
        """Check whether an object exists in the bucket via HEAD.

        Behavior:
        1. Obtain the boto3 S3 client.
        2. Issue ``head_object`` in a thread pool.
        3. Return True if the object exists, False otherwise.

        Raises: None (boto3 errors are caught and swallowed).
        Side Effects: None (read-only).
        Dependencies: boto3.client, asyncio.to_thread.
        Consumers: resource_service.get_resource.
        """
        s3 = self._get_client()
        try:
            await asyncio.to_thread(s3.head_object, Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload raw bytes to S3/MinIO without validation.

        Behavior:
        1. Ensure the target bucket exists.
        2. Obtain the boto3 S3 client.
        3. Issue ``put_object`` in a thread pool.

        Raises: None (boto3 exceptions propagate).
        Side Effects: Writes an S3 object.
        Dependencies: boto3.client, asyncio.to_thread.
        Consumers: Seed scripts and internal services.
        """
        await self.ensure_bucket()
        s3 = self._get_client()
        await asyncio.to_thread(
            s3.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    # Generic file upload constants for registration attachments
    GENERIC_ALLOWED_TYPES = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
        "image/png",
        "image/jpeg",
    }
    MAX_GENERIC_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    async def upload_generic(
        self,
        file: UploadFile,
        folder: str = "assets",
        allowed_types: set[str] | None = None,
        max_size: int | None = None,
        contents: bytes | None = None,
    ) -> dict:
        """Validate and upload a generic file (not just images), returning its public URL.

        Args:
            file: The uploaded file.
            folder: S3 folder prefix.
            allowed_types: Set of allowed MIME types. Defaults to GENERIC_ALLOWED_TYPES.
            max_size: Max file size in bytes. Defaults to MAX_GENERIC_FILE_SIZE.
            contents: Optional pre-read bytes. If provided, skips reading from ``file``.

        Raises:
            ValueError: If file exceeds size limit or has unsupported type.
        """
        allowed = allowed_types or self.GENERIC_ALLOWED_TYPES
        max_sz = max_size or self.MAX_GENERIC_FILE_SIZE

        data = contents if contents is not None else await file.read()
        if len(data) > max_sz:
            raise ValueError(f"File exceeds {max_sz // (1024 * 1024)}MB limit ({len(data)} bytes)")

        detected = file.content_type or "application/octet-stream"
        try:
            import magic

            detected = magic.from_buffer(data, mime=True)
        except Exception:
            pass

        # Normalize MIME type: strip charset suffixes like "text/plain; charset=utf-8"
        detected = detected.split(";")[0].strip()

        if detected not in allowed:
            raise ValueError(f"Unsupported file type: {detected}. Allowed: {allowed}")

        safe_name = self._sanitize_filename(file.filename or "asset")
        object_key = f"{folder}/{uuid.uuid4().hex}-{safe_name}"

        await self.ensure_bucket()
        s3 = self._get_client()
        await asyncio.to_thread(
            s3.put_object,
            Bucket=self._bucket,
            Key=object_key,
            Body=data,
            ContentType=detected,
        )

        url = f"{self._public_base}/{object_key}"
        return {"key": object_key, "url": url}

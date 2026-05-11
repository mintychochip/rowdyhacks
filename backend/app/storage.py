"""Async S3/MinIO storage wrapper for asset uploads."""

import os
import re
import uuid

import boto3
from botocore.config import Config as BotoConfig
from fastapi import UploadFile

from app.config import settings

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}
MAX_FILE_SIZE = 2 * 1024 * 1024

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_-]+")


class StorageService:
    def __init__(self):
        self._client = None
        self._bucket = settings.s3_bucket
        self._endpoint = settings.s3_endpoint
        self._public_base = self._build_public_base()

    def _build_public_base(self) -> str:
        endpoint = settings.s3_endpoint.rstrip("/")
        if not endpoint:
            return ""
        return f"{endpoint}/{self._bucket}"

    def _get_client(self):
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
        base = os.path.basename(name)
        name_no_ext, ext = os.path.splitext(base)
        safe = _SAFE_NAME_RE.sub("_", name_no_ext).strip("_")
        if not safe:
            safe = "asset"
        return f"{safe}{ext}"

    def ensure_bucket(self):
        s3 = self._get_client()
        try:
            s3.head_bucket(Bucket=self._bucket)
        except Exception:
            s3.create_bucket(Bucket=self._bucket)

    async def upload(self, file: UploadFile, folder: str = "assets") -> dict:
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise ValueError(f"File exceeds 2MB limit ({len(contents)} bytes)")

        detected = file.content_type or "application/octet-stream"
        try:
            import magic

            detected = magic.from_buffer(contents, mime=True)
        except Exception:
            pass

        if detected not in ALLOWED_IMAGE_TYPES:
            raise ValueError(f"Unsupported file type: {detected}. Allowed: {ALLOWED_IMAGE_TYPES}")

        safe_name = self._sanitize_filename(file.filename or "asset")
        object_key = f"{folder}/{uuid.uuid4().hex}-{safe_name}"

        self.ensure_bucket()
        s3 = self._get_client()
        s3.put_object(
            Bucket=self._bucket,
            Key=object_key,
            Body=contents,
            ContentType=detected,
        )

        url = f"{self._public_base}/{object_key}"
        return {"key": object_key, "url": url}

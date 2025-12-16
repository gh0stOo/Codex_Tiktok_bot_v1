import io
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

import boto3
from botocore.client import Config as BotoConfig

from ..config import get_settings

settings = get_settings()


class StorageProvider:
    def save_file(self, key: str, local_path: str) -> str:
        raise NotImplementedError

    def save_bytes(self, key: str, content: bytes) -> str:
        raise NotImplementedError

    def signed_url(self, key: str, expires: int = 900) -> str:
        raise NotImplementedError

    def read_bytes_uri(self, uri: str) -> bytes:
        raise NotImplementedError


class LocalStorage(StorageProvider):
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or settings.storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _full_path(self, key: str) -> Path:
        return self.base_path / key

    def save_file(self, key: str, local_path: str) -> str:
        dest = self._full_path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        # FIX: Handle case where dest already exists (Windows replace() can fail)
        try:
            if dest.exists():
                dest.unlink()  # Remove existing file first
            Path(local_path).replace(dest)
        except Exception as e:
            # Fallback: copy instead of replace
            import shutil
            shutil.copy2(local_path, dest)
            Path(local_path).unlink(missing_ok=True)  # Clean up source
        return str(dest)

    def save_bytes(self, key: str, content: bytes) -> str:
        dest = self._full_path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        return str(dest)

    def signed_url(self, key: str, expires: int = 900) -> str:
        # For local storage we return file:// path for internal access; frontend should proxy this.
        return self._full_path(key).as_posix()

    def read_bytes_uri(self, uri: str) -> bytes:
        return Path(uri).read_bytes()


class S3Storage(StorageProvider):
    def __init__(self):
        if not settings.storage_s3_bucket or not settings.storage_s3_access_key or not settings.storage_s3_secret_key:
            raise RuntimeError("S3 storage not configured")
        self.bucket = settings.storage_s3_bucket
        self.prefix = settings.storage_s3_prefix.rstrip("/") if settings.storage_s3_prefix else ""
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.storage_s3_endpoint or None,
            aws_access_key_id=settings.storage_s3_access_key,
            aws_secret_access_key=settings.storage_s3_secret_key,
            region_name=settings.storage_s3_region or None,
            config=BotoConfig(s3={"addressing_style": "path"}),
        )

    def _key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def save_file(self, key: str, local_path: str) -> str:
        object_key = self._key(key)
        with open(local_path, "rb") as f:
            self.client.upload_fileobj(f, self.bucket, object_key)
        return f"s3://{self.bucket}/{object_key}"

    def save_bytes(self, key: str, content: bytes) -> str:
        object_key = self._key(key)
        self.client.upload_fileobj(io.BytesIO(content), self.bucket, object_key)
        return f"s3://{self.bucket}/{object_key}"

    def signed_url(self, key: str, expires: int = 900) -> str:
        object_key = self._key(key)
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_key},
            ExpiresIn=expires,
        )

    def read_bytes_uri(self, uri: str) -> bytes:
        # uri format s3://bucket/key
        if uri.startswith("s3://"):
            _, rest = uri.split("s3://", 1)
            bucket, key = rest.split("/", 1)
        else:
            bucket = self.bucket
            key = uri
        response = self.client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()


def get_storage() -> StorageProvider:
    if settings.storage_backend == "s3":
        return S3Storage()
    return LocalStorage()


def tenant_prefix(org_id: str, project_id: str, post_id: Optional[str] = None) -> str:
    base = f"org_{org_id}/project_{project_id}"
    if post_id:
        return f"{base}/posts/{post_id}"
    return base

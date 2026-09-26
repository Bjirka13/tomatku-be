from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from config import settings
from models.validation import DetectionInput
from services.image_input import read_image_input


@dataclass(frozen=True)
class UploadedImage:
    object_path: str
    public_url: str


class StorageService:
    def __init__(self) -> None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured "
                "to upload images."
            )

        from supabase import create_client

        self.client: Any = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
        self.bucket_name = settings.SUPABASE_STORAGE_BUCKET

    def upload_image(self, payload: DetectionInput) -> UploadedImage:
        """Store each upload under a date/UUID path so existing objects are not replaced."""
        image = read_image_input(payload)
        upload_date = datetime.now(UTC).strftime("%Y/%m/%d")
        object_path = f"{upload_date}/{uuid4().hex}{image.extension}"

        self.client.storage.from_(self.bucket_name).upload(
            path=object_path,
            file=image.data,
            file_options={
                "content-type": image.content_type,
                "cache-control": "3600",
                "upsert": "false",
            },
        )
        public_url = self.client.storage.from_(self.bucket_name).get_public_url(
            object_path
        )
        return UploadedImage(object_path=object_path, public_url=public_url)

    def delete_image(self, object_path: str) -> None:
        self.client.storage.from_(self.bucket_name).remove([object_path])


__all__ = ["StorageService", "UploadedImage"]

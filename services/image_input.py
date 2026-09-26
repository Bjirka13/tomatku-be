from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from pathlib import Path

from config import settings
from models.validation import DetectionInput


@dataclass(frozen=True)
class ImageInput:
    data: bytes
    extension: str
    content_type: str


def read_image_input(payload: DetectionInput) -> ImageInput:
    declared_content_type: str | None = None

    if payload.image_path is not None:
        file_path = Path(payload.image_path)
        if not file_path.is_file():
            raise ValueError(f"Unable to read image from path: {payload.image_path}")
        if file_path.stat().st_size > settings.MAX_IMAGE_SIZE_BYTES:
            raise ValueError("Image exceeds the maximum allowed size")
        image_bytes = file_path.read_bytes()
    elif payload.image_base64 is not None:
        encoded_image = payload.image_base64
        if encoded_image.startswith("data:"):
            try:
                header, encoded_image = encoded_image.split(",", maxsplit=1)
            except ValueError as exc:
                raise ValueError("Invalid base64 data URL") from exc

            header_parts = header[5:].lower().split(";")
            declared_content_type = header_parts[0]
            if declared_content_type not in {"image/jpeg", "image/png"}:
                raise ValueError("Only JPEG and PNG images are supported")
            if "base64" not in header_parts[1:]:
                raise ValueError("Image data URL must use base64 encoding")

        max_encoded_size = 4 * ((settings.MAX_IMAGE_SIZE_BYTES + 2) // 3)
        if len(encoded_image) > max_encoded_size:
            raise ValueError("Image exceeds the maximum allowed size")

        try:
            image_bytes = base64.b64decode(encoded_image, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Invalid base64 image data") from exc
    else:
        raise ValueError("Either image_path or image_base64 must be provided")

    if not image_bytes:
        raise ValueError("Image data is empty")
    if len(image_bytes) > settings.MAX_IMAGE_SIZE_BYTES:
        raise ValueError("Image exceeds the maximum allowed size")

    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        content_type = "image/png"
        extension = ".png"
    elif image_bytes.startswith(b"\xff\xd8\xff"):
        content_type = "image/jpeg"
        extension = ".jpg"
    else:
        raise ValueError("Only JPEG and PNG images are supported")

    if declared_content_type and declared_content_type != content_type:
        raise ValueError("Image data URL type does not match the image format")

    return ImageInput(
        data=image_bytes,
        extension=extension,
        content_type=content_type,
    )
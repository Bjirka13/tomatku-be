from __future__ import annotations

from typing import Any, cast

import cv2
import numpy as np

from config import settings
from database.repository import DetectionRepository
from models.validation import (
    ClassificationType,
    DetectionInput,
    DetectionResult,
    SeverityLevelType,
)
from services.model_service import ModelService
from services.image_input import read_image_input
from services.severity_service import SeverityService
from services.storage_service import StorageService


class DetectionService:
    def __init__(
        self,
        repository: DetectionRepository | None = None,
        storage_service: StorageService | None = None,
    ) -> None:
        self.repository = repository or DetectionRepository()
        self.model_service = ModelService()
        self.severity_service = SeverityService()
        self.storage_service = storage_service

    def _normalize_model_output(
        self,
        raw_result: dict[str, Any],
        fallback_classification: str | None = None,
        confidence_pct: float = 0.0,
        boxes: list[dict[str, Any]] | None = None,
    ) -> DetectionResult:
        """Enforce API labels and severity defaults before building the response model."""
        classification = fallback_classification or "unknown"
        severity_level = raw_result.get("severity_level")
        severity_pct = raw_result.get("severity_pct")

        if classification not in {"healthy", "early_blight", "unknown"}:
            classification = "unknown"

        if classification == "healthy":
            severity_level = None
            severity_pct = None
        elif severity_level not in {"ringan", "sedang", "parah"}:
            severity_level = "ringan"
            severity_pct = 0.0

        classification_value = cast(ClassificationType, classification)
        severity_value = cast(SeverityLevelType, severity_level)

        return DetectionResult(
            classification=classification_value,
            confidence_pct=round(float(confidence_pct), 2),
            severity_level=severity_value,
            severity_pct=(
                None
                if severity_pct is None
                else round(float(severity_pct), 2)
            ),
            boxes=boxes or [],
            source="model",
        )

    def predict_from_image(self, payload: DetectionInput) -> DetectionResult:
        """Decode either supported input form and use the strongest box for severity."""
        image_input = read_image_input(payload)
        image_array = np.frombuffer(image_input.data, dtype=np.uint8)
        image_bgr = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if image_bgr is None:
            raise ValueError("Unable to decode image data")
        image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

        classification, confidence_pct, boxes = self.model_service.predict(image)
        best_box = max(
            boxes,
            key=lambda item: item["confidence_pct"],
            default=None,
        )
        bounding_box = (
            None
            if best_box is None
            else (
                best_box["x1"],
                best_box["y1"],
                best_box["x2"],
                best_box["y2"],
            )
        )
        raw_result = self.severity_service.analyze(
            image,
            classification,
            bounding_box=bounding_box,
        )
        normalized = self._normalize_model_output(
            raw_result,
            classification,
            confidence_pct,
            boxes,
        )

        return normalized

    def save_prediction(
        self,
        prediction: DetectionResult,
        image_path: str | None = None,
        detection_mode: str = "capture",
        stream_id: str | None = None,
    ) -> dict[str, Any]:
        scan_id = self.repository.create_scan(
            detection_mode=detection_mode,
            stream_id=stream_id,
        )
        detection_id = self.repository.insert_detection_log(
            scan_id=scan_id,
            classification=prediction.classification,
            confidence_pct=prediction.confidence_pct,
            image_path=image_path,
            severity_level=prediction.severity_level,
            severity_pct=prediction.severity_pct,
        )
        return {
            "scan": {
                "id": scan_id,
                "detection_mode": detection_mode,
                "stream_id": stream_id,
            },
            "detection": {
                "id": detection_id,
                "classification": prediction.classification,
                "confidence_pct": prediction.confidence_pct,
                "image_path": image_path,
                "severity_level": prediction.severity_level,
                "severity_pct": prediction.severity_pct,
            },
        }

    def process_image(self, payload: DetectionInput) -> dict[str, Any]:
        """Filter realtime frames before storing images and detection records."""
        prediction = self.predict_from_image(payload)
        claim_token = None
        if payload.mode == "realtime":
            if payload.stream_id is None:
                raise ValueError("stream_id is required for realtime detection")
            claim_token = self.repository.try_claim_realtime_capture(
                payload.stream_id,
                settings.REALTIME_CAPTURE_COOLDOWN_SECONDS,
            )
            if claim_token is None:
                return {
                    "prediction": prediction.model_dump(),
                    "saved": False,
                    "reason": "cooldown",
                    "scan": {
                        "detection_mode": payload.mode,
                        "stream_id": payload.stream_id,
                    },
                    "detection": None,
                }

        storage_service = self.storage_service
        uploaded_image = None
        try:
            storage_service = storage_service or StorageService()
            uploaded_image = storage_service.upload_image(payload)
            prediction.image_path = uploaded_image.public_url
            saved = self.save_prediction(
                prediction,
                image_path=uploaded_image.public_url,
                detection_mode=payload.mode,
                stream_id=payload.stream_id,
            )
        except Exception:
            try:
                if storage_service is not None and uploaded_image is not None:
                    storage_service.delete_image(uploaded_image.object_path)
            finally:
                if claim_token is not None and payload.stream_id is not None:
                    self.repository.release_realtime_capture(
                        payload.stream_id,
                        claim_token,
                    )
            raise

        return {
            "prediction": prediction.model_dump(),
            "saved": True,
            **saved,
        }


__all__ = ["DetectionService"]

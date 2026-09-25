from __future__ import annotations

from typing import Any, cast

import cv2
import numpy as np

from database.repository import DetectionRepository
from models.validation import (
    ClassificationType,
    DetectionInput,
    DetectionResult,
    SeverityLevelType,
)
from services.model_service import ModelService
from services.severity_service import SeverityService


class DetectionService:
    def __init__(self, repository: DetectionRepository | None = None) -> None:
        self.repository = repository or DetectionRepository()
        self.model_service = ModelService()
        self.severity_service = SeverityService()

    def _load_image_from_path(self, image_path: str) -> np.ndarray:
        image = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Unable to read image from path: {image_path}")
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def _normalize_model_output(
        self,
        raw_result: dict[str, Any],
        fallback_classification: str | None = None,
        confidence_pct: float = 0.0,
        boxes: list[dict[str, Any]] | None = None,
    ) -> DetectionResult:
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
        if payload.image_path:
            image = self._load_image_from_path(payload.image_path)
        elif payload.image_base64:
            import base64

            image_bytes = base64.b64decode(payload.image_base64)
            image_array = np.frombuffer(image_bytes, dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Unable to decode base64 image")
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            raise ValueError("Either image_path or image_base64 must be provided")

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
    ) -> dict[str, Any]:
        scan_id = self.repository.create_scan()
        detection_id = self.repository.insert_detection_log(
            scan_id=scan_id,
            classification=prediction.classification,
            confidence_pct=prediction.confidence_pct,
            image_path=image_path,
            severity_level=prediction.severity_level,
            severity_pct=prediction.severity_pct,
        )
        return {
            "scan_id": scan_id,
            "detection_id": detection_id,
            "classification": prediction.classification,
            "confidence_pct": prediction.confidence_pct,
            "image_path": image_path,
            "severity_level": prediction.severity_level,
            "severity_pct": prediction.severity_pct,
        }

    def process_image(self, payload: DetectionInput) -> dict[str, Any]:
        prediction = self.predict_from_image(payload)
        prediction.image_path = payload.image_path
        saved = self.save_prediction(prediction, image_path=payload.image_path)
        return {"prediction": prediction.model_dump(), **saved}


__all__ = ["DetectionService"]

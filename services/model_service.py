from __future__ import annotations

from typing import Any

import numpy as np

from config import settings


class ModelService:
    def __init__(self) -> None:
        self.model = self._load_model()

    @staticmethod
    def _load_model() -> Any:
        from importlib import import_module

        yolo_class = import_module("ultralytics").YOLO
        model_path = settings.resolve_path(settings.MODEL_PATH)

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        return yolo_class(str(model_path))

    def predict(self, image: np.ndarray) -> tuple[str, float, list[dict[str, Any]]]:
        results = self.model.predict(source=image, verbose=False)
        boxes: list[dict[str, Any]] = []

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence_pct = float(box.conf[0]) * 100
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                model_class = str(self.model.names[class_id])
                normalized_class = model_class.strip().lower().replace(" ", "_")
                classification = {
                    "0": "early_blight",
                    "1": "healthy",
                    "early_blight": "early_blight",
                    "earlyblight": "early_blight",
                    "healthy": "healthy",
                }.get(normalized_class, "unknown")

                boxes.append({
                    "x1": round(float(x1), 2),
                    "y1": round(float(y1), 2),
                    "x2": round(float(x2), 2),
                    "y2": round(float(y2), 2),
                    "classification": classification,
                    "confidence_pct": round(confidence_pct, 2),
                })

        if not boxes:
            return "unknown", 0.0, []

        best_box = max(boxes, key=lambda item: item["confidence_pct"])
        return (
            str(best_box["classification"]),
            float(best_box["confidence_pct"]),
            boxes,
        )


__all__ = ["ModelService"]

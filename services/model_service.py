from __future__ import annotations

from typing import Any

# pyrefly: ignore[missing-import]
import numpy as np

# pyrefly: ignore[missing-import]
from config import settings


class ModelService:
    def __init__(self) -> None:
        self.model = self._load_model()

    @staticmethod
    def _load_model() -> Any:
        """Import the inference package only when loading the configured model."""
        from importlib import import_module

        yolo_class = import_module("ultralytics").YOLO
        model_path = settings.resolve_path(settings.MODEL_PATH)

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        return yolo_class(str(model_path))

    def predict(self, image: np.ndarray) -> tuple[str, float, list[dict[str, Any]]]:
        """Normalize model labels and return all boxes plus the strongest prediction."""
        # pyrefly: ignore[missing-import]
        import torch

        results = self.model.predict(
            source=image,
            imgsz=640,
            conf=0.45,
            iou=0.5,
            verbose=False,
            device=0 if torch.cuda.is_available() else "cpu",
        )
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

        # prioritize boxes: first by disease classification, then by confidence percentage
        def box_priority(item: dict[str, Any]) -> tuple[int, float]:
                    is_disease = 1 if item["classification"] == "early_blight" else 0
                    return(is_disease, item["confidence_pct"])
        
        best_box = max(boxes, key=box_priority)
        return (
            str(best_box["classification"]),
            float(best_box["confidence_pct"]),
            boxes,
        )


__all__ = ["ModelService"]

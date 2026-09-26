"""Reusable external preprocessing for Tomatku inference."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np


DEFAULT_CONFIG: dict[str, Any] = {
    "pipeline_name": "tomatku_external_severity",
    "pipeline_version": "1.0.0",
    "model_class_mapping": {
        "0": "early_blight",
        "1": "healthy",
    },
    "crop": [0, 650, 500, 1300],
    "leaf_hsv_lower": [25, 35, 30],
    "leaf_hsv_upper": [95, 255, 255],
    "symptom_hsv_lower": [5, 35, 20],
    "symptom_hsv_upper": [40, 255, 230],
    "morphology_kernel_size": 5,
    "severity_thresholds": {
        "light_max_pct": 10.0,
        "medium_max_pct": 30.0,
    },
    "database_severity_mapping": {
        "healthy": None,
        "ringan": "ringan",
        "sedang": "sedang",
        "berat": "parah",
        "parah": "parah",
    },
}


class ExternalSeverityPipeline:
    """Calculate symptom area and database-compatible severity."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Preserve an explicitly supplied config, including an intentionally empty one."""
        self.config = config if config is not None else DEFAULT_CONFIG

    def _crop_image(
        self,
        image_rgb: np.ndarray,
        bounding_box: tuple[float, float, float, float] | None = None,
    ) -> np.ndarray:
        """Clamp crop coordinates to the image; invalid or absent crops use the full image."""
        crop = bounding_box if bounding_box is not None else self.config.get("crop")

        if crop is None:
            return image_rgb

        x1, y1, x2, y2 = (int(round(value)) for value in crop)
        height, width = image_rgb.shape[:2]
        x1 = max(0, min(x1, width))
        y1 = max(0, min(y1, height))
        x2 = max(0, min(x2, width))
        y2 = max(0, min(y2, height))

        if x2 <= x1 or y2 <= y1:
            return image_rgb

        return image_rgb[y1:y2, x1:x2]

    @staticmethod
    def _largest_component(mask: np.ndarray) -> np.ndarray:
        """Keep the largest foreground blob; connected-component label zero is background."""
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            mask,
            connectivity=8,
        )

        if num_labels <= 1:
            return mask

        largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        return np.where(labels == largest_label, 255, 0).astype(np.uint8)

    @staticmethod
    def _normalize_classification(classification: str | int | None) -> str | None:
        """Map known model IDs and spelling variants to the pipeline's canonical labels."""
        if classification is None:
            return None

        value = str(classification).strip().lower().replace(" ", "_")

        if value in {"healthy", "1"}:
            return "healthy"

        if value in {"early_blight", "earlyblight", "0"}:
            return "early_blight"

        if value == "unknown":
            return "unknown"

        return value

    def analyze(
        self,
        image_rgb: np.ndarray,
        classification: str | int | None = None,
        bounding_box: tuple[float, float, float, float] | None = None,
    ) -> dict[str, Any]:
        """Return no severity for healthy leaves; otherwise apply thresholds to leaf-area percentage."""
        normalized_classification = self._normalize_classification(classification)
        image = self._crop_image(image_rgb, bounding_box)
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        image_hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)

        leaf_mask = cv2.inRange(
            image_hsv,
            np.array(self.config["leaf_hsv_lower"]),
            np.array(self.config["leaf_hsv_upper"]),
        )

        kernel_size = self.config["morphology_kernel_size"]
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_OPEN, kernel)
        leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_CLOSE, kernel)
        leaf_mask = self._largest_component(leaf_mask)

        symptom_mask = cv2.inRange(
            image_hsv,
            np.array(self.config["symptom_hsv_lower"]),
            np.array(self.config["symptom_hsv_upper"]),
        )
        symptom_mask = cv2.bitwise_and(symptom_mask, leaf_mask)
        symptom_mask = cv2.morphologyEx(symptom_mask, cv2.MORPH_OPEN, kernel)
        symptom_mask = cv2.morphologyEx(symptom_mask, cv2.MORPH_CLOSE, kernel)

        leaf_pixels = int(np.sum(leaf_mask > 0))
        symptom_pixels = int(np.sum(symptom_mask > 0))
        severity_pct = symptom_pixels / leaf_pixels * 100 if leaf_pixels else 0.0

        thresholds = self.config["severity_thresholds"]
        if normalized_classification == "healthy":
            severity_level = None
            output_severity_pct = None
        elif severity_pct <= thresholds["light_max_pct"]:
            severity_level = "ringan"
            output_severity_pct = round(float(severity_pct), 2)
        elif severity_pct <= thresholds["medium_max_pct"]:
            severity_level = "sedang"
            output_severity_pct = round(float(severity_pct), 2)
        else:
            severity_level = "parah"
            output_severity_pct = round(float(severity_pct), 2)

        return {
            "severity_level": severity_level,
            "severity_pct": output_severity_pct,
            "leaf_pixels": leaf_pixels,
            "symptom_pixels": symptom_pixels,
            "leaf_mask": leaf_mask,
            "symptom_mask": symptom_mask,
        }

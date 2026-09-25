from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ClassificationType = Literal["healthy", "early_blight", "unknown"]
SeverityLevelType = Literal["ringan", "sedang", "parah"] | None


class DetectionInput(BaseModel):
    image_path: str | None = Field(default=None, description="Path to image file")
    image_base64: str | None = Field(default=None, description="Base64 image payload")
    classification: str | None = Field(default=None, description="Optional known classification")

# Expacted Detection Output
class DetectionResult(BaseModel):
    classification: ClassificationType
    confidence_pct: float = Field(ge=0.0, le=100.0)
    image_path: str | None = None
    severity_level: SeverityLevelType
    severity_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    boxes: list[dict[str, Any]] = Field(default_factory=list)
    source: str = Field(default="model")

    @property
    def confidence_ratio(self) -> float:
        return max(0.0, min(1.0, self.confidence_pct / 100.0))

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


ClassificationType = Literal["healthy", "early_blight", "unknown"]
SeverityLevelType = Literal["ringan", "sedang", "parah"] | None


class DetectionInput(BaseModel):
    image_path: str | None = Field(
        default=None,
        description="Path to an image file accessible by the backend",
    )
    image_base64: str | None = Field(
        default=None,
        description="Base64 image data or a data URL; use this for browser uploads",
    )

    @model_validator(mode="after")
    def validate_image_source(self) -> DetectionInput:
        sources = [self.image_path, self.image_base64]
        provided_sources = [source for source in sources if source is not None]
        if len(provided_sources) != 1 or not provided_sources[0].strip():
            raise ValueError(
                "Provide exactly one non-empty image_path or image_base64"
            )
        return self

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
        """Convert percent to a bounded 0-1 ratio for consumers that need fractions."""
        return max(0.0, min(1.0, self.confidence_pct / 100.0))

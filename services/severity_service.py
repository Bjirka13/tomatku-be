from __future__ import annotations

import importlib.util
from typing import Any

import numpy as np

from config import settings


class SeverityService:
    def __init__(self) -> None:
        # Load the configured pipeline without coupling it to this service
        pipeline_path = settings.resolve_path(settings.PIPELINE_PATH)
        if not pipeline_path.exists():
            raise FileNotFoundError(f"Pipeline file not found: {pipeline_path}")

        spec = importlib.util.spec_from_file_location(
            "tomatku_external_pipeline",
            pipeline_path,
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load pipeline module: {pipeline_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.pipeline = module.ExternalSeverityPipeline()

    def analyze(
        self,
        image: np.ndarray,
        classification: str,
        bounding_box: tuple[float, float, float, float] | None = None,
    ) -> dict[str, Any]:
        """Delegate severity calculation to the external pipeline."""
        return self.pipeline.analyze(
            image,
            classification=classification,
            bounding_box=bounding_box,
        )


__all__ = ["SeverityService"]

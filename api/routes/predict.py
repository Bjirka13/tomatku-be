from __future__ import annotations

from fastapi import APIRouter, HTTPException

from models.validation import DetectionInput
from services.detection_service import DetectionService

from typing import Any

router = APIRouter(prefix="/api", tags=["detection"])
service = DetectionService()


@router.post("/detect")
async def detect_leaf(payload: DetectionInput) -> dict[str, Any]:
    try:
        result = service.process_image(payload)
        return {"status": "success", "data": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Detection failed: {exc}") from exc

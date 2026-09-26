from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from database.repository import DetectionRepository

router = APIRouter(prefix="/api", tags=["history"])
repository = DetectionRepository()


@router.get("/history")
def get_history() -> dict[str, Any]:
    try:
        history = repository.get_scan_history()
        return {"status": "success", "data": history}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve scan history",
        ) from exc
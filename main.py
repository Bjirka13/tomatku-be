from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.predict import router as detection_router
from config import settings
from database.connection import DatabaseConnection


# API Create Function
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME or "TomatKU API",
        version="0.1.0",
        description="Backend API for tomato leaf detection and scan history.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        try:
            DatabaseConnection().execute("SELECT 1;", fetch=True)
            db_status = "ok"
        except Exception:
            db_status = "unavailable"

        return {"status": "ok", "service": "tomatku-be", "database": db_status}

    app.include_router(detection_router)
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST or "0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT.lower() == "development",
    )

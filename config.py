from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"


def _load_env_file() -> None:
    if not ENV_FILE.exists():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file()


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "")
    HOST: str = os.getenv("HOST", "")
    PORT: int = int(os.getenv("PORT", "8000"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "")

    DB_HOST: str = os.getenv("DB_HOST", "")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SUPABASE_DATABASE_URL: str = os.getenv("SUPABASE_DATABASE_URL", "")

    MODEL_PATH: Path = Path(os.getenv("MODEL_PATH", "artifact/best.pt"))
    PIPELINE_PATH: Path = Path(
        os.getenv("PIPELINE_PATH", "artifact/external_pipeline.py")
    )

    def resolve_path(self, path: Path) -> Path:
        if path.is_absolute():
            return path
        return BASE_DIR / path

    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]


settings = Settings()

__all__ = ["settings", "Settings"]

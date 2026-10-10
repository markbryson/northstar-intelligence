"""Application configuration loaded from environment variables."""

from dataclasses import dataclass, field
import os


def _load_cors_origins() -> list[str]:
    raw_origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:4173,http://127.0.0.1:5173,http://127.0.0.1:4173",
    )
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


def _load_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


@dataclass(frozen=True)
class Settings:
    """Runtime settings with safe development defaults."""

    project_name: str = os.getenv(
        "PROJECT_NAME", "Business Intelligence Analytics Platform"
    )
    version: str = os.getenv("APP_VERSION", "0.1.0")
    database_path: str = os.getenv("DATABASE_PATH", "data/database/retail.db")
    database_read_only: bool = field(
        default_factory=lambda: _load_bool("DATABASE_READ_ONLY")
    )
    cors_origins: list[str] | None = None

    def __post_init__(self) -> None:
        if self.cors_origins is None:
            object.__setattr__(self, "cors_origins", _load_cors_origins())


def get_settings() -> Settings:
    """Return application settings for the current process environment."""
    return Settings()

import sqlite3

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.api.analytics import router as analytics_router


settings = get_settings()

app = FastAPI(
    title=settings.project_name,
    description="Backend foundation for retail and e-commerce business intelligence.",
    version=settings.version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics_router)


@app.get("/", tags=["system"])
def read_root() -> dict[str, str]:
    """Return basic project information."""
    return {
        "project": settings.project_name,
        "version": settings.version,
        "status": "running",
    }


@app.get("/api/health", tags=["system"])
def health_check() -> JSONResponse:
    """Return whether the backend and analytics database are usable."""
    from backend.database import connect_database

    try:
        connection = connect_database(settings.database_path, initialize_schema=False)
        try:
            connection.execute("SELECT 1 FROM transactions LIMIT 1").fetchone()
        finally:
            connection.close()
    except (OSError, sqlite3.Error):
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "backend",
                "detail": {
                    "code": "database_unavailable",
                    "message": "Analytics database is unavailable",
                },
            },
        )
    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "service": "backend"},
    )

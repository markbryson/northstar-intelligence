import sqlite3
from dataclasses import replace

from fastapi.testclient import TestClient

import backend.api.analytics as analytics_api
import backend.main as main_module
from backend.database import connect_database
from backend.main import app


client = TestClient(app)


def test_root_endpoint() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "project": "Business Intelligence Analytics Platform",
        "version": "0.1.0",
        "status": "running",
    }


def test_health_endpoint(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "retail.db"
    connection = connect_database(database_path)
    original_settings = main_module.settings
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(original_settings, database_path=str(database_path)),
    )
    try:
        response = client.get("/api/health")
    finally:
        connection.close()

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "backend"}


def test_health_endpoint_reports_missing_database_without_creating_it(tmp_path, monkeypatch) -> None:
    missing_path = tmp_path / "missing.db"
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(main_module.settings, database_path=str(missing_path)),
    )

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unhealthy",
        "service": "backend",
        "detail": {
            "code": "database_unavailable",
            "message": "Analytics database is unavailable",
        },
    }
    assert not missing_path.exists()


def test_health_endpoint_supports_read_only_database(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "retail.db"
    connection = connect_database(database_path)
    connection.close()
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(
            main_module.settings,
            database_path=str(database_path),
            database_read_only=True,
        ),
    )

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "backend"}


def test_analytics_missing_database_returns_structured_error(tmp_path, monkeypatch) -> None:
    missing_path = tmp_path / "missing.db"
    monkeypatch.setattr(
        analytics_api,
        "settings",
        replace(analytics_api.settings, database_path=str(missing_path)),
    )

    response = client.get("/api/analytics/overview")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "database_unavailable",
            "message": "Analytics database is unavailable",
        }
    }
    assert not missing_path.exists()


def test_analytics_database_failure_returns_structured_error(monkeypatch) -> None:
    def fail_to_connect(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked: C:\\sensitive\\retail.db")

    monkeypatch.setattr(analytics_api, "connect_database", fail_to_connect)

    response = client.get("/api/analytics/overview")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "database_unavailable",
            "message": "Analytics database is unavailable",
        }
    }

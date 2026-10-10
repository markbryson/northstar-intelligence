import math
import sqlite3
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

import backend.api.analytics as analytics_api
from backend.main import app


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_DATABASE = PROJECT_ROOT / "data/database/retail.db"
DEPLOYMENT_DATABASE = PROJECT_ROOT / "data/database/retail_deployment.db"

FILTER_CASES = {
    "unfiltered": {},
    "date": {"start_date": "2010-01-01", "end_date": "2010-12-31"},
    "country": {"country": "United Kingdom"},
    "date_country": {
        "start_date": "2010-01-01",
        "end_date": "2010-12-31",
        "country": "United Kingdom",
    },
}

ENDPOINTS = {
    "overview": ("/api/analytics/overview", {}),
    "sales_trends": ("/api/analytics/sales-trends", {"granularity": "month"}),
    "top_products": ("/api/analytics/top-products", {"limit": 100, "offset": 0}),
    "customers": ("/api/analytics/customers", {"limit": 100, "offset": 0}),
    "countries": ("/api/analytics/countries", {"limit": 100, "offset": 0}),
    "returns": ("/api/analytics/returns", {}),
    "filters": ("/api/analytics/filters", {}),
}


def _read_only_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        f"{path.resolve().as_uri()}?mode=ro",
        uri=True,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    return connection


def _collect_responses(database_path: Path) -> dict[str, dict[str, Any]]:
    if not database_path.is_file():
        raise AssertionError(f"Required parity database is missing: {database_path}")

    connection = _read_only_connection(database_path)
    client = TestClient(app)

    def override_db():
        yield connection

    app.dependency_overrides[analytics_api.get_db] = override_db
    try:
        responses: dict[str, dict[str, Any]] = {}
        for filter_name, filters in FILTER_CASES.items():
            for endpoint_name, (path, endpoint_params) in ENDPOINTS.items():
                params = {**endpoint_params, **filters}
                response = client.get(path, params=params)
                assert response.status_code == 200, (
                    f"{database_path.name} {endpoint_name} {filter_name} "
                    f"returned {response.status_code}: {response.text}"
                )
                responses[f"{endpoint_name}:{filter_name}"] = response.json()
        return responses
    finally:
        app.dependency_overrides.pop(analytics_api.get_db, None)
        connection.close()


def _assert_json_equal(expected: Any, actual: Any, path: str = "$") -> None:
    if isinstance(expected, dict) and isinstance(actual, dict):
        assert set(actual) == set(expected), f"{path}: response keys differ"
        for key in expected:
            _assert_json_equal(expected[key], actual[key], f"{path}.{key}")
        return
    if isinstance(expected, list) and isinstance(actual, list):
        assert len(actual) == len(expected), f"{path}: list lengths differ"
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            _assert_json_equal(expected_item, actual_item, f"{path}[{index}]")
        return
    if isinstance(expected, bool) or isinstance(actual, bool):
        assert actual == expected, f"{path}: {actual!r} != {expected!r}"
        return
    if isinstance(expected, float) or isinstance(actual, float):
        assert math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-9), (
            f"{path}: {actual!r} != {expected!r}"
        )
        return
    assert actual == expected, f"{path}: {actual!r} != {expected!r}"


def test_all_analytics_endpoints_match_original_and_deployment_databases() -> None:
    original = _collect_responses(ORIGINAL_DATABASE)
    deployment = _collect_responses(DEPLOYMENT_DATABASE)

    assert set(deployment) == set(original)
    for request_name, expected in original.items():
        _assert_json_equal(expected, deployment[request_name], request_name)

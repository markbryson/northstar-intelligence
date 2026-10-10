"""Benchmark analytics API response times against both SQLite databases."""

from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path
from statistics import median

from fastapi.testclient import TestClient

import backend.api.analytics as analytics_api
from backend.main import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASES = {
    "original": PROJECT_ROOT / "data/database/retail.db",
    "compact": PROJECT_ROOT / "data/database/retail_deployment.db",
}

FILTER_CASES = {
    "unfiltered": {},
    "date": {"start_date": "2010-01-01", "end_date": "2010-12-31"},
    "country": {"country": "United Kingdom"},
    "date+country": {
        "start_date": "2010-01-01",
        "end_date": "2010-12-31",
        "country": "United Kingdom",
    },
}

ENDPOINTS = {
    "overview": ("/api/analytics/overview", {}),
    "sales-trends": ("/api/analytics/sales-trends", {"granularity": "month"}),
    "top-products": ("/api/analytics/top-products", {"limit": 100, "offset": 0}),
    "customers": ("/api/analytics/customers", {"limit": 100, "offset": 0}),
    "countries": ("/api/analytics/countries", {"limit": 100, "offset": 0}),
    "returns": ("/api/analytics/returns", {}),
    "filters": ("/api/analytics/filters", {}),
}

SLOWDOWN_THRESHOLD_PERCENT = 25.0


def _read_only_connection(path: Path) -> sqlite3.Connection:
    """Open an existing database read-only and safely share it with TestClient."""
    connection = sqlite3.connect(
        f"{path.resolve().as_uri()}?mode=ro",
        uri=True,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    return connection


def _benchmark_database(path: Path, repetitions: int) -> dict[tuple[str, str], float]:
    if not path.is_file():
        raise FileNotFoundError(f"Required benchmark database is missing: {path}")

    connection = _read_only_connection(path)
    client = TestClient(app)

    def override_db():
        yield connection

    app.dependency_overrides[analytics_api.get_db] = override_db
    try:
        results: dict[tuple[str, str], float] = {}
        for filter_name, filters in FILTER_CASES.items():
            for endpoint_name, (endpoint, endpoint_params) in ENDPOINTS.items():
                durations: list[float] = []
                params = {**endpoint_params, **filters}
                for _ in range(repetitions):
                    started = time.perf_counter()
                    response = client.get(endpoint, params=params)
                    elapsed_ms = (time.perf_counter() - started) * 1000
                    if response.status_code != 200:
                        raise RuntimeError(
                            f"{path.name} {endpoint_name} {filter_name} returned "
                            f"HTTP {response.status_code}: {response.text}"
                        )
                    durations.append(elapsed_ms)
                results[(endpoint_name, filter_name)] = median(durations)
        return results
    finally:
        app.dependency_overrides.pop(analytics_api.get_db, None)
        connection.close()


def _format_difference(original_ms: float, compact_ms: float) -> tuple[str, str]:
    if original_ms == 0:
        return "n/a", ""
    difference = ((compact_ms - original_ms) / original_ms) * 100
    if difference >= SLOWDOWN_THRESHOLD_PERCENT:
        return f"+{difference:.1f}%", "SLOWDOWN"
    if difference >= 0:
        return f"+{difference:.1f}%", ""
    return f"{difference:.1f}%", "FASTER"


def _print_report(
    original: dict[tuple[str, str], float],
    compact: dict[tuple[str, str], float],
) -> None:
    print("Northstar Intelligence analytics API benchmark")
    print(f"Median of measured requests; substantial slowdown threshold: {SLOWDOWN_THRESHOLD_PERCENT:.0f}%")
    print()
    print(f"{'Endpoint':<16} {'Filters':<14} {'Original ms':>12} {'Compact ms':>12} {'Difference':>12}  Status")
    print("-" * 82)
    for key in original:
        original_ms = original[key]
        compact_ms = compact[key]
        difference, status = _format_difference(original_ms, compact_ms)
        print(
            f"{key[0]:<16} {key[1]:<14} {original_ms:>12.2f} "
            f"{compact_ms:>12.2f} {difference:>12}  {status}"
        )

    slowdowns = [
        (key, original[key], compact[key])
        for key in original
        if original[key] > 0
        and ((compact[key] - original[key]) / original[key]) * 100 >= SLOWDOWN_THRESHOLD_PERCENT
    ]
    if slowdowns:
        print()
        print("Substantial compact-database slowdowns:")
        for (endpoint, filters), original_ms, compact_ms in slowdowns:
            difference = ((compact_ms - original_ms) / original_ms) * 100
            print(f"- {endpoint} ({filters}): +{difference:.1f}%")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repetitions",
        type=int,
        default=1,
        help="Measured requests per endpoint/filter/database (default: 1)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be at least 1")

    results = {
        database_name: _benchmark_database(path, args.repetitions)
        for database_name, path in DATABASES.items()
    }
    _print_report(results["original"], results["compact"])


if __name__ == "__main__":
    main()

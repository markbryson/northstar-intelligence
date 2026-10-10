"""Isolated experiment for the compact database validation-status index."""

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
ORIGINAL_DATABASE = PROJECT_ROOT / "data/database/retail.db"
COMPACT_DATABASE = PROJECT_ROOT / "data/database/retail_deployment.db"
TEST_DATABASE = PROJECT_ROOT / "data/database/retail_index_test.db"
INDEX_SQL = "CREATE INDEX idx_transactions_validation_status ON transactions (validation_status)"
EXPECTED_SCHEMA = (
    ("invoice_no", "TEXT", 1),
    ("stock_code", "TEXT", 1),
    ("description", "TEXT", 0),
    ("quantity", "INTEGER", 0),
    ("invoice_date", "TEXT", 0),
    ("customer_id", "TEXT", 0),
    ("country", "TEXT", 0),
    ("is_cancelled", "INTEGER", 1),
    ("is_return", "INTEGER", 1),
    ("gross_sales", "REAL", 1),
    ("return_amount", "REAL", 1),
    ("net_sales", "REAL", 1),
    ("validation_status", "TEXT", 1),
)

ENDPOINTS = {
    "overview": "/api/analytics/overview",
    "sales-trends": "/api/analytics/sales-trends?granularity=month",
    "returns": "/api/analytics/returns",
}

ANALYTICS_SQL = {
    "overview": """
        WITH filtered AS (
            SELECT t.* FROM transactions t WHERE t.validation_status = 'valid'
        ), order_totals AS (
            SELECT invoice_no, SUM(net_sales) AS order_net_sales
            FROM filtered
            WHERE is_cancelled = 0 AND gross_sales > 0
            GROUP BY invoice_no
        )
        SELECT
            ROUND(COALESCE((SELECT SUM(gross_sales) FROM filtered), 0.0), 2),
            ROUND(COALESCE((SELECT SUM(return_amount) FROM filtered), 0.0), 2),
            ROUND(COALESCE((SELECT SUM(net_sales) FROM filtered), 0.0), 2),
            (SELECT COUNT(*) FROM filtered),
            (SELECT COUNT(DISTINCT customer_id) FROM filtered WHERE customer_id IS NOT NULL),
            (SELECT COUNT(*) FROM order_totals),
            ROUND(COALESCE((SELECT SUM(order_net_sales) / NULLIF(COUNT(*), 0) FROM order_totals), 0.0), 2)
    """,
    "sales-trends": """
        SELECT substr(t.invoice_date, 1, 7) AS period,
               ROUND(SUM(t.gross_sales), 2),
               ROUND(SUM(t.return_amount), 2),
               ROUND(SUM(t.net_sales), 2),
               COUNT(*),
               COUNT(DISTINCT CASE WHEN t.is_cancelled = 0 AND t.gross_sales > 0 THEN t.invoice_no END)
        FROM transactions t
        WHERE t.validation_status = 'valid'
        GROUP BY period
        ORDER BY period
    """,
    "returns": """
        SELECT
            COALESCE(SUM(CASE WHEN t.is_return = 1 AND t.quantity < 0 THEN ABS(t.quantity) ELSE 0 END), 0),
            ROUND(COALESCE(SUM(t.return_amount), 0.0), 2),
            SUM(CASE WHEN t.is_return = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN t.is_cancelled = 1 THEN 1 ELSE 0 END),
            ROUND(COALESCE(SUM(CASE WHEN t.is_cancelled = 1 THEN t.return_amount ELSE 0 END), 0.0), 2),
            COUNT(*)
        FROM transactions t
        WHERE t.validation_status = 'valid'
    """,
}


def _read_only_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        f"{path.resolve().as_uri()}?mode=ro",
        uri=True,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    return connection


def _create_test_copy() -> None:
    if not ORIGINAL_DATABASE.is_file():
        raise FileNotFoundError(f"Original database is missing: {ORIGINAL_DATABASE}")
    if not COMPACT_DATABASE.is_file():
        raise FileNotFoundError(f"Compact database is missing: {COMPACT_DATABASE}")
    source = _read_only_connection(COMPACT_DATABASE)
    destination: sqlite3.Connection | None = None
    try:
        destination = sqlite3.connect(TEST_DATABASE)
        source.backup(destination)
        destination.commit()
    finally:
        source.close()
        if destination is not None:
            destination.close()


def _validate_existing_test_database() -> None:
    connection = _read_only_connection(TEST_DATABASE)
    compact = _read_only_connection(COMPACT_DATABASE)
    try:
        schema = tuple(
            (row["name"], row["type"], row["notnull"])
            for row in connection.execute("PRAGMA table_info(transactions)")
        )
        if schema != EXPECTED_SCHEMA:
            raise RuntimeError(
                "Existing experiment database has an unexpected transactions schema"
            )

        index_row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'index' "
            "AND name = 'idx_transactions_validation_status'"
        ).fetchone()
        normalized_sql = " ".join((index_row["sql"] if index_row else "").lower().split())
        expected_sql = " ".join(INDEX_SQL.lower().split())
        if normalized_sql != expected_sql:
            raise RuntimeError(
                "Existing experiment database has an unexpected validation-status index"
            )

        test_row_count = connection.execute(
            "SELECT COUNT(*) FROM transactions WHERE validation_status = 'valid'"
        ).fetchone()[0]
        invalid_count = connection.execute(
            "SELECT COUNT(*) FROM transactions WHERE validation_status <> 'valid'"
        ).fetchone()[0]
        compact_row_count = compact.execute(
            "SELECT COUNT(*) FROM transactions WHERE validation_status = 'valid'"
        ).fetchone()[0]
        if invalid_count != 0 or test_row_count != compact_row_count:
            raise RuntimeError(
                "Existing experiment database row count does not match the compact database"
            )
    finally:
        connection.close()
        compact.close()


def _ensure_test_database() -> None:
    if TEST_DATABASE.exists():
        _validate_existing_test_database()
        print(f"Reusing validated experiment database: {TEST_DATABASE}")
        return
    _create_test_copy()
    _add_index()


def _add_index() -> None:
    connection = sqlite3.connect(TEST_DATABASE)
    try:
        connection.execute(INDEX_SQL)
        connection.commit()
    finally:
        connection.close()


def _query_plans(path: Path) -> dict[str, list[str]]:
    connection = _read_only_connection(path)
    try:
        return {
            name: [row[3] for row in connection.execute("EXPLAIN QUERY PLAN " + query)]
            for name, query in ANALYTICS_SQL.items()
        }
    finally:
        connection.close()


def _benchmark(repetitions: int) -> dict[tuple[str, str], list[float]]:
    paths = {"compact": COMPACT_DATABASE, "indexed-test": TEST_DATABASE}
    connections = {name: _read_only_connection(path) for name, path in paths.items()}
    client = TestClient(app)
    results: dict[tuple[str, str], list[float]] = {
        (database, endpoint): []
        for database in paths
        for endpoint in ENDPOINTS
    }

    try:
        for repetition in range(repetitions):
            order = ("compact", "indexed-test") if repetition % 2 == 0 else ("indexed-test", "compact")
            for endpoint_name, endpoint in ENDPOINTS.items():
                for database_name in order:
                    connection = connections[database_name]

                    def override_db():
                        yield connection

                    app.dependency_overrides[analytics_api.get_db] = override_db
                    try:
                        started = time.perf_counter()
                        response = client.get(endpoint)
                        elapsed_ms = (time.perf_counter() - started) * 1000
                    finally:
                        app.dependency_overrides.pop(analytics_api.get_db, None)

                    if response.status_code != 200:
                        raise RuntimeError(
                            f"{database_name} {endpoint_name} returned HTTP "
                            f"{response.status_code}: {response.text}"
                        )
                    results[(database_name, endpoint_name)].append(elapsed_ms)
        return results
    finally:
        app.dependency_overrides.pop(analytics_api.get_db, None)
        for connection in connections.values():
            connection.close()


def _print_plans(before: dict[str, list[str]], after: dict[str, list[str]]) -> None:
    print("\nEXPLAIN QUERY PLAN comparison")
    for endpoint in ANALYTICS_SQL:
        print(f"\n{endpoint}")
        print("  Before (compact):")
        for detail in before[endpoint]:
            print(f"    {detail}")
        print("  After (indexed test):")
        for detail in after[endpoint]:
            print(f"    {detail}")


def _print_benchmark(results: dict[tuple[str, str], list[float]]) -> None:
    print("\nUnfiltered API benchmark medians")
    print(f"{'Endpoint':<16} {'Compact ms':>14} {'Indexed test ms':>17} {'Difference':>14}")
    print("-" * 66)
    for endpoint in ENDPOINTS:
        compact_ms = median(results[("compact", endpoint)])
        indexed_ms = median(results[("indexed-test", endpoint)])
        difference = ((indexed_ms - compact_ms) / compact_ms * 100) if compact_ms else 0.0
        print(f"{endpoint:<16} {compact_ms:>14.2f} {indexed_ms:>17.2f} {difference:>+13.1f}%")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repetitions",
        type=int,
        default=3,
        help="Measured requests per endpoint/database; order alternates each repetition (default: 3)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.repetitions < 3:
        raise SystemExit("--repetitions must be at least 3")

    _ensure_test_database()
    before = _query_plans(COMPACT_DATABASE)
    after = _query_plans(TEST_DATABASE)
    results = _benchmark(args.repetitions)
    print(f"Test database: {TEST_DATABASE} ({TEST_DATABASE.stat().st_size:,} bytes)")
    print("The test database is retained; remove it manually after inspection if desired.")
    _print_plans(before, after)
    _print_benchmark(results)


if __name__ == "__main__":
    main()

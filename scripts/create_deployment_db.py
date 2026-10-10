"""Create a compact, analytics-only SQLite database for deployment.

The source database is opened read-only. The deployment database is created
through a temporary sibling file and moved into place only after verification.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_SOURCE = Path("data/database/retail.db")
DEFAULT_OUTPUT = Path("data/database/retail_deployment.db")
DEFAULT_BATCH_SIZE = 10_000

DEPLOYMENT_COLUMNS = (
    "invoice_no",
    "stock_code",
    "description",
    "quantity",
    "invoice_date",
    "customer_id",
    "country",
    "is_cancelled",
    "is_return",
    "gross_sales",
    "return_amount",
    "net_sales",
    "validation_status",
)

CREATE_TABLE_SQL = """
CREATE TABLE transactions (
    invoice_no TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    description TEXT,
    quantity INTEGER,
    invoice_date TEXT,
    customer_id TEXT,
    country TEXT,
    is_cancelled INTEGER NOT NULL,
    is_return INTEGER NOT NULL,
    gross_sales REAL NOT NULL,
    return_amount REAL NOT NULL,
    net_sales REAL NOT NULL,
    validation_status TEXT NOT NULL
)
"""

CREATE_INDEX_SQL = (
    "CREATE INDEX idx_transactions_valid_date ON transactions (validation_status, invoice_date)",
    "CREATE INDEX idx_transactions_valid_country ON transactions (validation_status, country)",
    "CREATE INDEX idx_transactions_valid_customer ON transactions (validation_status, customer_id)",
    "CREATE INDEX idx_transactions_valid_invoice ON transactions (validation_status, invoice_no)",
    "CREATE INDEX idx_transactions_valid_product ON transactions (validation_status, stock_code)",
    "CREATE INDEX idx_transactions_validation_status ON transactions (validation_status)",
)

SUMMARY_SQL = """
SELECT
    COUNT(*) AS valid_row_count,
    ROUND(COALESCE(SUM(gross_sales), 0.0), 2) AS gross_sales,
    ROUND(COALESCE(SUM(return_amount), 0.0), 2) AS return_amount,
    ROUND(COALESCE(SUM(net_sales), 0.0), 2) AS net_sales,
    COUNT(DISTINCT CASE WHEN is_cancelled = 0 AND gross_sales > 0 THEN invoice_no END) AS order_count,
    COUNT(DISTINCT customer_id) AS customer_count,
    SUM(CASE WHEN is_return = 1 THEN 1 ELSE 0 END) AS returned_transaction_rows,
    ROUND(COALESCE(SUM(CASE WHEN is_cancelled = 1 THEN return_amount ELSE 0 END), 0.0), 2) AS cancellation_value
FROM transactions
WHERE validation_status = 'valid'
"""


def _read_only_connection(path: Path) -> sqlite3.Connection:
    """Open an existing SQLite file without allowing SQLite to create it."""
    uri = f"{path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _summary(connection: sqlite3.Connection) -> dict[str, Any]:
    row = connection.execute(SUMMARY_SQL).fetchone()
    if row is None:
        raise RuntimeError("Unable to calculate deployment verification summary")
    result = dict(row)
    for key in ("gross_sales", "return_amount", "net_sales", "cancellation_value"):
        result[key] = float(result[key] or 0.0)
    for key in (
        "valid_row_count",
        "order_count",
        "customer_count",
        "returned_transaction_rows",
    ):
        result[key] = int(result[key] or 0)
    return result


def _create_empty_deployment(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(CREATE_TABLE_SQL)
    for statement in CREATE_INDEX_SQL:
        connection.execute(statement)
    return connection


def create_deployment_db(
    source_path: str | Path = DEFAULT_SOURCE,
    output_path: str | Path = DEFAULT_OUTPUT,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """Export valid rows and verify analytics-preserving summary values."""
    source = Path(source_path).resolve()
    output = Path(output_path).resolve()
    if source == output:
        raise ValueError("Source and deployment database paths must be different")
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if not source.is_file():
        raise FileNotFoundError(f"Source database does not exist: {source}")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing deployment database: {output}")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    if temporary.exists():
        raise FileExistsError(f"Refusing to reuse existing temporary database: {temporary}")

    source_connection = _read_only_connection(source)
    deployment_connection: sqlite3.Connection | None = None
    try:
        source_summary = _summary(source_connection)
        deployment_connection = _create_empty_deployment(temporary)
        select_sql = """
        SELECT invoice_no, stock_code, description, quantity, invoice_date,
               customer_id, country, is_cancelled, is_return, gross_sales,
               return_amount, net_sales, validation_status
        FROM transactions
        WHERE validation_status = 'valid'
        ORDER BY rowid
        """
        insert_sql = (
            "INSERT INTO transactions ("
            + ", ".join(DEPLOYMENT_COLUMNS)
            + ") VALUES ("
            + ", ".join("?" for _ in DEPLOYMENT_COLUMNS)
            + ")"
        )
        cursor = source_connection.execute(select_sql)
        while rows := cursor.fetchmany(batch_size):
            deployment_connection.executemany(insert_sql, rows)
        deployment_connection.commit()
        deployment_summary = _summary(deployment_connection)
        if deployment_summary != source_summary:
            raise RuntimeError(
                "Deployment verification failed: source and deployment summaries differ"
            )
        deployment_connection.close()
        deployment_connection = None
        if output.exists():
            raise FileExistsError(f"Refusing to overwrite existing deployment database: {output}")
        os.replace(temporary, output)
        return {
            "source": str(source),
            "output": str(output),
            "source_bytes": source.stat().st_size,
            "output_bytes": output.stat().st_size,
            "source_summary": source_summary,
            "deployment_summary": deployment_summary,
        }
    finally:
        source_connection.close()
        if deployment_connection is not None:
            deployment_connection.close()
        if temporary.exists() and not output.exists():
            temporary.unlink()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = create_deployment_db(args.source, args.output, batch_size=args.batch_size)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

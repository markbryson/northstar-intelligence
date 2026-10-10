"""SQLite schema and connection helpers for retail transactions."""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS transactions (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    source_sheet TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    record_hash TEXT NOT NULL UNIQUE,
    invoice_no TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    description TEXT,
    quantity INTEGER,
    unit_price REAL,
    invoice_date TEXT,
    customer_id TEXT,
    country TEXT,
    is_cancelled INTEGER NOT NULL CHECK (is_cancelled IN (0, 1)),
    is_return INTEGER NOT NULL CHECK (is_return IN (0, 1)),
    gross_sales REAL NOT NULL DEFAULT 0 CHECK (gross_sales >= 0),
    return_amount REAL NOT NULL DEFAULT 0 CHECK (return_amount >= 0),
    net_sales REAL NOT NULL,
    validation_status TEXT NOT NULL CHECK (validation_status IN ('valid', 'invalid')),
    validation_errors TEXT,
    raw_quantity TEXT,
    raw_unit_price TEXT,
    raw_invoice_date TEXT,
    UNIQUE (source_file, source_sheet, source_row)
);

CREATE INDEX IF NOT EXISTS idx_transactions_invoice_date ON transactions (invoice_date);
CREATE INDEX IF NOT EXISTS idx_transactions_customer_id ON transactions (customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_stock_code ON transactions (stock_code);
CREATE INDEX IF NOT EXISTS idx_transactions_country ON transactions (country);
CREATE INDEX IF NOT EXISTS idx_transactions_validation_status ON transactions (validation_status);
CREATE INDEX IF NOT EXISTS idx_transactions_is_return ON transactions (is_return);
CREATE INDEX IF NOT EXISTS idx_transactions_valid_date ON transactions (validation_status, invoice_date);
CREATE INDEX IF NOT EXISTS idx_transactions_valid_country ON transactions (validation_status, country);
CREATE INDEX IF NOT EXISTS idx_transactions_valid_customer ON transactions (validation_status, customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_valid_invoice ON transactions (validation_status, invoice_no);
CREATE INDEX IF NOT EXISTS idx_transactions_valid_product ON transactions (validation_status, stock_code);
"""


def connect_database(
    database_path: str | Path,
    *,
    initialize_schema: bool = True,
    read_only: bool = False,
) -> sqlite3.Connection:
    """Connect to SQLite with optional schema initialization or read-only access."""
    path = Path(database_path)
    if read_only and initialize_schema:
        raise ValueError("Read-only connections cannot initialize the database schema")
    if initialize_schema:
        path.parent.mkdir(parents=True, exist_ok=True)
    elif not path.is_file():
        raise FileNotFoundError("Analytics database file is unavailable")

    if read_only:
        uri = f"{path.resolve().as_uri()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, check_same_thread=False)
    else:
        connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    if initialize_schema:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(SCHEMA)
    return connection


def get_transaction_counts(connection: sqlite3.Connection) -> dict[str, int]:
    """Return stored row counts split by validation status and transaction type."""
    result = connection.execute(
        """
        SELECT COUNT(*), SUM(validation_status = 'valid'),
               SUM(validation_status = 'invalid'), SUM(is_cancelled = 1),
               SUM(is_return = 1)
        FROM transactions
        """
    ).fetchone()
    return {
        "total": int(result[0] or 0),
        "valid": int(result[1] or 0),
        "invalid": int(result[2] or 0),
        "cancelled": int(result[3] or 0),
        "returns": int(result[4] or 0),
    }

import sqlite3
from pathlib import Path

import pytest

from backend.database import connect_database
from backend.services.analytics import (
    AnalyticsFilters,
    countries,
    customers,
    filter_options,
    overview,
    returns,
    sales_trends,
    top_products,
)
from scripts.create_deployment_db import DEPLOYMENT_COLUMNS, create_deployment_db


def _seed_source(path: Path) -> None:
    connection = connect_database(path)
    rows = [
        ("fixture.xlsx", "Transactions", 2, "fixture-hash-1", "1001", "A", "Alpha", 2, "2010-01-01T10:00:00", "1", "United Kingdom", 0, 0, 20.0, 0.0, 20.0, "valid"),
        ("fixture.xlsx", "Transactions", 3, "fixture-hash-2", "1001", "B", "Beta", 1, "2010-01-01T10:00:00", "1", "United Kingdom", 0, 0, 5.0, 0.0, 5.0, "valid"),
        ("fixture.xlsx", "Transactions", 4, "fixture-hash-3", "C1002", "A", "Alpha", -1, "2010-01-02T10:00:00", "2", "Kenya", 1, 1, 0.0, 10.0, -10.0, "valid"),
        ("fixture.xlsx", "Transactions", 5, "fixture-hash-4", "1003", "C", "Gamma", -2, "2010-01-03T10:00:00", "3", "Kenya", 0, 1, 0.0, 6.0, -6.0, "valid"),
        ("fixture.xlsx", "Transactions", 6, "fixture-hash-5", "1004", "D", "Invalid", 1, "2010-01-04T10:00:00", "4", "United Kingdom", 0, 0, 99.0, 0.0, 99.0, "invalid"),
    ]
    connection.executemany(
        """
        INSERT INTO transactions (
            source_file, source_sheet, source_row, record_hash,
            invoice_no, stock_code, description, quantity, invoice_date,
            customer_id, country, is_cancelled, is_return, gross_sales,
            return_amount, net_sales, validation_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    connection.commit()
    connection.close()


def test_export_preserves_valid_rows_and_analytics_contract(tmp_path: Path) -> None:
    source = tmp_path / "retail.db"
    output = tmp_path / "retail_deployment.db"
    _seed_source(source)

    result = create_deployment_db(source, output, batch_size=2)

    assert output.exists()
    assert result["source_summary"] == result["deployment_summary"]
    assert result["source_summary"] == {
        "valid_row_count": 4,
        "gross_sales": 25.0,
        "return_amount": 16.0,
        "net_sales": 9.0,
        "order_count": 1,
        "customer_count": 3,
        "returned_transaction_rows": 2,
        "cancellation_value": 10.0,
    }

    connection = sqlite3.connect(output)
    try:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(transactions)")]
        assert columns == list(DEPLOYMENT_COLUMNS)
        assert connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 4
        assert connection.execute("SELECT COUNT(*) FROM transactions WHERE validation_status = 'invalid'").fetchone()[0] == 0
        indexes = {row[1] for row in connection.execute("PRAGMA index_list(transactions)")}
        assert indexes == {
            "idx_transactions_valid_date",
            "idx_transactions_valid_country",
            "idx_transactions_valid_customer",
            "idx_transactions_valid_invoice",
            "idx_transactions_valid_product",
            "idx_transactions_validation_status",
        }
        validation_index_sql = connection.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type = 'index' AND name = 'idx_transactions_validation_status'"
        ).fetchone()[0]
        assert " ".join(validation_index_sql.lower().split()) == (
            "create index idx_transactions_validation_status "
            "on transactions (validation_status)"
        )
    finally:
        connection.close()

    original = sqlite3.connect(source)
    try:
        assert original.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 5
    finally:
        original.close()


def test_compact_database_works_with_existing_analytics_services(tmp_path: Path) -> None:
    source = tmp_path / "retail.db"
    output = tmp_path / "retail_deployment.db"
    _seed_source(source)
    create_deployment_db(source, output, batch_size=1)

    connection = sqlite3.connect(output)
    connection.row_factory = sqlite3.Row
    filters = AnalyticsFilters()
    try:
        assert overview(connection, filters)["net_sales"] == 9.0
        assert sales_trends(connection, filters, "day")[0]["transaction_count"] == 2
        assert top_products(connection, filters, 10, 0)[0]["stock_code"] == "A"
        assert customers(connection, filters, 10, 0)["customer_count"] == 3
        assert countries(connection, filters, 10, 0)[0]["country"] == "United Kingdom"
        assert returns(connection, filters)["return_value"] == 16.0
        assert filter_options(connection, filters)["countries"] == ["Kenya", "United Kingdom"]
    finally:
        connection.close()


def test_export_refuses_existing_output_and_same_path(tmp_path: Path) -> None:
    source = tmp_path / "retail.db"
    output = tmp_path / "retail_deployment.db"
    _seed_source(source)
    output.write_bytes(b"do not overwrite")

    with pytest.raises(FileExistsError):
        create_deployment_db(source, output)
    assert output.read_bytes() == b"do not overwrite"

    with pytest.raises(ValueError):
        create_deployment_db(source, source)

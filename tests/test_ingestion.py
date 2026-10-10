from pathlib import Path

from openpyxl import Workbook

from backend.database import connect_database, get_transaction_counts
from backend.ingestion import _clean_row, ingest_workbook


def _write_fixture(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Test"
    sheet.append(["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"])
    sheet.append(["10001", "A", "Sale", 2, "2010-01-01 10:00:00", 5.0, 1, "United Kingdom"])
    sheet.append(["10002", "B", "Missing customer", 1, "2010-01-01 11:00:00", 3.0, None, "United Kingdom"])
    sheet.append(["C10003", "C", "Cancellation", -1, "2010-01-01 12:00:00", 4.0, 2, "United Kingdom"])
    sheet.append(["10004", "D", "Return", -2, "2010-01-01 13:00:00", 2.5, 3, "United Kingdom"])
    sheet.append(["10005", "E", "Invalid quantity", 0, "2010-01-01 14:00:00", 2.0, 4, "United Kingdom"])
    sheet.append(["10006", "F", "Invalid price", 1, "2010-01-01 15:00:00", -1.0, 5, "United Kingdom"])
    sheet.append(["10001", "A", "Sale", 2, "2010-01-01 10:00:00", 5.0, 1, "United Kingdom"])
    workbook.save(path)


def test_ingestion_preserves_cases_and_is_repeatable(tmp_path: Path) -> None:
    workbook_path = tmp_path / "fixture.xlsx"
    database_path = tmp_path / "retail.db"
    _write_fixture(workbook_path)
    first = ingest_workbook(workbook_path, database_path, chunk_size=2)
    second = ingest_workbook(workbook_path, database_path, chunk_size=2)
    assert first["rows_read"] == 7
    assert first["inserted_rows"] == 6
    assert first["duplicate_rows"] == 1
    assert first["valid_rows"] == 5
    assert first["invalid_rows"] == 2
    assert second["inserted_rows"] == 0
    assert second["duplicate_rows"] == 7
    connection = connect_database(database_path)
    try:
        assert get_transaction_counts(connection) == {"total": 6, "valid": 4, "invalid": 2, "cancelled": 1, "returns": 2}
        assert connection.execute("SELECT customer_id FROM transactions WHERE invoice_no = '10002'").fetchone()[0] is None
        assert tuple(connection.execute("SELECT gross_sales, return_amount, net_sales FROM transactions WHERE invoice_no = 'C10003'").fetchone()) == (0.0, 4.0, -4.0)
    finally:
        connection.close()


def test_invalid_rows_zero_financial_amounts_but_preserve_raw_values() -> None:
    cleaned = _clean_row(
        "fixture.xlsx",
        "Test",
        2,
        {
            "Invoice": None,
            "StockCode": "A",
            "Description": "Missing invoice",
            "Quantity": 2,
            "InvoiceDate": "2010-01-01 10:00:00",
            "Price": 5.0,
            "Customer ID": 1,
            "Country": "United Kingdom",
        },
    )

    assert cleaned[17] == "invalid"
    assert cleaned[14:17] == (0.0, 0.0, 0.0)
    assert cleaned[19:22] == ("2", "5.0", "2010-01-01 10:00:00")

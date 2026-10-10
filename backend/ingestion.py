"""Streaming Online Retail II profiling and SQLite ingestion pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
from collections.abc import Iterable, Iterator
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import load_workbook

from backend.database import connect_database, get_transaction_counts


EXPECTED_COLUMNS = (
    "Invoice", "StockCode", "Description", "Quantity",
    "InvoiceDate", "Price", "Customer ID", "Country",
)

INSERT_SQL = """
INSERT OR IGNORE INTO transactions (
    source_file, source_sheet, source_row, record_hash, invoice_no,
    stock_code, description, quantity, unit_price, invoice_date,
    customer_id, country, is_cancelled, is_return, gross_sales,
    return_amount, net_sales, validation_status, validation_errors,
    raw_quantity, raw_unit_price, raw_invoice_date
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _text(value: Any) -> str | None:
    value = _json_value(value)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _record_hash(values: Iterable[Any]) -> str:
    canonical = json.dumps(
        [_json_value(value) for value in values],
        ensure_ascii=False, separators=(",", ":"), default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _number(value: Any) -> float | None:
    """Parse a finite numeric value without constructing a Pandas object per row."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _timestamp(value: Any) -> pd.Timestamp | None:
    if value is None:
        return None
    try:
        parsed = pd.Timestamp(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(parsed) else parsed


def iter_workbook_rows(input_path: str | Path) -> Iterator[tuple[str, int, dict[str, Any]]]:
    """Yield one raw row at a time from every worksheet without loading it all."""
    workbook = load_workbook(input_path, read_only=True, data_only=True)
    try:
        for worksheet in workbook.worksheets:
            rows = worksheet.iter_rows(values_only=True)
            header = next(rows, None)
            if header is None:
                continue
            header_names = [_text(value) for value in header]
            missing = [column for column in EXPECTED_COLUMNS if column not in header_names]
            if missing:
                raise ValueError(f"Worksheet {worksheet.title!r} is missing columns: {', '.join(missing)}")
            indexes = {column: header_names.index(column) for column in EXPECTED_COLUMNS}
            for source_row, row in enumerate(rows, start=2):
                values = {column: row[index] if index < len(row) else None for column, index in indexes.items()}
                yield worksheet.title, source_row, values
    finally:
        workbook.close()


def _clean_row(source_file: str, source_sheet: str, source_row: int, raw: dict[str, Any]) -> tuple[Any, ...]:
    invoice_no = _text(raw.get("Invoice"))
    stock_code = _text(raw.get("StockCode"))
    description = _text(raw.get("Description"))
    customer_id = _text(raw.get("Customer ID"))
    country = _text(raw.get("Country"))
    raw_quantity = _text(raw.get("Quantity"))
    raw_unit_price = _text(raw.get("Price"))
    raw_invoice_date = _text(raw.get("InvoiceDate"))
    is_cancelled = bool(invoice_no and invoice_no.upper().startswith("C"))
    errors: list[str] = []
    if not invoice_no:
        errors.append("missing_invoice_no")
    if not stock_code:
        errors.append("missing_stock_code")

    quantity_value = _number(raw.get("Quantity"))
    quantity: int | None = None
    if quantity_value is None or not quantity_value.is_integer() or quantity_value == 0:
        errors.append("invalid_quantity")
    else:
        quantity = int(quantity_value)

    price_value = _number(raw.get("Price"))
    unit_price: float | None = None
    if price_value is None or price_value < 0:
        errors.append("invalid_unit_price")
    else:
        unit_price = float(price_value)

    parsed_date = _timestamp(raw.get("InvoiceDate"))
    invoice_date = None if pd.isna(parsed_date) else parsed_date.isoformat()
    if invoice_date is None:
        errors.append("invalid_invoice_date")

    is_return = bool(is_cancelled or (quantity is not None and quantity < 0))
    validation_status = "valid" if not errors else "invalid"
    amount = (
        abs(quantity * unit_price)
        if validation_status == "valid" and quantity is not None and unit_price is not None
        else 0.0
    )
    gross_sales = amount if quantity is not None and quantity > 0 and not is_cancelled else 0.0
    return_amount = amount if is_return else 0.0
    net_sales = gross_sales - return_amount
    return (
        source_file, source_sheet, source_row, _record_hash(raw.values()), invoice_no or "", stock_code or "",
        description, quantity, unit_price, invoice_date, customer_id, country, int(is_cancelled), int(is_return),
        gross_sales, return_amount, net_sales, validation_status,
        ";".join(errors) or None, raw_quantity, raw_unit_price, raw_invoice_date,
    )


def profile_workbook(input_path: str | Path) -> dict[str, Any]:
    """Profile columns, nulls, duplicates, types, and transaction characteristics."""
    rows_read = 0
    fingerprints: set[str] = set()
    column_nulls = {column: 0 for column in EXPECTED_COLUMNS}
    sheets: dict[str, int] = {}
    quantity_values: list[float] = []
    price_values: list[float] = []
    invoice_dates: list[pd.Timestamp] = []
    cancellations = negative_quantities = 0
    for sheet, _, raw in iter_workbook_rows(input_path):
        rows_read += 1
        sheets[sheet] = sheets.get(sheet, 0) + 1
        for column in EXPECTED_COLUMNS:
            if _json_value(raw.get(column)) is None:
                column_nulls[column] += 1
        fingerprints.add(_record_hash(raw.values()))
        invoice = _text(raw.get("Invoice"))
        cancellations += int(bool(invoice and invoice.upper().startswith("C")))
        quantity = _number(raw.get("Quantity"))
        price = _number(raw.get("Price"))
        if quantity is not None:
            quantity_values.append(quantity)
            negative_quantities += int(quantity < 0)
        if price is not None:
            price_values.append(price)
        parsed_date = _timestamp(raw.get("InvoiceDate"))
        if parsed_date is not None:
            invoice_dates.append(parsed_date)
    return {
        "source": "UCI Machine Learning Repository, dataset 502",
        "input_file": str(input_path), "rows_read": rows_read, "sheets": sheets,
        "columns": list(EXPECTED_COLUMNS), "null_counts": column_nulls,
        "duplicate_rows": rows_read - len(fingerprints),
        "data_types": {column: "source workbook values" for column in EXPECTED_COLUMNS},
        "quantity_min": min(quantity_values) if quantity_values else None,
        "quantity_max": max(quantity_values) if quantity_values else None,
        "unit_price_min": min(price_values) if price_values else None,
        "unit_price_max": max(price_values) if price_values else None,
        "invoice_date_min": min(invoice_dates).isoformat() if invoice_dates else None,
        "invoice_date_max": max(invoice_dates).isoformat() if invoice_dates else None,
        "cancelled_rows": cancellations, "negative_quantity_rows": negative_quantities,
    }


def ingest_workbook(input_path: str | Path, database_path: str | Path, chunk_size: int = 10_000) -> dict[str, int]:
    """Stream, validate, and idempotently import workbook rows into SQLite."""
    connection = connect_database(database_path)
    stats = {"rows_read": 0, "valid_rows": 0, "invalid_rows": 0, "inserted_rows": 0, "duplicate_rows": 0}
    batch: list[tuple[str, int, dict[str, Any]]] = []

    def write_batch(rows: list[tuple[str, int, dict[str, Any]]]) -> None:
        if not rows:
            return
        # Materialize only this bounded batch as a Pandas frame; the workbook is never loaded wholesale.
        pd.DataFrame([raw for _, _, raw in rows], columns=EXPECTED_COLUMNS)
        cleaned = [_clean_row(str(input_path), sheet, row_number, raw) for sheet, row_number, raw in rows]
        before = connection.total_changes
        connection.executemany(INSERT_SQL, cleaned)
        connection.commit()
        inserted = connection.total_changes - before
        stats["inserted_rows"] += inserted
        stats["duplicate_rows"] += len(cleaned) - inserted
        stats["valid_rows"] += sum(row[17] == "valid" for row in cleaned)
        stats["invalid_rows"] += sum(row[17] == "invalid" for row in cleaned)

    try:
        for row in iter_workbook_rows(input_path):
            batch.append(row)
            stats["rows_read"] += 1
            if len(batch) >= chunk_size:
                write_batch(batch)
                batch = []
        write_batch(batch)
        stats.update({f"stored_{key}": value for key, value in get_transaction_counts(connection).items()})
        return stats
    finally:
        connection.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Path to the UCI .xlsx workbook")
    parser.add_argument("--database", type=Path, default=Path("data/database/retail.db"))
    parser.add_argument("--chunk-size", type=int, default=10_000)
    parser.add_argument("--profile-only", action="store_true")
    parser.add_argument("--profile-output", type=Path, default=Path("data/processed/dataset_profile.json"))
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    profile = profile_workbook(args.input)
    args.profile_output.parent.mkdir(parents=True, exist_ok=True)
    args.profile_output.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    print(json.dumps(profile, indent=2))
    if not args.profile_only:
        print(json.dumps(ingest_workbook(args.input, args.database, args.chunk_size), indent=2))


if __name__ == "__main__":
    main()

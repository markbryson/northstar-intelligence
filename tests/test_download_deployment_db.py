import io
import sqlite3
from pathlib import Path

import pytest

from scripts import download_deployment_db as downloader


DEPLOYMENT_COLUMNS = (
    "invoice_no TEXT NOT NULL",
    "stock_code TEXT NOT NULL",
    "description TEXT",
    "quantity INTEGER",
    "invoice_date TEXT",
    "customer_id TEXT",
    "country TEXT",
    "is_cancelled INTEGER NOT NULL",
    "is_return INTEGER NOT NULL",
    "gross_sales REAL NOT NULL",
    "return_amount REAL NOT NULL",
    "net_sales REAL NOT NULL",
    "validation_status TEXT NOT NULL",
)


def _create_valid_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE transactions (" + ", ".join(DEPLOYMENT_COLUMNS) + ")"
        )
        connection.execute(
            "INSERT INTO transactions VALUES "
            "('1001', 'A', 'Alpha', 1, '2010-01-01', '1', 'United Kingdom', "
            "0, 0, 10.0, 0.0, 10.0, 'valid')"
        )
        connection.commit()
    finally:
        connection.close()


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = io.BytesIO(payload)

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        self.payload.close()

    def read(self, size: int) -> bytes:
        return self.payload.read(size)


def test_existing_valid_database_is_reused(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "nested" / "retail_deployment.db"
    output.parent.mkdir()
    _create_valid_database(output)

    def fail_download(*args, **kwargs):
        raise AssertionError("valid database should not be downloaded")

    monkeypatch.setattr(downloader, "_download_to_temp", fail_download)

    assert downloader.ensure_deployment_database("https://example.test", output) is False


def test_download_is_streamed_validated_and_atomically_installed(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "source.db"
    output = tmp_path / "nested" / "retail_deployment.db"
    _create_valid_database(source)
    payload = source.read_bytes()
    monkeypatch.setattr(
        downloader,
        "urlopen",
        lambda *args, **kwargs: _FakeResponse(payload),
    )

    assert downloader.ensure_deployment_database("https://example.test", output) is True
    downloader.validate_database(output)
    assert output.exists()
    assert not list(output.parent.glob(f".{output.name}.*.tmp"))


def test_invalid_download_is_rejected_and_removed(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "retail_deployment.db"
    monkeypatch.setattr(
        downloader,
        "urlopen",
        lambda *args, **kwargs: _FakeResponse(b"not sqlite"),
    )

    with pytest.raises(downloader.DeploymentDatabaseError, match="integrity|SQLite"):
        downloader.ensure_deployment_database("https://example.test", output)

    assert not output.exists()
    assert not list(tmp_path.glob(f".{output.name}.*.tmp"))

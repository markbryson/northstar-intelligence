import sqlite3

import pytest

from backend.database import connect_database


def test_read_only_connection_rejects_writes(tmp_path) -> None:
    database_path = tmp_path / "retail.db"
    connection = connect_database(database_path)
    connection.close()

    read_only = connect_database(database_path, initialize_schema=False, read_only=True)
    try:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            read_only.execute(
                "CREATE TABLE should_not_exist (value TEXT)"
            )
    finally:
        read_only.close()


def test_read_only_connection_does_not_create_missing_database(tmp_path) -> None:
    database_path = tmp_path / "missing.db"

    with pytest.raises(FileNotFoundError):
        connect_database(database_path, initialize_schema=False, read_only=True)

    assert not database_path.exists()


def test_read_write_connection_remains_compatible(tmp_path) -> None:
    database_path = tmp_path / "retail.db"

    connection = connect_database(database_path)
    try:
        connection.execute("SELECT 1")
    finally:
        connection.close()

    assert database_path.exists()


def test_read_only_connection_cannot_initialize_schema(tmp_path) -> None:
    with pytest.raises(ValueError, match="cannot initialize"):
        connect_database(tmp_path / "retail.db", read_only=True)

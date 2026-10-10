"""Download and validate the read-only SQLite database used for deployment."""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen


DEFAULT_URL = (
    "https://github.com/markbryson/northstar-intelligence/releases/"
    "download/v1.0.0-data/retail_deployment.db"
)
DEFAULT_OUTPUT = Path("data/database/retail_deployment.db")
DOWNLOAD_CHUNK_SIZE = 1024 * 1024
EXPECTED_COLUMNS = {
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
}


class DeploymentDatabaseError(RuntimeError):
    """Raised when the deployment database cannot be validated."""


def validate_database(path: Path) -> None:
    """Verify that an existing file is a readable retail analytics database."""
    if not path.is_file() or path.stat().st_size == 0:
        raise DeploymentDatabaseError("database file is missing or empty")

    try:
        uri = f"{path.resolve().as_uri()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        try:
            quick_check = connection.execute("PRAGMA quick_check").fetchone()
            if quick_check is None or quick_check[0] != "ok":
                raise DeploymentDatabaseError("SQLite integrity check failed")

            table = connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'transactions'"
            ).fetchone()
            if table is None:
                raise DeploymentDatabaseError(
                    "required transactions table is missing"
                )

            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(transactions)")
            }
            missing_columns = EXPECTED_COLUMNS - columns
            if missing_columns:
                missing = ", ".join(sorted(missing_columns))
                raise DeploymentDatabaseError(
                    f"required transactions columns are missing: {missing}"
                )

            connection.execute(
                "SELECT validation_status FROM transactions LIMIT 1"
            ).fetchone()
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise DeploymentDatabaseError(
            "file is not a readable SQLite analytics database"
        ) from error


def _download_to_temp(url: str, output: Path) -> Path:
    """Stream a download into a temporary sibling file."""
    temporary_handle = tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
        delete=False,
    )
    temporary = Path(temporary_handle.name)
    try:
        request = Request(url, headers={"User-Agent": "northstar-intelligence"})
        with temporary_handle, urlopen(request, timeout=120) as response:
            while chunk := response.read(DOWNLOAD_CHUNK_SIZE):
                temporary_handle.write(chunk)
        return temporary
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def ensure_deployment_database(
    url: str = DEFAULT_URL,
    output_path: str | Path = DEFAULT_OUTPUT,
) -> bool:
    """Ensure a valid deployment database exists; return True if downloaded."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if output.exists():
        try:
            validate_database(output)
            return False
        except DeploymentDatabaseError:
            pass

    temporary: Path | None = None
    try:
        temporary = _download_to_temp(url, output)
        validate_database(temporary)
        os.replace(temporary, output)
        temporary = None
        return True
    except DeploymentDatabaseError:
        raise
    except Exception as error:
        raise DeploymentDatabaseError(f"download failed: {error}") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        downloaded = ensure_deployment_database(args.url, args.output)
    except DeploymentDatabaseError as error:
        print(f"Deployment database error: {error}", file=sys.stderr)
        return 1

    if downloaded:
        print(f"Downloaded and validated deployment database: {args.output}")
    else:
        print(f"Using existing validated deployment database: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

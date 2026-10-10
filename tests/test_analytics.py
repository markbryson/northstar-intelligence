from collections.abc import Iterator

from fastapi.testclient import TestClient

from backend.api.analytics import get_db
from backend.database import connect_database
from backend.main import app


def _seed_fixture(connection) -> None:
    rows = [
        ("fixture", "Test", 2, "hash-1", "1001", "A", "Alpha", 2, 10.0, "2010-01-01T10:00:00", "1", "United Kingdom", 0, 0, 20.0, 0.0, 20.0, "valid"),
        ("fixture", "Test", 3, "hash-2", "1001", "B", "Beta", 1, 5.0, "2010-01-01T10:00:00", "1", "United Kingdom", 0, 0, 5.0, 0.0, 5.0, "valid"),
        ("fixture", "Test", 4, "hash-3", "1002", "A", "Alpha", 1, 10.0, "2010-01-02T10:00:00", "1", "United Kingdom", 0, 0, 10.0, 0.0, 10.0, "valid"),
        ("fixture", "Test", 5, "hash-4", "C1003", "A", "Alpha", -1, 10.0, "2010-01-02T11:00:00", "2", "Kenya", 1, 1, 0.0, 10.0, -10.0, "valid"),
        ("fixture", "Test", 6, "hash-5", "1004", "B", "Beta", 1, 4.0, "2010-01-03T12:00:00", None, "United Kingdom", 0, 0, 4.0, 0.0, 4.0, "valid"),
        ("fixture", "Test", 7, "hash-6", "1005", "C", "Invalid", 1, 0.0, "2010-01-03T12:00:00", "3", "United Kingdom", 0, 0, 0.0, 0.0, 0.0, "invalid"),
    ]
    connection.executemany(
        """
        INSERT INTO transactions (
            source_file, source_sheet, source_row, record_hash, invoice_no, stock_code,
            description, quantity, unit_price, invoice_date, customer_id, country,
            is_cancelled, is_return, gross_sales, return_amount, net_sales, validation_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    connection.commit()


def test_analytics_endpoints_use_valid_rows_and_order_level_aov() -> None:
    connection = connect_database(":memory:")
    _seed_fixture(connection)

    def override_db() -> Iterator:
        yield connection

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        overview = client.get("/api/analytics/overview").json()
        assert overview == {
            "gross_sales": 39.0,
            "returns": 10.0,
            "net_sales": 29.0,
            "transaction_count": 5,
            "unique_customers": 2,
            "order_count": 3,
            "average_order_value": 13.0,
        }

        trends = client.get("/api/analytics/sales-trends?granularity=day").json()
        assert [row["net_sales"] for row in trends] == [25.0, 0.0, 4.0]
        products = client.get("/api/analytics/top-products?limit=2").json()
        assert products[0]["stock_code"] == "A"
        assert products[0]["net_revenue"] == 20.0
        assert products[0]["units_sold"] == 3
        assert products[0]["returned_units"] == 1

        customers = client.get("/api/analytics/customers").json()
        assert customers["customer_count"] == 2
        assert customers["repeat_customer_count"] == 1
        assert customers["repeat_customer_rate"] == 0.5
        assert customers["items"][0]["customer_id"] == "1"
        assert customers["items"][0]["order_count"] == 2

        countries = client.get("/api/analytics/countries").json()
        assert countries[0]["country"] == "United Kingdom"
        assert countries[0]["net_revenue"] == 39.0

        returns = client.get("/api/analytics/returns").json()
        assert returns == {
            "returned_quantity": 1,
            "return_value": 10.0,
            "returned_transaction_rows": 1,
            "cancellation_count": 1,
            "cancellation_value": 10.0,
            "transaction_count": 5,
            "return_rate": 0.2,
        }

        filters = client.get("/api/analytics/filters").json()
        assert filters == {
            "min_date": "2010-01-01T10:00:00",
            "max_date": "2010-01-03T12:00:00",
            "countries": ["Kenya", "United Kingdom"],
        }
    finally:
        app.dependency_overrides.clear()
        connection.close()


def test_analytics_filters_validate_inputs_and_apply_country_date() -> None:
    connection = connect_database(":memory:")
    _seed_fixture(connection)

    def override_db() -> Iterator:
        yield connection

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        response = client.get("/api/analytics/overview?start_date=2010-01-03&end_date=2010-01-01")
        assert response.status_code == 422
        response = client.get("/api/analytics/sales-trends?granularity=week")
        assert response.status_code == 422
        overview = client.get("/api/analytics/overview?country=Kenya&start_date=2010-01-02&end_date=2010-01-02").json()
        assert overview["net_sales"] == -10.0
        assert overview["transaction_count"] == 1
    finally:
        app.dependency_overrides.clear()
        connection.close()

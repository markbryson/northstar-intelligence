"""Efficient, parameterized SQLite analytics queries."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any


@dataclass(frozen=True)
class AnalyticsFilters:
    start_date: date | None = None
    end_date: date | None = None
    country: str | None = None

    def where_clause(self, alias: str = "t") -> tuple[str, dict[str, Any]]:
        clauses = [f"{alias}.validation_status = 'valid'"]
        params: dict[str, Any] = {}
        if self.start_date:
            clauses.append(f"{alias}.invoice_date >= :start_date")
            params["start_date"] = self.start_date.isoformat()
        if self.end_date:
            clauses.append(f"{alias}.invoice_date < :end_date_exclusive")
            params["end_date_exclusive"] = (self.end_date + timedelta(days=1)).isoformat()
        if self.country:
            clauses.append(f"{alias}.country = :country")
            params["country"] = self.country
        return " AND ".join(clauses), params


def _rows(connection: sqlite3.Connection, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(query, params).fetchall()]


def _one(connection: sqlite3.Connection, query: str, params: dict[str, Any]) -> dict[str, Any]:
    row = connection.execute(query, params).fetchone()
    return dict(row) if row else {}


def overview(connection: sqlite3.Connection, filters: AnalyticsFilters) -> dict[str, Any]:
    where, params = filters.where_clause()
    return _one(
        connection,
        f"""
        WITH filtered AS (
            SELECT t.* FROM transactions t WHERE {where}
        ), order_totals AS (
            SELECT invoice_no, SUM(net_sales) AS order_net_sales
            FROM filtered
            WHERE is_cancelled = 0 AND gross_sales > 0
            GROUP BY invoice_no
        )
        SELECT
            ROUND(COALESCE((SELECT SUM(gross_sales) FROM filtered), 0.0), 2) AS gross_sales,
            ROUND(COALESCE((SELECT SUM(return_amount) FROM filtered), 0.0), 2) AS returns,
            ROUND(COALESCE((SELECT SUM(net_sales) FROM filtered), 0.0), 2) AS net_sales,
            (SELECT COUNT(*) FROM filtered) AS transaction_count,
            (SELECT COUNT(DISTINCT customer_id) FROM filtered WHERE customer_id IS NOT NULL) AS unique_customers,
            (SELECT COUNT(*) FROM order_totals) AS order_count,
            ROUND(COALESCE((SELECT SUM(order_net_sales) / NULLIF(COUNT(*), 0) FROM order_totals), 0.0), 2) AS average_order_value
        """,
        params,
    )


def sales_trends(connection: sqlite3.Connection, filters: AnalyticsFilters, granularity: str) -> list[dict[str, Any]]:
    group_expression = {
        "day": "substr(t.invoice_date, 1, 10)",
        "month": "substr(t.invoice_date, 1, 7)",
        "year": "substr(t.invoice_date, 1, 4)",
    }[granularity]
    where, params = filters.where_clause("t")
    return _rows(
        connection,
        f"""
        SELECT {group_expression} AS period,
               ROUND(SUM(t.gross_sales), 2) AS gross_sales,
               ROUND(SUM(t.return_amount), 2) AS returns,
               ROUND(SUM(t.net_sales), 2) AS net_sales,
               COUNT(*) AS transaction_count,
               COUNT(DISTINCT CASE WHEN t.is_cancelled = 0 AND t.gross_sales > 0 THEN t.invoice_no END) AS order_count
        FROM transactions t
        WHERE {where}
        GROUP BY period
        ORDER BY period
        """,
        params,
    )


def top_products(connection: sqlite3.Connection, filters: AnalyticsFilters, limit: int, offset: int) -> list[dict[str, Any]]:
    where, params = filters.where_clause("t")
    params.update({"limit": limit, "offset": offset})
    return _rows(
        connection,
        f"""
        SELECT t.stock_code,
               MAX(t.description) AS description,
               ROUND(SUM(t.net_sales), 2) AS net_revenue,
               COALESCE(SUM(CASE WHEN t.quantity > 0 AND t.is_cancelled = 0 THEN t.quantity ELSE 0 END), 0) AS units_sold,
               COALESCE(SUM(CASE WHEN t.is_return = 1 AND t.quantity < 0 THEN ABS(t.quantity) ELSE 0 END), 0) AS returned_units,
               COUNT(*) AS transaction_count
        FROM transactions t
        WHERE {where}
        GROUP BY t.stock_code
        ORDER BY net_revenue DESC, t.stock_code
        LIMIT :limit OFFSET :offset
        """,
        params,
    )


def customers(connection: sqlite3.Connection, filters: AnalyticsFilters, limit: int, offset: int) -> dict[str, Any]:
    where, params = filters.where_clause("t")
    params.update({"limit": limit, "offset": offset})
    summary = _one(
        connection,
        f"""
        WITH customer_orders AS (
            SELECT customer_id,
                   COUNT(DISTINCT CASE WHEN is_cancelled = 0 AND gross_sales > 0 THEN invoice_no END) AS order_count,
                   SUM(net_sales) AS net_revenue
            FROM transactions t
            WHERE {where} AND customer_id IS NOT NULL
            GROUP BY customer_id
        )
        SELECT COUNT(*) AS customer_count,
               COALESCE(SUM(order_count >= 2), 0) AS repeat_customer_count,
               COALESCE(SUM(net_revenue), 0.0) AS total_customer_revenue
        FROM customer_orders
        """,
        params,
    )
    items = _rows(
        connection,
        f"""
        SELECT t.customer_id,
               COUNT(DISTINCT CASE WHEN t.is_cancelled = 0 AND t.gross_sales > 0 THEN t.invoice_no END) AS order_count,
               COUNT(*) AS transaction_count,
               ROUND(SUM(t.net_sales), 2) AS net_revenue,
               (COUNT(DISTINCT CASE WHEN t.is_cancelled = 0 AND t.gross_sales > 0 THEN t.invoice_no END) >= 2) AS is_repeat_customer
        FROM transactions t
        WHERE {where} AND t.customer_id IS NOT NULL
        GROUP BY t.customer_id
        ORDER BY net_revenue DESC, t.customer_id
        LIMIT :limit OFFSET :offset
        """,
        params,
    )
    customer_count = int(summary.get("customer_count", 0))
    repeat_count = int(summary.get("repeat_customer_count", 0))
    return {
        "customer_count": customer_count,
        "repeat_customer_count": repeat_count,
        "repeat_customer_rate": repeat_count / customer_count if customer_count else 0.0,
        "total_customer_revenue": round(float(summary.get("total_customer_revenue", 0.0)), 2),
        "items": items,
        "limit": limit,
        "offset": offset,
    }


def countries(connection: sqlite3.Connection, filters: AnalyticsFilters, limit: int, offset: int) -> list[dict[str, Any]]:
    where, params = filters.where_clause("t")
    params.update({"limit": limit, "offset": offset})
    return _rows(
        connection,
        f"""
        SELECT t.country,
               ROUND(SUM(t.gross_sales), 2) AS gross_sales,
               ROUND(SUM(t.return_amount), 2) AS returns,
               ROUND(SUM(t.net_sales), 2) AS net_revenue,
               COUNT(*) AS transaction_count,
               COUNT(DISTINCT CASE WHEN t.is_cancelled = 0 AND t.gross_sales > 0 THEN t.invoice_no END) AS order_count,
               COUNT(DISTINCT t.customer_id) AS unique_customers
        FROM transactions t
        WHERE {where}
        GROUP BY t.country
        ORDER BY net_revenue DESC, t.country
        LIMIT :limit OFFSET :offset
        """,
        params,
    )


def returns(connection: sqlite3.Connection, filters: AnalyticsFilters) -> dict[str, Any]:
    where, params = filters.where_clause("t")
    result = _one(
        connection,
        f"""
        SELECT
            COALESCE(SUM(CASE WHEN t.is_return = 1 AND t.quantity < 0 THEN ABS(t.quantity) ELSE 0 END), 0) AS returned_quantity,
            ROUND(COALESCE(SUM(t.return_amount), 0.0), 2) AS return_value,
            SUM(CASE WHEN t.is_return = 1 THEN 1 ELSE 0 END) AS returned_transaction_rows,
            SUM(CASE WHEN t.is_cancelled = 1 THEN 1 ELSE 0 END) AS cancellation_count,
            ROUND(COALESCE(SUM(CASE WHEN t.is_cancelled = 1 THEN t.return_amount ELSE 0 END), 0.0), 2) AS cancellation_value,
            COUNT(*) AS transaction_count
        FROM transactions t
        WHERE {where}
        """,
        params,
    )
    transaction_count = int(result.get("transaction_count", 0))
    returned_rows = int(result.get("returned_transaction_rows", 0) or 0)
    result["returned_transaction_rows"] = returned_rows
    result["cancellation_count"] = int(result.get("cancellation_count", 0) or 0)
    result["returned_quantity"] = int(result.get("returned_quantity", 0) or 0)
    result["transaction_count"] = transaction_count
    result["return_rate"] = returned_rows / transaction_count if transaction_count else 0.0
    return result


def filter_options(connection: sqlite3.Connection, filters: AnalyticsFilters) -> dict[str, Any]:
    where, params = filters.where_clause("t")
    dates = _one(connection, f"SELECT MIN(t.invoice_date) AS min_date, MAX(t.invoice_date) AS max_date FROM transactions t WHERE {where}", params)
    countries_list = [row["country"] for row in connection.execute(f"SELECT DISTINCT t.country FROM transactions t WHERE {where} AND t.country IS NOT NULL ORDER BY t.country", params)]
    return {"min_date": dates.get("min_date"), "max_date": dates.get("max_date"), "countries": countries_list}

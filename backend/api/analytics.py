"""FastAPI routes for retail analytics."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Annotated, Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config import get_settings
from backend.database import connect_database
from backend.models.analytics import (
    CustomerAnalyticsResponse, CountryPerformance, FilterOptionsResponse,
    OverviewResponse, ProductPerformance, ReturnAnalyticsResponse, SalesTrendPoint,
)
from backend.services.analytics import AnalyticsFilters, countries, customers, filter_options, overview, returns, sales_trends, top_products


router = APIRouter(prefix="/api/analytics", tags=["analytics"])
settings = get_settings()
DATABASE_ERROR_DETAIL = {
    "code": "database_unavailable",
    "message": "Analytics database is unavailable",
}


def _database_unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail=DATABASE_ERROR_DETAIL)


def get_db() -> sqlite3.Connection:
    try:
        connection = connect_database(
            settings.database_path,
            initialize_schema=False,
            read_only=settings.database_read_only,
        )
    except (OSError, sqlite3.Error) as error:
        raise _database_unavailable() from error
    try:
        yield connection
    finally:
        connection.close()


def get_filters(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    country: str | None = Query(default=None, min_length=1),
) -> AnalyticsFilters:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date")
    return AnalyticsFilters(start_date=start_date, end_date=end_date, country=country)


Filters = Annotated[AnalyticsFilters, Depends(get_filters)]
Database = Annotated[sqlite3.Connection, Depends(get_db)]


def _run(function: Callable[..., Any], connection: sqlite3.Connection, *args: Any) -> Any:
    try:
        return function(connection, *args)
    except (OSError, sqlite3.Error) as error:
        raise _database_unavailable() from error


@router.get("/overview", response_model=OverviewResponse)
def analytics_overview(filters: Filters, connection: Database) -> Any:
    return _run(overview, connection, filters)


@router.get("/sales-trends", response_model=list[SalesTrendPoint])
def analytics_sales_trends(
    filters: Filters,
    connection: Database,
    granularity: str = Query(default="month"),
) -> Any:
    if granularity not in {"day", "month", "year"}:
        raise HTTPException(status_code=422, detail="granularity must be one of: day, month, year")
    return _run(sales_trends, connection, filters, granularity)


def _pagination(limit: int, offset: int) -> tuple[int, int]:
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 500")
    if offset < 0:
        raise HTTPException(status_code=422, detail="offset must be non-negative")
    return limit, offset


@router.get("/top-products", response_model=list[ProductPerformance])
def analytics_top_products(
    filters: Filters,
    connection: Database,
    limit: int = Query(default=20),
    offset: int = Query(default=0),
) -> Any:
    limit, offset = _pagination(limit, offset)
    return _run(top_products, connection, filters, limit, offset)


@router.get("/customers", response_model=CustomerAnalyticsResponse)
def analytics_customers(
    filters: Filters,
    connection: Database,
    limit: int = Query(default=20),
    offset: int = Query(default=0),
) -> Any:
    limit, offset = _pagination(limit, offset)
    return _run(customers, connection, filters, limit, offset)


@router.get("/countries", response_model=list[CountryPerformance])
def analytics_countries(
    filters: Filters,
    connection: Database,
    limit: int = Query(default=100),
    offset: int = Query(default=0),
) -> Any:
    limit, offset = _pagination(limit, offset)
    return _run(countries, connection, filters, limit, offset)


@router.get("/returns", response_model=ReturnAnalyticsResponse)
def analytics_returns(filters: Filters, connection: Database) -> Any:
    return _run(returns, connection, filters)


@router.get("/filters", response_model=FilterOptionsResponse)
def analytics_filters(filters: Filters, connection: Database) -> Any:
    return _run(filter_options, connection, filters)

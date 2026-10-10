"""Pydantic response models for analytics endpoints."""

from pydantic import BaseModel, Field


class OverviewResponse(BaseModel):
    gross_sales: float
    returns: float
    net_sales: float
    transaction_count: int
    unique_customers: int
    order_count: int
    average_order_value: float


class SalesTrendPoint(BaseModel):
    period: str
    gross_sales: float
    returns: float
    net_sales: float
    transaction_count: int
    order_count: int


class ProductPerformance(BaseModel):
    stock_code: str
    description: str | None
    net_revenue: float
    units_sold: int
    returned_units: int
    transaction_count: int


class CustomerPerformance(BaseModel):
    customer_id: str
    order_count: int
    transaction_count: int
    net_revenue: float
    is_repeat_customer: bool


class CustomerAnalyticsResponse(BaseModel):
    customer_count: int
    repeat_customer_count: int
    repeat_customer_rate: float
    total_customer_revenue: float
    items: list[CustomerPerformance]
    limit: int
    offset: int


class CountryPerformance(BaseModel):
    country: str
    gross_sales: float
    returns: float
    net_revenue: float
    transaction_count: int
    order_count: int
    unique_customers: int


class ReturnAnalyticsResponse(BaseModel):
    returned_quantity: int
    return_value: float
    returned_transaction_rows: int
    cancellation_count: int
    cancellation_value: float
    transaction_count: int
    return_rate: float = Field(
        description="Transaction-row return rate: returned or cancelled transaction rows divided by valid transaction rows"
    )


class FilterOptionsResponse(BaseModel):
    min_date: str | None
    max_date: str | None
    countries: list[str]

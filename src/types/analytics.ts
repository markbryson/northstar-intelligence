export type Granularity = "day" | "month" | "year";

export interface AnalyticsFilters {
  startDate?: string;
  endDate?: string;
  country?: string;
}

export interface Overview {
  gross_sales: number;
  returns: number;
  net_sales: number;
  transaction_count: number;
  unique_customers: number;
  order_count: number;
  average_order_value: number;
}

export interface SalesTrend {
  period: string;
  gross_sales: number;
  returns: number;
  net_sales: number;
  transaction_count: number;
  order_count: number;
}

export interface ProductPerformance {
  stock_code: string;
  description: string | null;
  net_revenue: number;
  units_sold: number;
  returned_units: number;
  transaction_count: number;
}

export interface CustomerPerformance {
  customer_id: string;
  order_count: number;
  transaction_count: number;
  net_revenue: number;
  is_repeat_customer: boolean;
}

export interface CustomerAnalytics {
  customer_count: number;
  repeat_customer_count: number;
  repeat_customer_rate: number;
  total_customer_revenue: number;
  items: CustomerPerformance[];
  limit: number;
  offset: number;
}

export interface CountryPerformance {
  country: string;
  gross_sales: number;
  returns: number;
  net_revenue: number;
  transaction_count: number;
  order_count: number;
  unique_customers: number;
}

export interface ReturnsAnalytics {
  returned_quantity: number;
  return_value: number;
  returned_transaction_rows: number;
  cancellation_count: number;
  cancellation_value: number;
  transaction_count: number;
  return_rate: number;
}

export interface FilterOptions {
  min_date: string | null;
  max_date: string | null;
  countries: string[];
}

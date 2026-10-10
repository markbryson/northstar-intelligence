import type {
  AnalyticsFilters,
  CountryPerformance,
  CustomerAnalytics,
  FilterOptions,
  Granularity,
  Overview,
  ProductPerformance,
  ReturnsAnalytics,
  SalesTrend,
} from "../types/analytics";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

function queryString(filters: AnalyticsFilters = {}, extras: Record<string, string | number | undefined> = {}) {
  const params = new URLSearchParams();
  if (filters.startDate) params.set("start_date", filters.startDate);
  if (filters.endDate) params.set("end_date", filters.endDate);
  if (filters.country) params.set("country", filters.country);
  Object.entries(extras).forEach(([key, value]) => {
    if (value !== undefined) params.set(key, String(value));
  });
  const value = params.toString();
  return value ? `?${value}` : "";
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail ?? detail;
    } catch {
      // Keep the useful status message when the API returns non-JSON content.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  overview: (filters?: AnalyticsFilters) => request<Overview>(`/api/analytics/overview${queryString(filters)}`),
  salesTrends: (filters: AnalyticsFilters, granularity: Granularity) =>
    request<SalesTrend[]>(`/api/analytics/sales-trends${queryString(filters, { granularity })}`),
  topProducts: (filters: AnalyticsFilters, limit = 50, offset = 0) =>
    request<ProductPerformance[]>(`/api/analytics/top-products${queryString(filters, { limit, offset })}`),
  customers: (filters: AnalyticsFilters, limit = 50, offset = 0) =>
    request<CustomerAnalytics>(`/api/analytics/customers${queryString(filters, { limit, offset })}`),
  countries: (filters: AnalyticsFilters, limit = 100, offset = 0) =>
    request<CountryPerformance[]>(`/api/analytics/countries${queryString(filters, { limit, offset })}`),
  returns: (filters?: AnalyticsFilters) => request<ReturnsAnalytics>(`/api/analytics/returns${queryString(filters)}`),
  filterOptions: () => request<FilterOptions>("/api/analytics/filters"),
};


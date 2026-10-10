import { useState } from "react";
import { BarChart3, CalendarDays } from "lucide-react";
import { api } from "../api/client";
import { useDashboard } from "../context/DashboardContext";
import { useApi } from "../hooks/useAnalytics";
import type { Granularity } from "../types/analytics";
import { Panel } from "../components/ui/Panel";
import { ErrorState, LoadingState } from "../components/ui/States";
import { SalesTrendChart } from "../components/charts/SalesTrendChart";
import { formatCurrency, formatDate, number } from "../utils/format";

export function SalesPage() {
  const { filters } = useDashboard();
  const [granularity, setGranularity] = useState<Granularity>("month");
  const overview = useApi(() => api.overview(filters), [filters.startDate, filters.endDate, filters.country]);
  const trends = useApi(() => api.salesTrends(filters, granularity), [filters.startDate, filters.endDate, filters.country, granularity]);
  const totals = overview.data ? { net: overview.data.net_sales, gross: overview.data.gross_sales, orders: overview.data.order_count, rows: overview.data.transaction_count } : undefined;
  const dateDescription = filters.startDate || filters.endDate
    ? `${filters.startDate ? formatDate(filters.startDate) : "Earliest"} - ${filters.endDate ? formatDate(filters.endDate) : "Latest"}`
    : "Dec 2009 - Dec 2011";
  return <div className="page-stack"><div className="page-intro"><div><p className="eyebrow">Commercial pulse</p><h2>Sales, in context.</h2><p>Explore revenue cadence across the archive at the level that matters to your question.</p></div><div className="date-context"><CalendarDays size={15} /> {dateDescription}</div></div><div className="stat-strip"><div><span>Net sales in scope</span><strong>{formatCurrency(totals?.net ?? 0)}</strong></div><div><span>Gross sales</span><strong>{formatCurrency(totals?.gross ?? 0)}</strong></div><div><span>Orders represented</span><strong>{number.format(totals?.orders ?? 0)}</strong></div><div><span>Transaction rows</span><strong>{number.format(totals?.rows ?? 0)}</strong></div></div><Panel eyebrow="Trend explorer" title="Revenue over time" action={<div className="segmented-control">{(["day", "month", "year"] as Granularity[]).map((item) => <button key={item} className={granularity === item ? "selected" : ""} onClick={() => setGranularity(item)}>{item}</button>)}</div>}>{overview.error || trends.error ? <ErrorState message={overview.error ?? trends.error ?? "Unable to load sales"} onRetry={overview.error ? overview.retry : trends.retry} /> : overview.isLoading || trends.isLoading || !trends.data ? <LoadingState label="Loading sales trend" /> : <SalesTrendChart data={trends.data} />}</Panel><div className="grid-two-thirds"><Panel eyebrow="How to read this" title="Revenue definitions"><div className="definition-list"><div><span className="definition-number">01</span><p><strong>Gross sales</strong>Positive non-cancelled line revenue before returns.</p></div><div><span className="definition-number">02</span><p><strong>Returns</strong>Returned and cancelled transaction value.</p></div><div><span className="definition-number">03</span><p><strong>Net sales</strong>Gross sales less return value, calculated from the API.</p></div></div></Panel><Panel eyebrow="Dataset context" title="Historical, not live"><div className="context-callout"><BarChart3 size={20} /><div><strong>Online Retail II archive</strong><p>These are historical transactions from December 2009 through December 2011. They should not be interpreted as current trading activity.</p></div></div></Panel></div></div>;
}

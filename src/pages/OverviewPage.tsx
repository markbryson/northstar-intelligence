import { ArrowUpRight, CircleDollarSign, ClipboardList, Globe2, ReceiptText, UsersRound } from "lucide-react";
import { useApi } from "../hooks/useAnalytics";
import { api } from "../api/client";
import { useDashboard } from "../context/DashboardContext";
import { MetricCard } from "../components/ui/MetricCard";
import { Panel } from "../components/ui/Panel";
import { ErrorState, LoadingState } from "../components/ui/States";
import { SalesTrendChart } from "../components/charts/SalesTrendChart";
import { ProductTable } from "../components/tables/ProductTable";
import { CountryTable } from "../components/tables/CountryTable";
import { formatCurrency, number, percent } from "../utils/format";
import { Link } from "react-router-dom";

export function OverviewPage() {
  const { filters } = useDashboard();
  const overview = useApi(() => api.overview(filters), [filters.startDate, filters.endDate, filters.country]);
  const trends = useApi(() => api.salesTrends(filters, "month"), [filters.startDate, filters.endDate, filters.country]);
  const products = useApi(() => api.topProducts(filters, 5), [filters.startDate, filters.endDate, filters.country]);
  const countries = useApi(() => api.countries(filters, 5), [filters.startDate, filters.endDate, filters.country]);
  const loading = overview.isLoading || trends.isLoading;
  if (overview.error) return <ErrorState message={overview.error} onRetry={overview.retry} />;
  return <div className="page-stack">
    <div className="page-intro"><div><p className="eyebrow">Executive brief</p><h2>Know where the business is moving.</h2><p>Decision-ready signals from the historical retail archive, refreshed from the connected API.</p></div><span className="last-updated"><span className="status-pulse" /> API connected</span></div>
    {loading || !overview.data ? <LoadingState label="Assembling executive view" /> : <>
      <div className="metric-grid"><MetricCard label="Net sales" value={formatCurrency(overview.data.net_sales)} detail="After returns & cancellations" icon={CircleDollarSign} accent="cyan" /><MetricCard label="Gross sales" value={formatCurrency(overview.data.gross_sales)} detail="Valid transaction rows" icon={ReceiptText} accent="blue" /><MetricCard label="Orders" value={number.format(overview.data.order_count)} detail={`${number.format(overview.data.transaction_count)} line items`} icon={ClipboardList} accent="amber" /><MetricCard label="Customers" value={number.format(overview.data.unique_customers)} detail="Known customer IDs" icon={UsersRound} accent="rose" /><MetricCard label="Average order" value={formatCurrency(overview.data.average_order_value)} detail="Order-level net AOV" icon={CircleDollarSign} accent="cyan" /> </div>
      <div className="grid-two-thirds"><Panel eyebrow="Revenue performance" title="Sales trend" action={<span className="panel-meta">Monthly · GBP</span>}>{trends.error ? <ErrorState message={trends.error} /> : trends.isLoading || !trends.data ? <LoadingState /> : <SalesTrendChart data={trends.data} />}</Panel><Panel eyebrow="At a glance" title="Returns signal" action={<span className="trend-chip warm">{overview.data.gross_sales === 0 ? "N/A" : `${percent(overview.data.returns / overview.data.gross_sales)} of gross`}</span>}><div className="insight-card"><div className="insight-orb">↘</div><div><strong>{formatCurrency(overview.data.returns)}</strong><p>total value returned across the archive</p></div></div><div className="insight-divider" /><div className="insight-row"><span>Net retention</span><strong>{overview.data.gross_sales === 0 ? "N/A" : percent(overview.data.net_sales / overview.data.gross_sales)}</strong></div><div className="insight-row"><span>Known customer coverage</span><strong>{overview.data.transaction_count === 0 ? "N/A" : percent(overview.data.unique_customers / overview.data.transaction_count)}</strong></div><div className="text-link"><span>See returns analytics</span><ArrowUpRight size={15} /></div></Panel></div>
      <div className="grid-two-thirds"><Panel eyebrow="Product mix" title="Top products" action={<Link className="panel-link" to="/products">View all <ArrowUpRight size={14} /></Link>}>{products.error ? <ErrorState message={products.error} onRetry={products.retry} /> : products.isLoading || !products.data ? <LoadingState /> : <ProductTable items={products.data} compact />}</Panel><Panel eyebrow="Market view" title="Leading countries" action={<Link className="panel-link" to="/geography">Explore <ArrowUpRight size={14} /></Link>}>{countries.error ? <ErrorState message={countries.error} onRetry={countries.retry} /> : countries.isLoading || !countries.data ? <LoadingState /> : <CountryTable items={countries.data} />}</Panel></div>
    </>}
  </div>;
}

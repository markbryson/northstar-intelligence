import { Repeat2, UserRound, UsersRound } from "lucide-react";
import { api } from "../api/client";
import { useDashboard } from "../context/DashboardContext";
import { useApi } from "../hooks/useAnalytics";
import { CustomerTable } from "../components/tables/CustomerTable";
import { MetricCard } from "../components/ui/MetricCard";
import { Panel } from "../components/ui/Panel";
import { ErrorState, LoadingState } from "../components/ui/States";
import { formatCurrency, number, percent } from "../utils/format";

export function CustomersPage() {
  const { filters } = useDashboard();
  const customers = useApi(() => api.customers(filters, 100), [filters.startDate, filters.endDate, filters.country]);
  return <div className="page-stack"><div className="page-intro"><div><p className="eyebrow">Relationship lens</p><h2>Customers with context.</h2><p>Understand known-customer revenue and repeat purchasing in the historical record.</p></div></div>{customers.error ? <ErrorState message={customers.error} onRetry={customers.retry} /> : customers.isLoading || !customers.data ? <LoadingState label="Loading customer analytics" /> : <><div className="metric-grid metric-grid-compact"><MetricCard label="Known customers" value={number.format(customers.data.customer_count)} detail="Customer IDs present" icon={UsersRound} accent="cyan" /><MetricCard label="Repeat customers" value={number.format(customers.data.repeat_customer_count)} detail={`${percent(customers.data.repeat_customer_rate)} of known customers`} icon={Repeat2} accent="amber" /><MetricCard label="Customer revenue" value={formatCurrency(customers.data.total_customer_revenue)} detail="Net revenue with IDs" icon={UserRound} accent="blue" /></div><Panel eyebrow="Revenue concentration" title="Top 100 customer leaderboard" action={<span className="panel-meta">Top 100 by net revenue</span>}><CustomerTable items={customers.data.items} /></Panel></>}</div>;
}

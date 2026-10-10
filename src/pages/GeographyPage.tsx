import { Globe2, MapPin } from "lucide-react";
import { api } from "../api/client";
import { useDashboard } from "../context/DashboardContext";
import { useApi } from "../hooks/useAnalytics";
import { CountryTable } from "../components/tables/CountryTable";
import { Panel } from "../components/ui/Panel";
import { ErrorState, LoadingState } from "../components/ui/States";
import { formatCurrency, number } from "../utils/format";

export function GeographyPage() {
  const { filters } = useDashboard();
  const countries = useApi(() => api.countries(filters, 100), [filters.startDate, filters.endDate, filters.country]);
  const leading = countries.data?.[0];
  return (
    <div className="page-stack">
      <div className="page-intro"><div><p className="eyebrow">Market footprint</p><h2>Where demand shows up.</h2><p>Country-level activity from the source transactions. No geographic estimates are inferred.</p></div><div className="page-icon"><Globe2 size={20} /></div></div>
      {countries.error ? <ErrorState message={countries.error} onRetry={countries.retry} /> : countries.isLoading || !countries.data ? <LoadingState label="Loading market performance" /> : <>
        <div className="stat-strip"><div><span>Markets displayed</span><strong>{number.format(countries.data.length)}</strong></div><div><span>Leading market</span><strong>{leading?.country ?? "-"}</strong></div><div><span>Leading net revenue</span><strong>{formatCurrency(leading?.net_revenue ?? 0)}</strong></div><div><span>Orders in leading market</span><strong>{number.format(leading?.order_count ?? 0)}</strong></div></div>
        <div className="grid-two-thirds"><Panel eyebrow="Top 100 markets ranked by net revenue" title="Country performance"><CountryTable items={countries.data} /></Panel><Panel eyebrow="Geographic integrity" title="No invented geography"><div className="context-callout vertical"><MapPin size={20} /><div><strong>Source-level country labels</strong><p>The API exposes the country field captured in each transaction. A map is intentionally omitted because the current backend provides no geocoded boundaries or latitude/longitude data.</p></div></div></Panel></div>
      </>}
    </div>
  );
}

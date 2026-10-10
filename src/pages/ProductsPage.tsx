import { Search, SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";
import { api } from "../api/client";
import { useDashboard } from "../context/DashboardContext";
import { useApi } from "../hooks/useAnalytics";
import { ProductTable } from "../components/tables/ProductTable";
import { Panel } from "../components/ui/Panel";
import { ErrorState, LoadingState } from "../components/ui/States";
import { formatCurrency, number } from "../utils/format";

export function ProductsPage() {
  const { filters } = useDashboard();
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<"revenue" | "units">("revenue");
  const products = useApi(() => api.topProducts(filters, 100), [filters.startDate, filters.endDate, filters.country]);
  const filtered = useMemo(() => (products.data ?? []).filter((item) => `${item.stock_code} ${item.description ?? ""}`.toLowerCase().includes(search.toLowerCase())).sort((a, b) => sort === "revenue" ? b.net_revenue - a.net_revenue : b.units_sold - a.units_sold), [products.data, search, sort]);
  const total = filtered.reduce((sum, product) => sum + product.net_revenue, 0);
  return <div className="page-stack"><div className="page-intro"><div><p className="eyebrow">Merchandising lens</p><h2>Product performance.</h2><p>See which individual SKUs carry the most net revenue and volume.</p></div><div className="page-icon"><SlidersHorizontal size={18} /></div></div><div className="stat-strip"><div><span>Products displayed</span><strong>{number.format(filtered.length)}</strong></div><div><span>Net revenue displayed</span><strong>{formatCurrency(total)}</strong></div><div><span>Ranking</span><strong>{sort === "revenue" ? "Revenue" : "Units sold"}</strong></div></div><Panel title="Product leaderboard" eyebrow="Top 100 products; search filters this loaded set" action={<div className="table-controls"><label className="search-input"><Search size={15} /><input placeholder="Search code or description" value={search} onChange={(event) => setSearch(event.target.value)} /></label><div className="segmented-control"><button className={sort === "revenue" ? "selected" : ""} onClick={() => setSort("revenue")}>Revenue</button><button className={sort === "units" ? "selected" : ""} onClick={() => setSort("units")}>Units</button></div></div>}>{products.error ? <ErrorState message={products.error} onRetry={products.retry} /> : products.isLoading || !products.data ? <LoadingState label="Loading product performance" /> : <ProductTable items={filtered} />}</Panel></div>;
}

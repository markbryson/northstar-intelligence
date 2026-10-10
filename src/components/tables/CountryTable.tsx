import { ArrowUpRight } from "lucide-react";
import type { CountryPerformance } from "../../types/analytics";
import { formatCurrency, number } from "../../utils/format";
import { EmptyState } from "../ui/States";

export function CountryTable({ items }: { items: CountryPerformance[] }) {
  if (!items.length) return <EmptyState />;
  const max = Math.max(...items.map((item) => item.net_revenue), 1);
  return <div className="country-list">{items.map((item, index) => <div className="country-row" key={item.country}><span className="country-rank">{index + 1}</span><div className="country-name"><strong>{item.country}</strong><span className="mini-bar"><i style={{ width: `${Math.max((item.net_revenue / max) * 100, 3)}%` }} /></span></div><div className="country-stat"><strong>{formatCurrency(item.net_revenue)}</strong><small>{number.format(item.order_count)} orders</small></div><ArrowUpRight size={15} className="muted" /></div>)}</div>;
}

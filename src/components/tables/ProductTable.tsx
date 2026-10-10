import { ArrowUpRight, Package } from "lucide-react";
import type { ProductPerformance } from "../../types/analytics";
import { formatCurrency, number } from "../../utils/format";
import { EmptyState } from "../ui/States";

export function ProductTable({ items, compact = false }: { items: ProductPerformance[]; compact?: boolean }) {
  if (!items.length) return <EmptyState />;
  return <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Product</th><th>Net revenue</th><th>Units sold</th><th>Returns</th>{!compact && <th>Rows</th>}</tr></thead><tbody>{items.map((item, index) => <tr key={item.stock_code}><td><div className="product-cell"><span className="rank-badge">{String(index + 1).padStart(2, "0")}</span><span className="product-glyph"><Package size={15} /></span><span><strong>{item.description || "Unnamed product"}</strong><small>{item.stock_code}</small></span></div></td><td><strong>{formatCurrency(item.net_revenue)}</strong></td><td>{number.format(item.units_sold)}</td><td className={item.returned_units ? "text-warm" : "muted"}>{number.format(item.returned_units)}</td>{!compact && <td className="muted">{number.format(item.transaction_count)}</td>}</tr>)}</tbody></table>{compact && <div className="table-footer-link"><span>Showing top {items.length} products</span><ArrowUpRight size={14} /></div>}</div>;
}

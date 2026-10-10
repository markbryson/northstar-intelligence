import { Repeat2, UserRound } from "lucide-react";
import type { CustomerPerformance } from "../../types/analytics";
import { formatCurrency, number } from "../../utils/format";
import { EmptyState } from "../ui/States";

export function CustomerTable({ items }: { items: CustomerPerformance[] }) {
  if (!items.length) return <EmptyState />;
  return <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Customer</th><th>Revenue</th><th>Orders</th><th>Activity</th></tr></thead><tbody>{items.map((item) => <tr key={item.customer_id}><td><div className="customer-cell"><span className="customer-avatar"><UserRound size={15} /></span><span><strong>Customer {item.customer_id}</strong><small>{item.is_repeat_customer ? <><Repeat2 size={11} /> Repeat customer</> : "Single-order customer"}</small></span></div></td><td><strong>{formatCurrency(item.net_revenue)}</strong></td><td>{number.format(item.order_count)}</td><td className="muted">{number.format(item.transaction_count)} rows</td></tr>)}</tbody></table></div>;
}

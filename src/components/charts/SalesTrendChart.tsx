import { CalendarRange } from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SalesTrend } from "../../types/analytics";
import { formatCompactCurrency, formatPeriod } from "../../utils/format";

export function SalesTrendChart({ data, compact = false }: { data: SalesTrend[]; compact?: boolean }) {
  return (
    <div className="chart-wrap">
      {data.length ? <ResponsiveContainer width="100%" height={compact ? 220 : 310}>
        <AreaChart data={data} margin={{ top: 10, right: 8, left: 0, bottom: 0 }}>
          <defs><linearGradient id="netFill" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#72e1d2" stopOpacity={0.28} /><stop offset="95%" stopColor="#72e1d2" stopOpacity={0} /></linearGradient></defs>
          <CartesianGrid vertical={false} stroke="#dce6ec" strokeDasharray="4 4" />
          <XAxis dataKey="period" tickFormatter={formatPeriod} axisLine={false} tickLine={false} tick={{ fill: "#8190a0", fontSize: 11 }} minTickGap={24} />
          <YAxis axisLine={false} tickLine={false} tick={{ fill: "#8190a0", fontSize: 11 }} tickFormatter={formatCompactCurrency} width={48} />
          <Tooltip content={<TrendTooltip />} />
          <Area type="monotone" dataKey="net_sales" name="Net sales" stroke="#32b8a8" strokeWidth={2.5} fill="url(#netFill)" activeDot={{ r: 5, fill: "#32b8a8", stroke: "#fff", strokeWidth: 2 }} />
          <Area type="monotone" dataKey="returns" name="Returns" stroke="#f39b72" strokeWidth={1.5} fill="none" strokeDasharray="5 5" />
        </AreaChart>
      </ResponsiveContainer> : <div className="chart-empty"><CalendarRange size={22} />No trend data for this scope</div>}
    </div>
  );
}

function TrendTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; label?: string }) {
  if (!active || !payload?.length) return null;
  return <div className="chart-tooltip"><p>{formatPeriod(label ?? "")}</p>{payload.map((item) => <div key={item.name}><span style={{ background: item.color }} />{item.name}<strong>{formatCompactCurrency(item.value)}</strong></div>)}</div>;
}

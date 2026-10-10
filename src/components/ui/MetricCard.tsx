import { ArrowDownRight, ArrowUpRight, type LucideIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string;
  detail?: string;
  icon: LucideIcon;
  accent?: "cyan" | "amber" | "blue" | "rose";
  trend?: "up" | "down";
}

export function MetricCard({ label, value, detail, icon: Icon, accent = "cyan", trend }: MetricCardProps) {
  return (
    <article className={`metric-card metric-${accent}`}>
      <div className="metric-topline">
        <span className="metric-icon"><Icon size={18} strokeWidth={1.8} /></span>
        <span className="metric-label">{label}</span>
        {trend && (
          <span className={`metric-trend ${trend}`}>
            {trend === "up" ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
          </span>
        )}
      </div>
      <p className="metric-value">{value}</p>
      {detail && <p className="metric-detail">{detail}</p>}
    </article>
  );
}

export const GBP = new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 0 });
export const GBPExact = new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 2 });
export const number = new Intl.NumberFormat("en-GB");
const percentFormatter = new Intl.NumberFormat("en-GB", { style: "percent", maximumFractionDigits: 1 });

export function formatCurrency(value: number) { return GBPExact.format(value); }
export function percent(value: number) { return percentFormatter.format(value); }
export function formatCompactCurrency(value: number) {
  if (Math.abs(value) >= 1_000_000) return `£${(value / 1_000_000).toFixed(1)}m`;
  if (Math.abs(value) >= 1_000) return `£${(value / 1_000).toFixed(0)}k`;
  return `£${Math.round(value)}`;
}
export function formatPeriod(value: string) {
  if (!value) return "";
  if (/^\d{4}-\d{2}-\d{2}/.test(value)) return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short" }).format(new Date(value));
  if (/^\d{4}-\d{2}$/.test(value)) return new Intl.DateTimeFormat("en-GB", { month: "short", year: "2-digit" }).format(new Date(`${value}-01`));
  return value;
}
export function formatDate(value: string | null) { return value ? new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value)) : "—"; }

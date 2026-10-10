import { CalendarDays, Check, Filter, RotateCcw } from "lucide-react";
import { useState } from "react";
import { useDashboard } from "../../context/DashboardContext";
import type { AnalyticsFilters } from "../../types/analytics";
import { ErrorState } from "../ui/States";

export function FilterBar() {
  const { filters, setFilters, options, optionsLoading, optionsError, retryOptions } = useDashboard();
  const [draft, setDraft] = useState<AnalyticsFilters>(filters);

  const apply = () => setFilters({ ...draft });
  const reset = () => {
    const next = {};
    setDraft(next);
    setFilters(next);
  };

  return (
    <div className="filter-bar">
      <div className="filter-heading"><Filter size={16} /><span>Explore the archive</span></div>
      {optionsError && <ErrorState message="Filter options could not be loaded. Please retry." onRetry={retryOptions} />}
      <label className="filter-field"><span><CalendarDays size={14} /> From</span><input type="date" value={draft.startDate ?? ""} onChange={(event) => setDraft({ ...draft, startDate: event.target.value || undefined })} /></label>
      <label className="filter-field"><span><CalendarDays size={14} /> To</span><input type="date" value={draft.endDate ?? ""} onChange={(event) => setDraft({ ...draft, endDate: event.target.value || undefined })} /></label>
      <label className="filter-field country-field"><span>Country</span><select value={draft.country ?? ""} onChange={(event) => setDraft({ ...draft, country: event.target.value || undefined })}><option value="">All markets</option>{options?.countries.map((country) => <option key={country} value={country}>{country}</option>)}</select></label>
      <div className="filter-actions"><button className="button button-primary" onClick={apply} disabled={optionsLoading}><Check size={15} /> Apply</button><button className="button button-ghost" onClick={reset} aria-label="Reset filters"><RotateCcw size={15} /></button></div>
    </div>
  );
}

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { api } from "../api/client";
import { useApi } from "../hooks/useAnalytics";
import type { AnalyticsFilters, FilterOptions } from "../types/analytics";

interface DashboardContextValue {
  filters: AnalyticsFilters;
  setFilters: (filters: AnalyticsFilters) => void;
  options: FilterOptions | null;
  optionsLoading: boolean;
  optionsError: string | null;
  retryOptions: () => void;
}

const DashboardContext = createContext<DashboardContextValue | undefined>(undefined);

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [filters, setFilters] = useState<AnalyticsFilters>({});
  const filterOptions = useApi(() => api.filterOptions(), []);
  const value = useMemo(
    () => ({
      filters,
      setFilters,
      options: filterOptions.data,
      optionsLoading: filterOptions.isLoading,
      optionsError: filterOptions.error,
      retryOptions: filterOptions.retry,
    }),
    [filters, filterOptions.data, filterOptions.isLoading, filterOptions.error, filterOptions.retry],
  );
  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

export function useDashboard() {
  const value = useContext(DashboardContext);
  if (!value) throw new Error("useDashboard must be used within DashboardProvider");
  return value;
}

import { AlertCircle, LoaderCircle, RefreshCw } from "lucide-react";

export function LoadingState({ label = "Loading analytics" }: { label?: string }) {
  return <div className="state-card"><LoaderCircle className="spin" size={20} /><span>{label}</span></div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state-card error-state">
      <AlertCircle size={20} />
      <span>{message}</span>
      {onRetry && <button className="icon-button" onClick={onRetry} aria-label="Retry"><RefreshCw size={16} /></button>}
    </div>
  );
}

export function EmptyState({ message = "No records match the current filters." }: { message?: string }) {
  return <div className="empty-state">{message}</div>;
}

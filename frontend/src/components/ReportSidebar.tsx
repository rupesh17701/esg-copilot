import { ReportSummary } from "../api/client";

interface Props {
  reports: ReportSummary[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
}

export default function ReportSidebar({ reports, selectedId, onSelect, onDelete }: Props) {
  if (reports.length === 0) {
    return <p className="text-sm text-ink-muted">No reports uploaded yet.</p>;
  }

  return (
    <ul className="space-y-1">
      {reports.map((r) => (
        <li key={r.id}>
          <div
            className={`group flex items-center justify-between rounded-md px-3 py-2 text-sm cursor-pointer ${
              r.id === selectedId
                ? "bg-series-1/10 text-series-1 dark:text-series-1-dark"
                : "text-ink-secondary hover:bg-black/5 dark:text-ink-secondary-dark dark:hover:bg-white/5"
            }`}
            onClick={() => onSelect(r.id)}
          >
            <div className="min-w-0">
              <div className="truncate font-medium">{r.company_name}</div>
              <div className="truncate text-xs text-ink-muted">{r.sector}</div>
            </div>
            <button
              className="ml-2 shrink-0 rounded px-1.5 py-0.5 text-xs text-ink-muted opacity-0 hover:bg-status-critical/10 hover:text-status-critical group-hover:opacity-100"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(r.id);
              }}
              aria-label={`Delete ${r.company_name}`}
            >
              ✕
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

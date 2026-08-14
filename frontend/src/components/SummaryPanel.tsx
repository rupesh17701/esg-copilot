import { useState } from "react";
import { api } from "../api/client";

export default function SummaryPanel({ reportId }: { reportId: number }) {
  const [summary, setSummary] = useState<string | null>(null);
  const [source, setSource] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function generate() {
    setLoading(true);
    try {
      const res = await api.getSummary(reportId);
      setSummary(res.summary);
      setSource(res.source);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-lg border border-black/10 bg-surface p-4 dark:border-white/10 dark:bg-surface-dark">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-ink-primary dark:text-ink-primary-dark">AI risk narrative</h3>
        <button
          className="rounded-md border border-black/10 px-3 py-1 text-xs font-medium text-ink-primary hover:bg-black/5 dark:border-white/10 dark:text-ink-primary-dark dark:hover:bg-white/5"
          onClick={generate}
          disabled={loading}
        >
          {loading ? "Generating…" : summary ? "Regenerate" : "Generate summary"}
        </button>
      </div>
      {summary ? (
        <div className="mt-3 whitespace-pre-wrap text-sm text-ink-secondary dark:text-ink-secondary-dark">
          {summary}
          {source && (
            <div className="mt-2 text-xs text-ink-muted">Source: {source === "anthropic" ? "Claude" : "offline template"}</div>
          )}
        </div>
      ) : (
        <p className="mt-2 text-sm text-ink-muted">Generate a concise narrative summary of this company's ESG risk profile.</p>
      )}
    </div>
  );
}

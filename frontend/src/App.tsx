import { useEffect, useState } from "react";
import { api, ReportDetail, ReportSummary } from "./api/client";
import CarbonPanel from "./components/CarbonPanel";
import ChatPanel from "./components/ChatPanel";
import DimensionBars from "./components/DimensionBars";
import PrincipleList from "./components/PrincipleList";
import ReportSidebar from "./components/ReportSidebar";
import ScoreGauge from "./components/ScoreGauge";
import SummaryPanel from "./components/SummaryPanel";
import UploadPanel from "./components/UploadPanel";

export default function App() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [selected, setSelected] = useState<ReportDetail | null>(null);
  const [llmMode, setLlmMode] = useState<string | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    api.health().then((h) => setLlmMode(h.llm_mode));
    refreshList();
  }, []);

  async function refreshList() {
    const list = await api.listReports();
    setReports(list);
  }

  async function selectReport(id: number) {
    setLoadingDetail(true);
    try {
      const detail = await api.getReport(id);
      setSelected(detail);
    } finally {
      setLoadingDetail(false);
    }
  }

  async function handleUploaded(id: number) {
    await refreshList();
    await selectReport(id);
  }

  async function handleDelete(id: number) {
    await api.deleteReport(id);
    if (selected?.id === id) setSelected(null);
    await refreshList();
  }

  return (
    <div className="min-h-screen bg-plane text-ink-primary dark:bg-plane-dark dark:text-ink-primary-dark">
      <header className="border-b border-black/10 bg-surface px-6 py-4 dark:border-white/10 dark:bg-surface-dark">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <h1 className="text-lg font-bold">ESG Copilot</h1>
            <p className="text-xs text-ink-muted">AI agent for BRSR analysis, ESG risk & carbon intelligence</p>
          </div>
          {llmMode && (
            <span
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                llmMode === "anthropic" ? "bg-status-good/10 text-status-good" : "bg-status-warning/10 text-status-warning"
              }`}
            >
              {llmMode === "anthropic" ? "Claude connected" : "Offline mode (no API key)"}
            </span>
          )}
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 p-6 lg:grid-cols-[260px_1fr]">
        <aside className="space-y-4">
          <UploadPanel onUploaded={handleUploaded} />
          <div>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">Reports</h2>
            <ReportSidebar reports={reports} selectedId={selected?.id ?? null} onSelect={selectReport} onDelete={handleDelete} />
          </div>
        </aside>

        <section>
          {!selected && !loadingDetail && (
            <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-baseline text-sm text-ink-muted dark:border-baseline-dark">
              Upload a BRSR report to see its ESG score, carbon intelligence, and chat with the copilot.
            </div>
          )}

          {loadingDetail && <div className="p-8 text-sm text-ink-muted">Loading…</div>}

          {selected && !loadingDetail && (
            <div className="space-y-6">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <div>
                  <h2 className="text-xl font-bold">{selected.company_name}</h2>
                  <p className="text-sm text-ink-muted">
                    {selected.sector} · {selected.extracted_data.reporting_year ?? "Year not disclosed"} ·{" "}
                    {selected.extraction_source === "heuristic" ? "Offline extraction" : "AI-assisted extraction"}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-6 md:grid-cols-[220px_1fr]">
                <div className="flex items-center justify-center rounded-lg border border-black/10 bg-surface p-4 dark:border-white/10 dark:bg-surface-dark">
                  <ScoreGauge score={selected.esg_score.overall_score} band={selected.esg_score.risk_band} />
                </div>
                <div className="rounded-lg border border-black/10 bg-surface p-4 dark:border-white/10 dark:bg-surface-dark">
                  <h3 className="mb-3 text-sm font-semibold">Score by dimension</h3>
                  <DimensionBars dimensions={selected.esg_score.dimensions} />
                  <p className="mt-3 text-xs text-ink-muted">
                    Overall disclosure completeness across all 9 NGRBC principles: {selected.esg_score.disclosure_completeness_pct}%
                  </p>
                </div>
              </div>

              <SummaryPanel reportId={selected.id} />

              <div className="rounded-lg border border-black/10 bg-surface p-4 dark:border-white/10 dark:bg-surface-dark">
                <h3 className="mb-3 text-sm font-semibold">Carbon intelligence</h3>
                <CarbonPanel carbon={selected.carbon_metrics} />
              </div>

              <div className="rounded-lg border border-black/10 bg-surface p-4 dark:border-white/10 dark:bg-surface-dark">
                <h3 className="mb-3 text-sm font-semibold">NGRBC principle-wise disclosure completeness</h3>
                <PrincipleList principles={selected.extracted_data.principles} />
              </div>

              <div className="h-[420px] rounded-lg border border-black/10 bg-surface p-4 dark:border-white/10 dark:bg-surface-dark">
                <ChatPanel reportId={selected.id} />
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

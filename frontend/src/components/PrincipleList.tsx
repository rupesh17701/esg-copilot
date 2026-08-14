import { PrincipleDisclosure } from "../api/client";

export default function PrincipleList({ principles }: { principles: PrincipleDisclosure[] }) {
  const sorted = [...principles].sort((a, b) => a.principle - b.principle);
  return (
    <div className="space-y-3">
      {sorted.map((p) => (
        <div key={p.principle}>
          <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
            <span className="text-ink-primary dark:text-ink-primary-dark">
              <span className="font-semibold">P{p.principle}</span>{" "}
              <span className="text-ink-secondary dark:text-ink-secondary-dark">{p.title}</span>
            </span>
            <span className="shrink-0 tabular-nums text-ink-muted">
              {p.essential_indicators_found}/{p.essential_indicators_expected} · {p.disclosure_completeness.toFixed(0)}%
            </span>
          </div>
          <div
            className="h-1.5 w-full rounded-full bg-grid dark:bg-grid-dark"
            title={`${p.disclosure_completeness.toFixed(0)}% of expected essential indicators found`}
          >
            <div
              className="h-1.5 rounded-full bg-series-1 dark:bg-series-1-dark"
              style={{ width: `${Math.min(100, p.disclosure_completeness)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

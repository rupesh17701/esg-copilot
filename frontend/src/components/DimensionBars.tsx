import { DimensionScore } from "../api/client";

const DIMENSION_META: Record<DimensionScore["dimension"], { label: string; color: string }> = {
  environmental: { label: "Environmental", color: "#2a78d6" },
  social: { label: "Social", color: "#eb6834" },
  governance: { label: "Governance", color: "#1baf7a" },
};

export default function DimensionBars({ dimensions }: { dimensions: DimensionScore[] }) {
  return (
    <div className="space-y-4">
      {dimensions.map((d) => {
        const meta = DIMENSION_META[d.dimension];
        return (
          <div key={d.dimension}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="flex items-center gap-2 font-medium text-ink-primary dark:text-ink-primary-dark">
                <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: meta.color }} />
                {meta.label}
              </span>
              <span className="tabular-nums text-ink-secondary dark:text-ink-secondary-dark">{d.score.toFixed(1)}</span>
            </div>
            <div className="h-2 w-full rounded-full bg-grid dark:bg-grid-dark">
              <div
                className="h-2 rounded-full transition-[width]"
                style={{ width: `${Math.min(100, d.score)}%`, backgroundColor: meta.color }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

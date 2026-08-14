import { CarbonIntelligenceResult } from "../api/client";
import StatTile from "./StatTile";

const POSITION_COLOR: Record<CarbonIntelligenceResult["benchmark_position"], string> = {
  "Below average": "#0ca30c",
  Average: "#fab219",
  "Above average": "#d03b3b",
  Unknown: "#898781",
};

function fmt(value: number | null, unit: string, digits = 0): string {
  return value === null ? "Not disclosed" : `${value.toLocaleString(undefined, { maximumFractionDigits: digits })} ${unit}`;
}

export default function CarbonPanel({ carbon }: { carbon: CarbonIntelligenceResult }) {
  return (
    <div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Scope 1" value={fmt(carbon.scope1_tco2e, "tCO2e")} />
        <StatTile label="Scope 2" value={fmt(carbon.scope2_tco2e, "tCO2e")} />
        <StatTile label="Scope 3" value={fmt(carbon.scope3_tco2e, "tCO2e")} />
        <StatTile
          label="Total Scope 1+2"
          value={fmt(carbon.total_scope12_tco2e, "tCO2e")}
          accent="#2a78d6"
        />
      </div>

      {carbon.benchmark && (
        <div className="mt-4 rounded-lg border border-black/10 bg-surface p-4 dark:border-white/10 dark:bg-surface-dark">
          <div className="flex items-center justify-between">
            <div className="text-xs font-medium uppercase tracking-wide text-ink-muted">
              Carbon intensity vs. {carbon.benchmark.sector} sector benchmark
            </div>
            <span
              className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium"
              style={{
                color: POSITION_COLOR[carbon.benchmark_position],
                backgroundColor: `${POSITION_COLOR[carbon.benchmark_position]}1a`,
              }}
            >
              {carbon.benchmark_position}
            </span>
          </div>
          <div className="mt-2 text-lg font-semibold tabular-nums text-ink-primary dark:text-ink-primary-dark">
            {carbon.carbon_intensity_per_revenue ?? "—"}{" "}
            <span className="text-sm font-normal text-ink-secondary dark:text-ink-secondary-dark">
              tCO2e / INR crore revenue
            </span>
          </div>
          <div className="mt-1 text-xs text-ink-muted">
            Sector typical range: {carbon.benchmark.typical_intensity_range[0]}–{carbon.benchmark.typical_intensity_range[1]}{" "}
            {carbon.benchmark.unit}
          </div>
        </div>
      )}

      {carbon.observations.length > 0 && (
        <ul className="mt-4 space-y-1.5 text-sm text-ink-secondary dark:text-ink-secondary-dark">
          {carbon.observations.map((obs, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-ink-muted">•</span>
              <span>{obs}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

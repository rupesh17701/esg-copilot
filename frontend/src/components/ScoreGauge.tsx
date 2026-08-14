import { RISK_BAND_META, RiskBand } from "./riskBand";

interface Props {
  score: number;
  band: RiskBand;
}

export default function ScoreGauge({ score, band }: Props) {
  const meta = RISK_BAND_META[band];
  const size = 160;
  const stroke = 14;
  const radius = (size - stroke) / 2;
  const circumference = Math.PI * radius; // semicircle
  const pct = Math.max(0, Math.min(100, score)) / 100;
  const dash = circumference * pct;

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size / 2 + stroke / 2} viewBox={`0 0 ${size} ${size / 2 + stroke / 2}`}>
        <path
          d={`M ${stroke / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - stroke / 2} ${size / 2}`}
          fill="none"
          stroke="#e1e0d9"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        <path
          d={`M ${stroke / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - stroke / 2} ${size / 2}`}
          fill="none"
          stroke={meta.color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
        />
      </svg>
      <div className="-mt-4 text-center">
        <div className="text-4xl font-bold text-ink-primary dark:text-ink-primary-dark tabular-nums">
          {score.toFixed(1)}
        </div>
        <div className="text-xs text-ink-muted">/ 100</div>
      </div>
      <div
        className="mt-2 inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-medium"
        style={{ color: meta.color, backgroundColor: `${meta.color}1a` }}
      >
        <span aria-hidden>{meta.icon}</span>
        <span>{meta.label}</span>
      </div>
    </div>
  );
}

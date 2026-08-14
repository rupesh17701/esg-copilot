interface Props {
  label: string;
  value: string;
  sublabel?: string;
  accent?: string;
}

export default function StatTile({ label, value, sublabel, accent }: Props) {
  return (
    <div className="rounded-lg border border-black/10 bg-surface p-4 dark:border-white/10 dark:bg-surface-dark">
      <div className="text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</div>
      <div
        className="mt-1 text-2xl font-semibold tabular-nums text-ink-primary dark:text-ink-primary-dark"
        style={accent ? { color: accent } : undefined}
      >
        {value}
      </div>
      {sublabel && <div className="mt-1 text-xs text-ink-secondary dark:text-ink-secondary-dark">{sublabel}</div>}
    </div>
  );
}

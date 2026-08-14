export type RiskBand = "Low" | "Moderate" | "Elevated" | "High";

export const RISK_BAND_META: Record<RiskBand, { color: string; icon: string; label: string }> = {
  Low: { color: "#0ca30c", icon: "✓", label: "Low risk" },
  Moderate: { color: "#fab219", icon: "▲", label: "Moderate risk" },
  Elevated: { color: "#ec835a", icon: "▲", label: "Elevated risk" },
  High: { color: "#d03b3b", icon: "✕", label: "High risk" },
};

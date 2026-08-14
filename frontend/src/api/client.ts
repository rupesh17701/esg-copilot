export interface PrincipleDisclosure {
  principle: number;
  title: string;
  essential_indicators_found: number;
  essential_indicators_expected: number;
  leadership_indicators_found: number;
  notes: string[];
  disclosure_completeness: number;
}

export interface EnvironmentalMetrics {
  scope1_emissions_tco2e: number | null;
  scope2_emissions_tco2e: number | null;
  scope3_emissions_tco2e: number | null;
  total_energy_consumption_gj: number | null;
  renewable_energy_pct: number | null;
  water_withdrawal_kl: number | null;
  water_recycled_pct: number | null;
  total_waste_generated_mt: number | null;
  waste_recycled_pct: number | null;
  revenue_inr_crore: number | null;
}

export interface GovernanceSignals {
  board_independence_pct: number | null;
  anti_corruption_policy: boolean | null;
  whistleblower_mechanism: boolean | null;
  complaints_received: number | null;
  complaints_resolved: number | null;
}

export interface SocialSignals {
  employee_wellbeing_coverage_pct: number | null;
  safety_incidents_total: number | null;
  human_rights_complaints: number | null;
  csr_spend_inr_crore: number | null;
  women_workforce_pct: number | null;
}

export interface ExtractedBRSRData {
  company_name: string;
  sector: string;
  reporting_year: string | null;
  principles: PrincipleDisclosure[];
  environment: EnvironmentalMetrics;
  governance: GovernanceSignals;
  social: SocialSignals;
}

export interface DimensionScore {
  dimension: "environmental" | "social" | "governance";
  score: number;
  max_score: number;
  rationale: string[];
}

export interface ESGScoreResult {
  overall_score: number;
  risk_band: "Low" | "Moderate" | "Elevated" | "High";
  dimensions: DimensionScore[];
  disclosure_completeness_pct: number;
}

export interface CarbonBenchmark {
  sector: string;
  typical_intensity_range: [number, number];
  unit: string;
}

export interface CarbonIntelligenceResult {
  scope1_tco2e: number | null;
  scope2_tco2e: number | null;
  scope3_tco2e: number | null;
  total_scope12_tco2e: number | null;
  carbon_intensity_per_revenue: number | null;
  renewable_energy_pct: number | null;
  benchmark: CarbonBenchmark | null;
  benchmark_position: "Below average" | "Average" | "Above average" | "Unknown";
  observations: string[];
}

export interface ReportSummary {
  id: number;
  filename: string;
  company_name: string;
  sector: string;
  created_at: string;
  extraction_source: string;
}

export interface ReportDetail extends ReportSummary {
  extracted_data: ExtractedBRSRData;
  esg_score: ESGScoreResult;
  carbon_metrics: CarbonIntelligenceResult;
}

export interface ChatMessageOut {
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatResponse {
  reply: string;
  source: "anthropic" | "offline";
  citations: string[];
}

const API_BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; llm_configured: boolean; llm_mode: string }>("/health"),

  listReports: () => request<ReportSummary[]>("/reports"),

  getReport: (id: number) => request<ReportDetail>(`/reports/${id}`),

  uploadReport: async (file: File): Promise<ReportDetail> => {
    const form = new FormData();
    form.append("file", file);
    return request<ReportDetail>("/reports", { method: "POST", body: form });
  },

  deleteReport: (id: number) => request<void>(`/reports/${id}`, { method: "DELETE" }),

  getSummary: (id: number) => request<{ summary: string; source: string }>(`/reports/${id}/summary`),

  getChatHistory: (id: number) => request<ChatMessageOut[]>(`/reports/${id}/chat`),

  sendChatMessage: (id: number, message: string) =>
    request<ChatResponse>(`/reports/${id}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    }),
};

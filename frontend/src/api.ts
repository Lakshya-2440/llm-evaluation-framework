export type RunStatus = "queued" | "running" | "completed" | "failed";
export type AttackCategory = "hallucination" | "bias" | "safety" | "robustness";

export type EvalRunRequest = {
  target_model?: string;
  attacker_model?: string;
  judge_model?: string;
  categories: AttackCategory[];
  attacks_per_category: number;
  rounds: number;
  use_mart: boolean;
  success_threshold: number;
  temperature: number;
  max_tokens: number;
  custom_judge_prompt?: string;
};

export type RunListItem = {
  id: string;
  status: RunStatus;
  progress: number;
  created_at: string;
  updated_at: string;
  target_model: string;
  attack_suite_id: string;
  error?: string | null;
  summary?: RunSummary | null;
};

export type RunSummary = {
  n_attacks: number;
  pass_rate: number;
  average_risk: number;
  category_pass_rates: Record<string, number>;
  risk_rating: "Green" | "Yellow" | "Red";
  top_failures: AttackRecord[];
};

export type AttackRecord = {
  id: string;
  round_number: number;
  category: AttackCategory;
  prompt: string;
  metadata: Record<string, string | number | null>;
  response_text?: string | null;
  score?: number | null;
  passed?: boolean | null;
  rationale?: string | null;
};

export type RunDetail = RunListItem & {
  attacker_model: string;
  judge_model: string;
  config: Record<string, unknown>;
  attacks: AttackRecord[];
};

export type CompareItem = {
  run_id: string;
  target_model: string;
  status: RunStatus;
  pass_rate: number;
  average_risk: number;
  category_pass_rates: Record<string, number>;
  n_attacks: number;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";
const API_KEY = import.meta.env.VITE_APP_API_KEY || "";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (API_KEY) headers.set("X-API-Key", API_KEY);
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

export const api = {
  async health() {
    return request<{ ok: boolean; hf_configured: boolean; database: string }>("/health");
  },
  async createRun(payload: EvalRunRequest) {
    return request<{ id: string; status: RunStatus }>("/eval/run", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  async listRuns() {
    return request<RunListItem[]>("/eval/run");
  },
  async getRun(id: string) {
    return request<RunDetail>(`/eval/run/${id}`);
  },
  async compare(ids: string[]) {
    return request<CompareItem[]>(`/eval/compare?run_ids=${encodeURIComponent(ids.join(","))}`);
  },
  async downloadReport(id: string, format: "technical" | "executive" | "json" | "csv" | "pdf") {
    const headers = new Headers();
    if (API_KEY) headers.set("X-API-Key", API_KEY);
    const response = await fetch(`${API_BASE}/eval/run/${id}/report?format=${format}`, { headers });
    if (!response.ok) throw new Error(await response.text());
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `llm-eval-${id}.${format === "pdf" ? "pdf" : format === "csv" ? "csv" : format === "json" ? "json" : "md"}`;
    anchor.click();
    URL.revokeObjectURL(url);
  }
};

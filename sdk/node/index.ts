export type EvalPayload = {
  target_model?: string;
  attacker_model?: string;
  judge_model?: string;
  categories: string[];
  attacks_per_category: number;
  rounds: number;
  use_mart: boolean;
  success_threshold: number;
};

export class LlmEvalClient {
  constructor(
    private baseUrl = "http://localhost:8000",
    private apiKey?: string
  ) {}

  private headers() {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (this.apiKey) headers["X-API-Key"] = this.apiKey;
    return headers;
  }

  async startEval(payload: EvalPayload) {
    const response = await fetch(`${this.baseUrl}/eval/run`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  }

  async status(runId: string) {
    const response = await fetch(`${this.baseUrl}/eval/run/${runId}/status`, {
      headers: this.headers()
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  }

  async report(runId: string, format = "json") {
    const response = await fetch(`${this.baseUrl}/eval/run/${runId}/report?format=${format}`, {
      headers: this.headers()
    });
    if (!response.ok) throw new Error(await response.text());
    return response.arrayBuffer();
  }
}

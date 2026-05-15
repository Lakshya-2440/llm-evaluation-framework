import { type ReactNode, useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  CheckCircle2,
  ClipboardList,
  Download,
  FileText,
  FlaskConical,
  Loader2,
  Play,
  RefreshCw,
  ShieldAlert,
  SlidersHorizontal,
  XCircle
} from "lucide-react";
import { api, AttackCategory, AttackRecord, CompareItem, EvalRunRequest, RunDetail, RunListItem } from "./api";

const CATEGORIES: AttackCategory[] = ["hallucination", "safety", "bias", "robustness", "privacy", "tool_misuse"];

const defaultForm: EvalRunRequest = {
  target_model: "Qwen/Qwen2.5-7B-Instruct:fastest",
  attacker_model: "Qwen/Qwen2.5-7B-Instruct:fastest",
  judge_model: "Qwen/Qwen2.5-7B-Instruct:fastest",
  categories: ["hallucination", "safety", "bias", "robustness", "privacy", "tool_misuse"],
  attacks_per_category: 8,
  rounds: 11,
  use_mart: true,
  success_threshold: 6,
  temperature: 0.4,
  max_tokens: 512
};

export function App() {
  const [form, setForm] = useState<EvalRunRequest>(defaultForm);
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [comparison, setComparison] = useState<CompareItem[]>([]);
  const [hfConfigured, setHfConfigured] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadRuns() {
    const list = await api.listRuns();
    setRuns(list);
    if (!selectedRunId && list[0]) setSelectedRunId(list[0].id);
  }

  async function loadHealth() {
    const health = await api.health();
    setHfConfigured(health.hf_configured);
  }

  useEffect(() => {
    loadHealth().catch(() => setHfConfigured(false));
    loadRuns().catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selectedRunId) {
      setDetail(null);
      return;
    }
    api.getRun(selectedRunId).then(setDetail).catch((err) => setError(err.message));
  }, [selectedRunId]);

  useEffect(() => {
    const active = runs.some((run) => run.status === "queued" || run.status === "running");
    if (!active) return;
    const interval = window.setInterval(async () => {
      await loadRuns();
      if (selectedRunId) {
        const next = await api.getRun(selectedRunId);
        setDetail(next);
      }
    }, 1400);
    return () => window.clearInterval(interval);
  }, [runs, selectedRunId]);

  useEffect(() => {
    if (compareIds.length < 2) {
      setComparison([]);
      return;
    }
    api.compare(compareIds).then(setComparison).catch((err) => setError(err.message));
  }, [compareIds]);

  const selectedRun = useMemo(() => runs.find((run) => run.id === selectedRunId), [runs, selectedRunId]);

  async function startRun() {
    setBusy(true);
    setError("");
    try {
      const created = await api.createRun(form);
      setSelectedRunId(created.id);
      await loadRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setBusy(false);
    }
  }

  function toggleCategory(category: AttackCategory) {
    setForm((current) => {
      const categories = current.categories.includes(category)
        ? current.categories.filter((item) => item !== category)
        : [...current.categories, category];
      return { ...current, categories: categories.length ? categories : current.categories };
    });
  }

  function toggleCompare(id: string) {
    setCompareIds((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">LLM Evaluation</p>
          <h1>Red-Team Console</h1>
        </div>
        <div className="status-strip">
          <span className={hfConfigured ? "pill good" : "pill warn"}>{hfConfigured ? "HF connected" : "Offline fallback"}</span>
          <button
            className="icon-button"
            title="Refresh"
            onClick={() => {
              loadHealth().catch((err) => setError(err.message));
              loadRuns().catch((err) => setError(err.message));
            }}
          >
            <RefreshCw size={18} />
          </button>
        </div>
      </header>

      {error && (
        <div className="error-banner">
          <ShieldAlert size={18} />
          <span>{error}</span>
        </div>
      )}

      <main className="workspace">
        <section className="run-panel" aria-label="Create evaluation run">
          <div className="section-title">
            <SlidersHorizontal size={18} />
            <h2>Run Setup</h2>
          </div>

          <label>
            Target model
            <input value={form.target_model || ""} onChange={(event) => setForm({ ...form, target_model: event.target.value })} />
          </label>
          <label>
            Attacker model
            <input value={form.attacker_model || ""} onChange={(event) => setForm({ ...form, attacker_model: event.target.value })} />
          </label>
          <label>
            Judge model
            <input value={form.judge_model || ""} onChange={(event) => setForm({ ...form, judge_model: event.target.value })} />
          </label>

          <div className="field-group">
            <span>Attack categories</span>
            <div className="chip-row">
              {CATEGORIES.map((category) => (
                <label className="check-chip" key={category}>
                  <input type="checkbox" checked={form.categories.includes(category)} onChange={() => toggleCategory(category)} />
                  {category}
                </label>
              ))}
            </div>
          </div>

          <div className="grid-two">
            <label>
              Attacks/category
              <input
                type="number"
                min={1}
                max={200}
                value={form.attacks_per_category}
                onChange={(event) => setForm({ ...form, attacks_per_category: Number(event.target.value) })}
              />
            </label>
            <label>
              Rounds
              <input
                type="number"
                min={1}
                max={12}
                value={form.rounds}
                onChange={(event) => setForm({ ...form, rounds: Number(event.target.value) })}
              />
            </label>
          </div>

          <label>
            Failure threshold
            <input
              type="range"
              min={0}
              max={10}
              step={0.5}
              value={form.success_threshold}
              onChange={(event) => setForm({ ...form, success_threshold: Number(event.target.value) })}
            />
            <span className="range-value">{form.success_threshold.toFixed(1)}</span>
          </label>

          <label className="toggle-row">
            <input type="checkbox" checked={form.use_mart} onChange={(event) => setForm({ ...form, use_mart: event.target.checked })} />
            <span>MART loop</span>
          </label>

          <label>
            Custom judge prompt
            <textarea
              value={form.custom_judge_prompt || ""}
              onChange={(event) => setForm({ ...form, custom_judge_prompt: event.target.value || undefined })}
              rows={4}
              placeholder="Optional domain rubric"
            />
          </label>

          <button className="primary-action" onClick={startRun} disabled={busy}>
            {busy ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
            Start evaluation
          </button>
        </section>

        <section className="results-area">
          <div className="overview-grid">
            <Metric title="Runs" value={runs.length.toString()} icon={<ClipboardList size={18} />} />
            <Metric title="Selected risk" value={selectedRun?.summary?.risk_rating || "-"} icon={<ShieldAlert size={18} />} tone={selectedRun?.summary?.risk_rating || ""} />
            <Metric title="Pass rate" value={selectedRun?.summary ? `${selectedRun.summary.pass_rate}%` : "-"} icon={<CheckCircle2 size={18} />} />
            <Metric title="Violations" value={selectedRun?.summary ? `${selectedRun.summary.violation_rate}%` : "-"} icon={<XCircle size={18} />} />
            <Metric title="Hallucination" value={selectedRun?.summary ? `${selectedRun.summary.hallucination_rate}%` : "-"} icon={<Activity size={18} />} />
          </div>

          <div className="split">
            <section className="list-panel" aria-label="Evaluation runs">
              <div className="section-title">
                <FlaskConical size={18} />
                <h2>Evaluation Runs</h2>
              </div>
              <div className="run-list">
                {runs.map((run) => (
                  <button
                    key={run.id}
                    className={`run-row ${selectedRunId === run.id ? "active" : ""}`}
                    onClick={() => setSelectedRunId(run.id)}
                  >
                    <span className={`dot ${run.status}`} />
                    <span className="run-main">
                      <strong>{run.target_model}</strong>
                      <small>{run.id.slice(0, 8)} - {new Date(run.created_at).toLocaleString()}</small>
                    </span>
                    <span className="progress-mini">
                      <span style={{ width: `${Math.round(run.progress * 100)}%` }} />
                    </span>
                    <input
                      type="checkbox"
                      checked={compareIds.includes(run.id)}
                      onChange={(event) => {
                        event.stopPropagation();
                        toggleCompare(run.id);
                      }}
                      onClick={(event) => event.stopPropagation()}
                      title="Compare run"
                    />
                  </button>
                ))}
                {!runs.length && <p className="empty-state">No runs yet.</p>}
              </div>
            </section>

            <section className="detail-panel" aria-label="Run results">
              {detail ? <RunDetailView detail={detail} /> : <p className="empty-state">Select a run.</p>}
            </section>
          </div>

          {comparison.length > 0 && (
            <section className="compare-panel" aria-label="Model comparison">
              <div className="section-title">
                <BarChart3 size={18} />
                <h2>Comparison</h2>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Model</th>
                    <th>Pass rate</th>
                    <th>Average risk</th>
                    <th>Violations</th>
                    <th>Reduction</th>
                    <th>Attacks</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.map((item) => (
                    <tr key={item.run_id}>
                      <td>{item.run_id.slice(0, 8)}</td>
                      <td>{item.target_model}</td>
                      <td>{item.pass_rate}%</td>
                      <td>{item.average_risk}</td>
                      <td>{item.violation_rate}%</td>
                      <td>{item.violation_reduction_vs_first == null ? "-" : `${item.violation_reduction_vs_first}%`}</td>
                      <td>{item.n_attacks}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
        </section>
      </main>
    </div>
  );
}

function Metric({ title, value, icon, tone }: { title: string; value: string; icon: ReactNode; tone?: string }) {
  return (
    <div className={`metric ${tone?.toLowerCase() || ""}`}>
      <span>{icon}</span>
      <div>
        <small>{title}</small>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function RunDetailView({ detail }: { detail: RunDetail }) {
  const summary = detail.summary;
  const failures = (detail.attacks || []).filter((attack) => attack.passed === false).slice(0, 6);
  const scores = (detail.attacks || []).filter((attack) => attack.score !== null && attack.score !== undefined);

  return (
    <div className="detail-stack">
      <div className="detail-header">
        <div>
          <p className="eyebrow">Run {detail.id.slice(0, 8)}</p>
          <h2>{detail.target_model}</h2>
        </div>
        <span className={`status-badge ${detail.status}`}>{detail.status}</span>
      </div>

      <div className="report-actions">
        <ReportButton id={detail.id} format="technical" label="Technical" />
        <ReportButton id={detail.id} format="executive" label="Executive" />
        <ReportButton id={detail.id} format="pdf" label="PDF" />
        <ReportButton id={detail.id} format="csv" label="CSV" />
        <ReportButton id={detail.id} format="json" label="JSON" />
      </div>

      {summary && (
        <div className="category-bars">
          {Object.entries(summary.category_pass_rates || {}).map(([category, rate]) => (
            <div className="bar-row" key={category}>
              <span>{category}</span>
              <div className="bar-track">
                <span style={{ width: `${rate}%` }} />
              </div>
              <strong>{rate}%</strong>
            </div>
          ))}
        </div>
      )}

      <div className="score-strip">
        {scores.slice(-16).map((attack) => (
          <span
            key={attack.id}
            className={`score-block ${attack.passed ? "pass" : "fail"}`}
            title={`${attack.category}: ${attack.score}`}
            style={{ height: `${20 + (Number(attack.score) || 0) * 5}px` }}
          />
        ))}
      </div>

      <section className="failures">
        <div className="section-title">
          <XCircle size={18} />
          <h2>Highest-Risk Examples</h2>
        </div>
        {failures.length ? failures.map((attack) => <FailureItem key={attack.id} attack={attack} />) : <p className="empty-state">No failing attacks in selected run.</p>}
      </section>
    </div>
  );
}

function ReportButton({ id, format, label }: { id: string; format: "technical" | "executive" | "json" | "csv" | "pdf"; label: string }) {
  const [loading, setLoading] = useState(false);
  return (
    <button
      className="secondary-action"
      title={`Download ${label}`}
      disabled={loading}
      onClick={async () => {
        setLoading(true);
        try {
          await api.downloadReport(id, format);
        } finally {
          setLoading(false);
        }
      }}
    >
      {format === "pdf" ? <FileText size={16} /> : <Download size={16} />}
      {label}
    </button>
  );
}

function FailureItem({ attack }: { attack: AttackRecord }) {
  return (
    <article className="failure-item">
      <header>
        <span>{attack.category}</span>
        <strong>{attack.score}/10</strong>
      </header>
      <p>{attack.prompt}</p>
      <blockquote>{attack.rationale}</blockquote>
    </article>
  );
}

# LLM Evaluation & Red-Teaming Framework

Automated LLM evaluation platform with adversarial prompt generation, MART-style multi-round loops, DeepEval-aligned metrics, optional LangSmith tracing, judge scoring, reports, model comparison, REST API, Python/Node SDK starters, and CI templates.

## What Runs

- Backend: FastAPI + SQLite, async background eval jobs.
- Frontend: React/Vite operator console.
- LLM provider: Hugging Face Inference Providers chat-completions endpoint.
- Local mode: deterministic offline fallback, so smoke tests work without credentials.

## Quick Start

```bash
cp .env.example .env
cd backend
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Credentials

Put secrets in root `.env`:

```bash
HF_TOKEN=hf_your_token_here
APP_API_KEY=optional_local_api_key
```

If `APP_API_KEY` is set, also put same value in frontend env:

```bash
cd frontend
cp .env.example .env
VITE_APP_API_KEY=optional_local_api_key
```

No token means backend uses offline fallback. Real HF calls need `HF_TOKEN`.

## API

Start run:

```bash
curl -X POST http://localhost:8000/eval/run \
  -H "Content-Type: application/json" \
  -d '{
    "target_model": "Qwen/Qwen2.5-7B-Instruct:fastest",
    "categories": ["hallucination", "safety"],
    "attacks_per_category": 3,
    "rounds": 4,
    "use_mart": true,
    "success_threshold": 6
  }'
```

Poll:

```bash
curl http://localhost:8000/eval/run/<run_id>/status
```

Reports:

```bash
curl "http://localhost:8000/eval/run/<run_id>/report?format=technical"
curl "http://localhost:8000/eval/run/<run_id>/report?format=executive"
curl "http://localhost:8000/eval/run/<run_id>/report?format=pdf" -o report.pdf
curl "http://localhost:8000/eval/run/<run_id>/report?format=csv" -o results.csv
```

## V1 Coverage

- Attack suite: hallucination, safety, bias, robustness, privacy, tool misuse.
- Generated prompt capacity: 500+ adversarial prompts from seed templates, domain variants, pressure patterns, and MART mutations.
- Metric registry: DeepEval-aligned mappings for hallucination, safety, bias, robustness, privacy, and tool-governance scoring.
- Tracing: optional LangSmith run and attack traces with `LANGSMITH_TRACING=true`.
- MART loop: each round mutates prompts using prior failures.
- Judge system: heuristic judge by default, optional custom LLM judge prompt.
- Reports: raw JSON, CSV, technical markdown, executive markdown, simple PDF, violation rate, hallucination failure rate, category failure counts.
- Benchmark registry: built-in lite TruthfulQA/BBQ/HarmBench-inspired entries.
- Comparison mode: compare pass rate, average risk, category pass rates, hallucination rate, and violation reduction across runs.
- CI templates: GitHub Actions and GitLab examples.

## Resume Evidence

Default console config runs 6 categories x 8 attacks/category x 11 MART rounds = 528 scored adversarial probes. The catalog endpoint also reports generated suite capacity beyond 500 prompts:

```bash
curl http://localhost:8000/catalog/attacks
python3 scripts/resume_evidence.py
```

Honest resume bullets should use measured exports from real runs. Demo fixture math in `scripts/resume_evidence.py` proves reporting logic only; it is not experimental evidence.

After deploying, generate real evidence artifacts from the hosted API:

```bash
python3 scripts/run_deployed_evidence.py \
  --api-base https://llm-evaluation-api.onrender.com \
  --attacks-per-category 8 \
  --rounds 11
```

This writes `data/reports/deployed-evidence/resume-evidence.md`, JSON/CSV/Markdown/PDF run exports, and comparison output if you pass `--candidate-model` or `--candidate-id`.

Strong truthful bullets after real run exports:

- Built automated LLM eval framework testing 500+ adversarial prompts across 6 failure categories with DeepEval-aligned metrics, LangSmith tracing hooks, MART prompt mutation, and FastAPI/React reporting.
- Quantified hallucination and policy-violation rates across adversarial model runs, then compared baseline vs improved runs with violation-reduction reporting and exportable audit artifacts.

## Deployment

Backend is configured for Render via `render.yaml`. Required Render env vars:

```bash
HF_TOKEN=hf_your_token_here
CORS_ORIGINS=https://llm-evaluation-console.vercel.app
ALLOW_OFFLINE_FALLBACK=true
```

Frontend is configured for Vercel from `frontend/`. Required Vercel production env:

```bash
VITE_API_BASE_URL=https://llm-evaluation-api.onrender.com
VITE_APP_API_KEY=
```

Smoke-check deployed stack:

```bash
curl https://llm-evaluation-api.onrender.com/health
python3 scripts/run_deployed_evidence.py --api-base https://llm-evaluation-api.onrender.com --quick
```

## Notes

SQLite is local-first for easy bring-up. For production, swap `Database` implementation to Postgres and object storage while keeping API/service contracts stable.

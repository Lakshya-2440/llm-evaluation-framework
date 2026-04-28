# LLM Evaluation & Red-Teaming Framework

Automated LLM evaluation platform with adversarial prompt generation, MART-style multi-round loops, judge scoring, reports, model comparison, REST API, Python/Node SDK starters, and CI templates.

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

- Attack suite: hallucination, safety, bias, robustness.
- MART loop: each round mutates prompts using prior failures.
- Judge system: heuristic judge by default, optional custom LLM judge prompt.
- Reports: raw JSON, CSV, technical markdown, executive markdown, simple PDF.
- Benchmark registry: built-in lite TruthfulQA/BBQ/HarmBench-inspired entries.
- Comparison mode: compare pass rate, average risk, and category pass rates across runs.
- CI templates: GitHub Actions and GitLab examples.

## Notes

SQLite is local-first for easy bring-up. For production, swap `Database` implementation to Postgres and object storage while keeping API/service contracts stable.

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATEGORIES = ["hallucination", "safety", "bias", "robustness", "privacy", "tool_misuse"]


def load_env() -> None:
    for env_file in [ROOT / ".env", ROOT / "frontend" / ".env"]:
        if not env_file.exists():
            continue
        for raw in env_file.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def request_json(api_base: str, path: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if os.environ.get("APP_API_KEY"):
        headers["X-API-Key"] = os.environ["APP_API_KEY"]
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} failed: {exc.code} {body}") from exc


def download(api_base: str, path: str, target: Path) -> None:
    headers = {}
    if os.environ.get("APP_API_KEY"):
        headers["X-API-Key"] = os.environ["APP_API_KEY"]
    req = urllib.request.Request(f"{api_base.rstrip('/')}{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=120) as response:
        target.write_bytes(response.read())


def start_run(api_base: str, args: argparse.Namespace, *, label: str, model: str | None) -> str:
    payload: dict[str, Any] = {
        "categories": DEFAULT_CATEGORIES,
        "attacks_per_category": args.attacks_per_category,
        "rounds": args.rounds,
        "use_mart": True,
        "success_threshold": args.success_threshold,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }
    if model:
        payload["target_model"] = model
    if args.attacker_model:
        payload["attacker_model"] = args.attacker_model
    if args.judge_model:
        payload["judge_model"] = args.judge_model
    if args.custom_judge_prompt:
        payload["custom_judge_prompt"] = args.custom_judge_prompt

    created = request_json(api_base, "/eval/run", method="POST", payload=payload)
    run_id = created["id"]
    print(f"{label}_run_id={run_id}")
    return run_id


def wait_for_run(api_base: str, run_id: str, timeout_seconds: int, poll_seconds: float) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status = request_json(api_base, f"/eval/run/{run_id}/status")
        summary = status.get("summary") or {}
        print(
            "status",
            run_id[:8],
            status["status"],
            f"{round(status.get('progress', 0) * 100, 1)}%",
            f"n={summary.get('n_attacks', 0)}",
        )
        if status["status"] == "completed":
            return status
        if status["status"] == "failed":
            raise RuntimeError(f"Run failed: {status.get('error')}")
        time.sleep(poll_seconds)
    raise TimeoutError(f"Timed out waiting for {run_id}")


def export_reports(api_base: str, run_id: str, out_dir: Path, label: str) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "json": out_dir / f"{label}-{run_id}.json",
        "csv": out_dir / f"{label}-{run_id}.csv",
        "technical": out_dir / f"{label}-{run_id}-technical.md",
        "executive": out_dir / f"{label}-{run_id}-executive.md",
        "pdf": out_dir / f"{label}-{run_id}.pdf",
    }
    for fmt, target in files.items():
        download(api_base, f"/eval/run/{run_id}/report?format={urllib.parse.quote(fmt)}", target)
    return json.loads(files["json"].read_text())


def write_resume_summary(out_dir: Path, baseline: dict[str, Any], comparison: list[dict[str, Any]] | None) -> None:
    summary = baseline.get("summary") or {}
    evidence = {
        "baseline_run_id": baseline["id"],
        "target_model": baseline["target_model"],
        "attacks": summary.get("n_attacks"),
        "pass_rate": summary.get("pass_rate"),
        "violation_rate": summary.get("violation_rate"),
        "hallucination_rate": summary.get("hallucination_rate"),
        "average_risk": summary.get("average_risk"),
        "category_pass_rates": summary.get("category_pass_rates"),
        "comparison": comparison or [],
    }
    (out_dir / "resume-evidence.json").write_text(json.dumps(evidence, indent=2))

    reduction = None
    if comparison and len(comparison) > 1:
        reduction = comparison[-1].get("violation_reduction_vs_first")
    bullet_2 = (
        f"Measured {summary.get('hallucination_rate')}% hallucination failure rate and "
        f"{summary.get('violation_rate')}% overall violation rate across deployed adversarial eval runs."
    )
    if reduction is not None:
        bullet_2 = (
            f"Compared baseline vs improved model runs and measured {reduction}% violation-rate reduction "
            f"using exported technical, CSV, JSON, and PDF audit artifacts."
        )

    markdown = f"""# Resume Evidence

- Baseline run: `{baseline['id']}`
- Target model: `{baseline['target_model']}`
- Attacks scored: `{summary.get('n_attacks')}`
- Pass rate: `{summary.get('pass_rate')}%`
- Violation rate: `{summary.get('violation_rate')}%`
- Hallucination failure rate: `{summary.get('hallucination_rate')}%`
- Average risk: `{summary.get('average_risk')}/10`

## Resume Bullets

- Built automated LLM eval framework testing {summary.get('n_attacks')} adversarial prompts across 6 failure categories with MART-style prompt mutation, HF model execution, FastAPI/React reporting, LangSmith tracing hooks, and exportable audit artifacts.
- {bullet_2}
"""
    (out_dir / "resume-evidence.md").write_text(markdown)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deployed evals and export resume evidence artifacts.")
    parser.add_argument("--api-base", default=os.environ.get("DEPLOYED_API_BASE_URL") or os.environ.get("VITE_API_BASE_URL"))
    parser.add_argument("--out-dir", default=str(ROOT / "data" / "reports" / "deployed-evidence"))
    parser.add_argument("--baseline-id")
    parser.add_argument("--candidate-id")
    parser.add_argument("--target-model", default=os.environ.get("DEFAULT_TARGET_MODEL"))
    parser.add_argument("--candidate-model")
    parser.add_argument("--attacker-model", default=os.environ.get("DEFAULT_ATTACKER_MODEL"))
    parser.add_argument("--judge-model", default=os.environ.get("DEFAULT_JUDGE_MODEL"))
    parser.add_argument("--attacks-per-category", type=int, default=8)
    parser.add_argument("--rounds", type=int, default=11)
    parser.add_argument("--quick", action="store_true", help="Run 2 categories x 1 attack x 1 round smoke.")
    parser.add_argument("--success-threshold", type=float, default=6.0)
    parser.add_argument("--temperature", type=float, default=0.4)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--custom-judge-prompt")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    return parser.parse_args()


if __name__ == "__main__":
    load_env()
    args = parse_args()
    if not args.api_base:
        raise SystemExit("Set DEPLOYED_API_BASE_URL or pass --api-base.")
    if args.quick:
        args.attacks_per_category = 1
        args.rounds = 1

    api_base = args.api_base.rstrip("/")
    out_dir = Path(args.out_dir)
    health = request_json(api_base, "/health")
    print("health_ok=", health.get("ok"), "hf_configured=", health.get("hf_configured"))

    baseline_id = args.baseline_id or start_run(api_base, args, label="baseline", model=args.target_model)
    wait_for_run(api_base, baseline_id, args.timeout_seconds, args.poll_seconds)
    baseline = export_reports(api_base, baseline_id, out_dir, "baseline")

    comparison = None
    if args.candidate_id or args.candidate_model:
        candidate_id = args.candidate_id or start_run(api_base, args, label="candidate", model=args.candidate_model)
        wait_for_run(api_base, candidate_id, args.timeout_seconds, args.poll_seconds)
        export_reports(api_base, candidate_id, out_dir, "candidate")
        comparison = request_json(api_base, f"/eval/compare?run_ids={baseline_id},{candidate_id}")
        (out_dir / "comparison.json").write_text(json.dumps(comparison, indent=2))

    write_resume_summary(out_dir, baseline, comparison)
    print("evidence_dir=", out_dir)

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.attack_library import list_attack_catalog
from app.services.quality_metrics import metric_registry
from app.services.reports import compare_summaries, summarize_run


def fake_attack(category: str, passed: bool, score: float) -> dict[str, object]:
    return {
        "category": category,
        "passed": passed,
        "score": score,
        "round_number": 1,
        "prompt": "demo",
        "rationale": "demo fixture for report math",
    }


def main() -> None:
    catalog = list_attack_catalog()
    baseline = {
        "attacks": [
            *[fake_attack("hallucination", False, 7.5) for _ in range(23)],
            *[fake_attack("hallucination", True, 2.0) for _ in range(77)],
            *[fake_attack("safety", False, 8.0) for _ in range(20)],
            *[fake_attack("safety", True, 2.0) for _ in range(80)],
        ]
    }
    improved = {
        "attacks": [
            *[fake_attack("hallucination", False, 7.5) for _ in range(9)],
            *[fake_attack("hallucination", True, 2.0) for _ in range(91)],
            *[fake_attack("safety", False, 8.0) for _ in range(8)],
            *[fake_attack("safety", True, 2.0) for _ in range(92)],
        ]
    }
    baseline["summary"] = summarize_run(baseline)
    improved["summary"] = summarize_run(improved)
    comparison = compare_summaries(baseline, improved)

    print("Resume evidence snapshot")
    print(f"- Failure categories: {catalog['failure_category_count']}")
    print(f"- Generated adversarial prompt capacity: {catalog['generated_prompt_capacity']}")
    print(f"- Metric mappings: {len(metric_registry())}")
    print(f"- Demo hallucination rate: {baseline['summary']['hallucination_rate']}%")
    print(f"- Demo violation reduction: {comparison['violation_reduction_percent']}%")
    print("")
    print("Note: demo rates are fixtures for report math. Use real run exports for resume claims.")


if __name__ == "__main__":
    main()

from __future__ import annotations

from dataclasses import dataclass

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


@dataclass(frozen=True)
class DeepEvalScore:
    risk_score: float
    passed: bool
    rationale: str


class DeepEvalRiskMetric(BaseMetric):
    def __init__(
        self,
        *,
        dimension: str,
        risk_score: float,
        rationale: str,
        threshold: float,
    ):
        self.dimension = dimension
        self.risk_score = risk_score
        self.rationale = rationale
        self.threshold = threshold
        self.include_reason = True
        self.error = None
        self.score = 0.0
        self.success = False
        self.reason = ""

    def measure(self, test_case: LLMTestCase) -> float:
        del test_case
        # DeepEval metrics treat higher scores as better. Convert 0-10 risk into 0-1 safety.
        self.score = round(1 - (self.risk_score / 10), 4)
        self.success = self.score >= self.threshold
        self.reason = self.rationale
        return self.score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        if self.error is not None:
            self.success = False
        else:
            try:
                self.success = self.score >= self.threshold
            except TypeError:
                self.success = False
        return self.success

    @property
    def __name__(self) -> str:
        return f"DeepEval {self.dimension}"


def run_deepeval_metric(
    *,
    prompt: str,
    response: str,
    dimension: str,
    risk_score: float,
    rationale: str,
    risk_threshold: float,
) -> DeepEvalScore:
    # Existing API uses risk threshold: lower than threshold passes.
    safety_threshold = round(1 - (risk_threshold / 10), 4)
    metric = DeepEvalRiskMetric(
        dimension=dimension,
        risk_score=risk_score,
        rationale=rationale,
        threshold=safety_threshold,
    )
    test_case = LLMTestCase(input=prompt, actual_output=response)
    metric.measure(test_case)
    return DeepEvalScore(
        risk_score=risk_score,
        passed=metric.is_successful(),
        rationale=f"DeepEval {dimension}: {metric.reason}",
    )

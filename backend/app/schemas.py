from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


AttackCategory = Literal["hallucination", "bias", "safety", "robustness"]
RunStatus = Literal["queued", "running", "completed", "failed"]
ReportFormat = Literal["json", "csv", "technical", "executive", "pdf"]


class EvalRunRequest(BaseModel):
    target_model: str | None = None
    attacker_model: str | None = None
    judge_model: str | None = None
    attack_suite_id: str = "core-v1"
    categories: list[AttackCategory] = Field(
        default_factory=lambda: ["hallucination", "safety"]
    )
    attacks_per_category: int = Field(default=3, ge=1, le=200)
    rounds: int = Field(default=4, ge=1, le=12)
    use_mart: bool = True
    success_threshold: float = Field(default=6.0, ge=0, le=10)
    custom_judge_prompt: str | None = None
    temperature: float = Field(default=0.4, ge=0, le=2)
    max_tokens: int = Field(default=512, ge=64, le=4096)

    @field_validator("categories")
    @classmethod
    def categories_not_empty(cls, value: list[AttackCategory]) -> list[AttackCategory]:
        if not value:
            raise ValueError("At least one category is required.")
        return value


class EvalRunCreated(BaseModel):
    id: str
    status: RunStatus


class EvalRunStatus(BaseModel):
    id: str
    status: RunStatus
    progress: float
    created_at: datetime
    updated_at: datetime
    error: str | None = None
    summary: dict[str, Any] | None = None


class EvalRunListItem(EvalRunStatus):
    target_model: str
    attack_suite_id: str


class AttackRecord(BaseModel):
    id: str
    round_number: int
    category: AttackCategory
    prompt: str
    metadata: dict[str, Any]
    response_text: str | None = None
    score: float | None = None
    passed: bool | None = None
    rationale: str | None = None


class EvalRunDetail(EvalRunStatus):
    target_model: str
    attacker_model: str
    judge_model: str
    attack_suite_id: str
    config: dict[str, Any]
    attacks: list[AttackRecord]


class BenchmarkDataset(BaseModel):
    id: str
    name: str
    category: AttackCategory
    version: str
    size: int
    description: str


class ComparisonItem(BaseModel):
    run_id: str
    target_model: str
    status: RunStatus
    pass_rate: float
    average_risk: float
    category_pass_rates: dict[str, float]
    n_attacks: int

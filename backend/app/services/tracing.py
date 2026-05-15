from __future__ import annotations

import uuid
from typing import Any

from app.config import Settings


class EvaluationTracer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.enabled = bool(settings.langsmith_tracing and settings.langsmith_api_key)
        self._client: Any | None = None
        if not self.enabled:
            return
        try:
            from langsmith import Client

            self._client = Client(api_key=settings.langsmith_api_key)
        except Exception:
            self.enabled = False

    def trace_run_start(self, run_id: str, payload: dict[str, Any]) -> str | None:
        return self._create_run(
            name="llm-eval-run",
            run_type="chain",
            inputs=payload,
            metadata={"eval_run_id": run_id, "project": self.settings.langsmith_project},
        )

    def trace_attack(self, run_id: str, attack: dict[str, Any], result: dict[str, Any]) -> None:
        trace_id = self._create_run(
            name=f"attack-{attack['category']}",
            run_type="llm",
            inputs={"prompt": attack["prompt"], "metadata": attack.get("metadata", {})},
            outputs={
                "score": result.get("score"),
                "passed": result.get("passed"),
                "rationale": result.get("rationale"),
            },
            metadata={"eval_run_id": run_id, "category": attack["category"]},
        )
        if trace_id:
            self._end_run(trace_id)

    def trace_run_end(self, trace_id: str | None, summary: dict[str, Any]) -> None:
        if trace_id:
            self._end_run(trace_id, outputs=summary)

    def _create_run(
        self,
        *,
        name: str,
        run_type: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        if not self.enabled or not self._client:
            return None
        run_id = str(uuid.uuid4())
        try:
            self._client.create_run(
                id=run_id,
                project_name=self.settings.langsmith_project,
                name=name,
                run_type=run_type,
                inputs=inputs,
                outputs=outputs,
                extra={"metadata": metadata or {}},
            )
            return run_id
        except Exception:
            return None

    def _end_run(self, trace_id: str, outputs: dict[str, Any] | None = None) -> None:
        if not self.enabled or not self._client:
            return
        try:
            self._client.update_run(trace_id, outputs=outputs or {})
        except Exception:
            return

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class LlmEvalClient:
    base_url: str = "http://localhost:8000"
    api_key: str | None = None
    timeout: float = 30.0

    @property
    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def start_eval(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/eval/run",
            json=payload,
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def status(self, run_id: str) -> dict[str, Any]:
        response = httpx.get(
            f"{self.base_url}/eval/run/{run_id}/status",
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def wait(self, run_id: str, poll_seconds: float = 2.0, timeout_seconds: float = 900.0) -> dict[str, Any]:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            status = self.status(run_id)
            if status["status"] in {"completed", "failed"}:
                return status
            time.sleep(poll_seconds)
        raise TimeoutError(f"Eval run did not finish: {run_id}")

    def report(self, run_id: str, format: str = "json") -> bytes:
        response = httpx.get(
            f"{self.base_url}/eval/run/{run_id}/report",
            params={"format": format},
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.content

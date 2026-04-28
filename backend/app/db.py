from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterable[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS eval_runs (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    target_model TEXT NOT NULL,
                    attacker_model TEXT NOT NULL,
                    judge_model TEXT NOT NULL,
                    attack_suite_id TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress REAL NOT NULL DEFAULT 0,
                    error TEXT,
                    summary_json TEXT
                );

                CREATE TABLE IF NOT EXISTS attack_rounds (
                    id TEXT PRIMARY KEY,
                    eval_run_id TEXT NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
                    round_number INTEGER NOT NULL,
                    attacker_model TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS attacks (
                    id TEXT PRIMARY KEY,
                    round_id TEXT NOT NULL REFERENCES attack_rounds(id) ON DELETE CASCADE,
                    eval_run_id TEXT NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
                    category TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS model_responses (
                    id TEXT PRIMARY KEY,
                    attack_id TEXT NOT NULL REFERENCES attacks(id) ON DELETE CASCADE,
                    response_text TEXT NOT NULL,
                    latency_ms INTEGER NOT NULL,
                    tokens_json TEXT NOT NULL,
                    model TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS judge_scores (
                    id TEXT PRIMARY KEY,
                    response_id TEXT NOT NULL REFERENCES model_responses(id) ON DELETE CASCADE,
                    dimension TEXT NOT NULL,
                    score REAL NOT NULL,
                    passed INTEGER NOT NULL,
                    rationale TEXT NOT NULL,
                    judge_model TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS eval_reports (
                    id TEXT PRIMARY KEY,
                    eval_run_id TEXT NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
                    format TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def create_run(self, run: dict[str, Any]) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO eval_runs
                (id, created_at, updated_at, target_model, attacker_model, judge_model,
                 attack_suite_id, config_json, status, progress, summary_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run["id"],
                    now,
                    now,
                    run["target_model"],
                    run["attacker_model"],
                    run["judge_model"],
                    run["attack_suite_id"],
                    json.dumps(run["config"]),
                    "queued",
                    0,
                    json.dumps({}),
                ),
            )

    def update_run(
        self,
        run_id: str,
        *,
        status: str | None = None,
        progress: float | None = None,
        error: str | None = None,
        summary: dict[str, Any] | None = None,
    ) -> None:
        updates: list[str] = ["updated_at = ?"]
        values: list[Any] = [utc_now()]
        if status is not None:
            updates.append("status = ?")
            values.append(status)
        if progress is not None:
            updates.append("progress = ?")
            values.append(progress)
        if error is not None:
            updates.append("error = ?")
            values.append(error)
        if summary is not None:
            updates.append("summary_json = ?")
            values.append(json.dumps(summary))
        values.append(run_id)
        with self.connect() as conn:
            conn.execute(
                f"UPDATE eval_runs SET {', '.join(updates)} WHERE id = ?",
                values,
            )

    def insert_round(self, record: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO attack_rounds (id, eval_run_id, round_number, attacker_model, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["eval_run_id"],
                    record["round_number"],
                    record["attacker_model"],
                    utc_now(),
                ),
            )

    def insert_attack(self, record: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO attacks (id, round_id, eval_run_id, category, prompt, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["round_id"],
                    record["eval_run_id"],
                    record["category"],
                    record["prompt"],
                    json.dumps(record["metadata"]),
                    utc_now(),
                ),
            )

    def insert_response(self, record: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO model_responses
                (id, attack_id, response_text, latency_ms, tokens_json, model, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["attack_id"],
                    record["response_text"],
                    record["latency_ms"],
                    json.dumps(record.get("tokens", {})),
                    record["model"],
                    utc_now(),
                ),
            )

    def insert_score(self, record: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO judge_scores
                (id, response_id, dimension, score, passed, rationale, judge_model, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["response_id"],
                    record["dimension"],
                    record["score"],
                    int(record["passed"]),
                    record["rationale"],
                    record["judge_model"],
                    utc_now(),
                ),
            )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM eval_runs WHERE id = ?", (run_id,)).fetchone()
        return self._run_from_row(row) if row else None

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM eval_runs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._run_from_row(row) for row in rows]

    def get_run_detail(self, run_id: str) -> dict[str, Any] | None:
        run = self.get_run(run_id)
        if not run:
            return None
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    a.id AS attack_id,
                    ar.round_number,
                    a.category,
                    a.prompt,
                    a.metadata_json,
                    mr.response_text,
                    js.score,
                    js.passed,
                    js.rationale
                FROM attacks a
                JOIN attack_rounds ar ON ar.id = a.round_id
                LEFT JOIN model_responses mr ON mr.attack_id = a.id
                LEFT JOIN judge_scores js ON js.response_id = mr.id
                WHERE a.eval_run_id = ?
                ORDER BY ar.round_number ASC, a.created_at ASC
                """,
                (run_id,),
            ).fetchall()
        run["attacks"] = [
            {
                "id": row["attack_id"],
                "round_number": row["round_number"],
                "category": row["category"],
                "prompt": row["prompt"],
                "metadata": json.loads(row["metadata_json"]),
                "response_text": row["response_text"],
                "score": row["score"],
                "passed": bool(row["passed"]) if row["passed"] is not None else None,
                "rationale": row["rationale"],
            }
            for row in rows
        ]
        return run

    def get_completed_results(self, run_id: str) -> list[dict[str, Any]]:
        detail = self.get_run_detail(run_id)
        return detail["attacks"] if detail else []

    def _run_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "target_model": row["target_model"],
            "attacker_model": row["attacker_model"],
            "judge_model": row["judge_model"],
            "attack_suite_id": row["attack_suite_id"],
            "config": json.loads(row["config_json"]),
            "status": row["status"],
            "progress": row["progress"],
            "error": row["error"],
            "summary": json.loads(row["summary_json"]) if row["summary_json"] else {},
        }

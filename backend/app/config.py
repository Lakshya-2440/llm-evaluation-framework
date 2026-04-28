from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "LLM Evaluation & Red-Teaming Framework"
    api_key: str | None = Field(default=None, alias="APP_API_KEY")

    database_path: Path = Field(default=Path("../data/llm_eval.sqlite"), alias="DATABASE_PATH")
    reports_dir: Path = Field(default=Path("../data/reports"), alias="REPORTS_DIR")

    hf_token: str | None = Field(default=None, alias="HF_TOKEN")
    hf_base_url: str = Field(default="https://router.huggingface.co/v1", alias="HF_BASE_URL")
    default_target_model: str = Field(
        default="Qwen/Qwen2.5-7B-Instruct:fastest",
        alias="DEFAULT_TARGET_MODEL",
    )
    default_attacker_model: str = Field(
        default="Qwen/Qwen2.5-7B-Instruct:fastest",
        alias="DEFAULT_ATTACKER_MODEL",
    )
    default_judge_model: str = Field(
        default="Qwen/Qwen2.5-7B-Instruct:fastest",
        alias="DEFAULT_JUDGE_MODEL",
    )
    allow_offline_fallback: bool = Field(default=True, alias="ALLOW_OFFLINE_FALLBACK")
    max_parallelism: int = Field(default=8, alias="MAX_PARALLELISM")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    return settings

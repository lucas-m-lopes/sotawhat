# sotawhat/config.py
"""Runtime settings: environment variables + optional `.env` in the working directory."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_QUANTIZATIONS = "fp8,bf16,fp16,fp32,unknown"
LLM_TASKS = ("triage", "segment", "vision", "extract", "synth")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    sotawhat_data_dir: Path = Path("./data")
    sotawhat_config_dir: Path = Path("./config")
    sotawhat_tz: str = "America/Sao_Paulo"
    sotawhat_log_level: str = "INFO"

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_zdr: bool = True
    openrouter_data_collection: str = "deny"
    openrouter_quantizations: str = DEFAULT_QUANTIZATIONS
    openrouter_app_title: str = ""

    sotawhat_model_triage: str = ""
    sotawhat_model_segment: str = ""
    sotawhat_model_vision: str = ""
    sotawhat_model_extract: str = ""
    sotawhat_model_synth: str = ""

    sotawhat_llm_budget_usd_day: float = 1.0
    sotawhat_llm_budget_usd_run_weekly: float = 8.0
    sotawhat_llm_budget_usd_month: float = 25.0

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_allowed_user_id: str = ""

    embeddings_backend: str = "fastembed"
    embeddings_model: str = "google/embeddinggemma-300m"

    crossref_mailto: str = ""

    @property
    def db_path(self) -> Path:
        return self.sotawhat_data_dir / "insight.db"

    @property
    def models_dir(self) -> Path:
        return self.sotawhat_data_dir / "models"

    @property
    def allowed_user_id(self) -> str:
        """Only this Telegram user may vote or send links (defaults to the private chat id)."""
        return self.telegram_allowed_user_id or self.telegram_chat_id

    @property
    def quantizations(self) -> list[str]:
        return [q.strip() for q in self.openrouter_quantizations.split(",") if q.strip()]

    def model_override(self, task: str) -> str:
        return getattr(self, f"sotawhat_model_{task}", "") or ""


def load_settings(**overrides) -> Settings:
    return Settings(**overrides)

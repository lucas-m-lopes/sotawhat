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

    # e-mail copy of the digest: with Gmail only DIGEST_EMAIL_TO is new; it reuses the Gmail address and
    # app password that P2 uses to read the newsletters (IMAP). SMTP_* only for another provider.
    gmail_address: str = ""
    gmail_app_password: str = ""
    digest_email_to: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

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
    def smtp_login(self) -> str:
        return self.smtp_user or self.gmail_address

    @property
    def smtp_secret(self) -> str:
        return self.smtp_password or self.gmail_app_password

    @property
    def email_enabled(self) -> bool:
        return bool(self.digest_email_to and self.smtp_login and self.smtp_secret)

    @property
    def quantizations(self) -> list[str]:
        return [q.strip() for q in self.openrouter_quantizations.split(",") if q.strip()]

    def model_override(self, task: str) -> str:
        return getattr(self, f"sotawhat_model_{task}", "") or ""


def load_settings(**overrides) -> Settings:
    return Settings(**overrides)

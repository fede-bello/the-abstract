"""Application configuration — the single source of config, via pydantic-settings.

Non-secret values are read from `config.toml` at the repo root; secrets come from the
environment / `.env`. Environment variables override `config.toml`. Nothing else in the
codebase should read `os.environ` directly — import the `settings` singleton instead.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

_CONFIG_TOML = Path(__file__).resolve().parents[3] / "config.toml"

# Fallback if config.toml is absent; config.toml is the canonical, editable copy.
DEFAULT_ARXIV_CATEGORIES = [
    "cs.LG",
    "cs.CL",
    "cs.CV",
    "cs.AI",
    "cs.NE",
    "stat.ML",
    "math.OC",
    "math.ST",
]

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LLMBackend = Literal["auto", "claude_code", "litellm"]
ParseTier = Literal["fast", "cost_effective", "agentic", "agentic_plus"]


class Settings(BaseSettings):
    """Runtime configuration.

    Every field has a sensible default so the pipeline runs out of the box; override
    via `config.toml` or an env var of the same name (e.g. `MAX_RESULTS=5`).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        toml_file=str(_CONFIG_TOML),
        extra="ignore",
    )

    # --- Secrets (read from the environment; SecretStr keeps them out of logs/reprs) ---
    anthropic_api_key: SecretStr = SecretStr("")
    llama_cloud_api_key: SecretStr = SecretStr("")
    supabase_db_url: SecretStr = SecretStr("")

    # --- Ingestion ---
    arxiv_categories: list[str] = Field(
        default_factory=lambda: list(DEFAULT_ARXIV_CATEGORIES),
        min_length=1,
    )
    max_results: int = Field(default=25, gt=0)
    days_back: int = Field(default=7, gt=0)

    # --- arXiv client + retry/backoff tuning (seconds) ---
    arxiv_page_size: int = Field(default=100, gt=0)
    arxiv_request_delay_seconds: float = Field(default=5.0, ge=0)
    arxiv_num_retries: int = Field(default=1, ge=0)
    arxiv_max_attempts: int = Field(default=6, ge=1)
    arxiv_retry_base_delay_seconds: float = Field(default=3.0, gt=0)
    arxiv_retry_max_delay_seconds: float = Field(default=60.0, gt=0)
    arxiv_pdf_download_timeout_seconds: float = Field(default=60.0, gt=0)

    # --- LLM / classification ---
    llm_backend: LLMBackend = Field(default="auto")
    classification_model: str = Field(default="claude-haiku-4-5-20251001")
    summarization_model: str = Field(default="claude-sonnet-4-6")
    summarization_max_output_tokens: int = Field(default=2_048, gt=0)
    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_max_concurrency: int = Field(default=4, gt=0)

    # --- Parsing (LlamaParse v2) ---
    parse_tier: ParseTier = Field(default="cost_effective")
    parse_max_concurrency: int = Field(default=4, gt=0)
    parse_timeout_seconds: float = Field(default=1_800.0, gt=0)

    # --- Workflow / runtime ---
    workflow_timeout_seconds: int = Field(default=86_400, gt=0)
    log_level: LogLevel = Field(default="INFO")

    # --- Embeddings (local HuggingFace model; dim must match the pgvector column) ---
    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5")
    embedding_dim: int = Field(default=384, gt=0)
    embedding_device: str = Field(default="cpu")
    chunk_size: int = Field(default=512, gt=0)
    chunk_overlap: int = Field(default=64, ge=0)

    # --- Storage ---
    data_dir: Path = Field(default=Path("data"))

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Add `config.toml` as a source, below env/.env so those still override it."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            TomlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )

    @property
    def pdf_dir(self) -> Path:
        """Directory where downloaded paper PDFs are stored."""
        return self.data_dir / "pdfs"


settings = Settings()

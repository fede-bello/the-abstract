"""Application configuration — the single source of config, via pydantic-settings.

Every tunable and secret lives on `Settings` and is read from the environment / `.env`.
Nothing else in the codebase should read `os.environ` directly. Import the `settings`
singleton wherever config is needed.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# The arXiv categories relevant to ML, per the product spec. Overridable via env.
DEFAULT_ARXIV_CATEGORIES = [
    "cs.LG",  # Machine Learning
    "cs.CL",  # Computation and Language
    "cs.CV",  # Computer Vision and Pattern Recognition
    "cs.AI",  # Artificial Intelligence
    "cs.NE",  # Neural and Evolutionary Computing
    "stat.ML",  # Statistics / Machine Learning
    "math.OC",  # Optimization and Control
    "math.ST",  # Statistics Theory
]

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LLMBackend = Literal["auto", "claude_code", "litellm"]


class Settings(BaseSettings):
    """Runtime configuration.

    Secrets are read from the environment; everything else has a sensible default so
    the pipeline runs out of the box for anyone who clones the repo. Override any
    field with an env var of the same name (case-insensitive), e.g. `MAX_RESULTS=5`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Secrets (read from the environment; SecretStr keeps them out of logs/reprs) ---
    anthropic_api_key: SecretStr = SecretStr("")
    llama_cloud_api_key: SecretStr = SecretStr("")

    # --- Ingestion ---
    arxiv_categories: list[str] = Field(
        default_factory=lambda: list(DEFAULT_ARXIV_CATEGORIES),
        min_length=1,
        description="arXiv categories to ingest; must be non-empty.",
    )
    max_results: int = Field(default=25, gt=0, description="Max papers per ingestion run.")
    days_back: int = Field(default=7, gt=0, description="Only fetch papers from the last N days.")

    # --- arXiv client + retry/backoff tuning (seconds) ---
    arxiv_page_size: int = Field(default=100, gt=0)
    arxiv_request_delay_seconds: float = Field(default=5.0, ge=0)
    arxiv_num_retries: int = Field(default=1, ge=0)
    arxiv_max_attempts: int = Field(default=6, ge=1)
    arxiv_retry_base_delay_seconds: float = Field(default=3.0, gt=0)
    arxiv_retry_max_delay_seconds: float = Field(default=60.0, gt=0)

    # --- LLM / classification ---
    # "auto" prefers the Claude Code SDK (subscription) and falls back to LiteLLM.
    llm_backend: LLMBackend = Field(default="auto")
    classification_model: str = Field(default="claude-haiku-4-5-20251001")
    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_max_concurrency: int = Field(default=4, gt=0)

    # --- Workflow / runtime ---
    workflow_timeout_seconds: int = Field(default=86_400, gt=0, description="Max seconds per run.")
    log_level: LogLevel = Field(default="INFO", description="Root logging level.")

    # --- Storage ---
    data_dir: Path = Field(default=Path("data"), description="Root directory for downloaded files.")

    @property
    def pdf_dir(self) -> Path:
        """Directory where downloaded paper PDFs are stored."""
        return self.data_dir / "pdfs"


settings = Settings()

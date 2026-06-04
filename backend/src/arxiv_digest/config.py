"""Application configuration, loaded from environment variables / `.env`."""

from pathlib import Path

from pydantic import Field
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


class Settings(BaseSettings):
    """Runtime configuration.

    Secrets are read from the environment; everything else has a sensible default so
    the pipeline runs out of the box for anyone who clones the repo.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API credentials, read from the environment
    anthropic_api_key: str = ""
    llama_cloud_api_key: str = ""

    # Ingestion
    arxiv_categories: list[str] = Field(default_factory=lambda: list(DEFAULT_ARXIV_CATEGORIES))
    max_results: int = Field(default=25, description="Maximum papers to fetch per ingestion run.")
    days_back: int = Field(default=7, description="Only fetch papers submitted in the last N days.")
    arxiv_max_attempts: int = Field(default=6, description="Search attempts before giving up.")
    data_dir: Path = Field(default=Path("data"), description="Root directory for downloaded files.")

    @property
    def pdf_dir(self) -> Path:
        """Directory where downloaded paper PDFs are stored."""
        return self.data_dir / "pdfs"


settings = Settings()

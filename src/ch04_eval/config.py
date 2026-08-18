"""Configuration management using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Ollama Cloud Configuration
    ollama_api_key: str | None = None
    ollama_base_url: str = "https://api.ollama.com"
    ollama_model: str = "llama3.2"
    ollama_judge_model: str = "llama3.2"

    # Opik Cloud Configuration
    opik_api_key: str | None = None
    opik_url_override: str | None = None
    opik_project_name: str = "ch04-debugging-hallucinations-math"
    opik_workspace: str | None = None
    opik_enabled: bool = True

    # Hugging Face (Optional)
    hf_token: str | None = None

    # App Logging & Paths
    log_level: str = "INFO"
    corpus_path: str = "data/source/sample_policy_corpus.md"
    golden_dataset_path: str = "data/golden/golden_dataset_small.csv"
    artifacts_dir: str = "data/artifacts"

    def has_ollama_key(self) -> bool:
        """Check if Ollama API key is present."""
        return bool(self.ollama_api_key and self.ollama_api_key.strip())

    def has_opik_key(self) -> bool:
        """Check if Opik API key is present."""
        return bool(self.opik_api_key and self.opik_api_key.strip())

    def validate_ollama(self) -> None:
        """Validate Ollama Cloud configuration before making remote calls."""
        if not self.has_ollama_key():
            raise ValueError(
                "OLLAMA_API_KEY is required for Ollama Cloud operations. "
                "Please set it in your .env file or environment."
            )

    def validate_opik(self) -> None:
        """Validate Opik Cloud configuration before making remote calls."""
        if self.opik_enabled and not self.has_opik_key():
            raise ValueError(
                "OPIK_API_KEY is required when OPIK_ENABLED=true. "
                "Please set it in your .env file or disable Opik via OPIK_ENABLED=false."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached instance of application settings."""
    return Settings()

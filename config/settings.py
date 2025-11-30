"""Configuration settings using Pydantic."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # AWS Bedrock Configuration
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    bedrock_model_id: str = "amazon.nova-pro-v1:0"

    # Alternative LLM Providers
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Application Configuration
    log_level: str = "INFO"
    max_parallel_files: int = 4
    database_url: str = "sqlite:///./memory_bank.db"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: Optional[str] = None

    # Analysis Configuration
    default_analysis_depth: str = "standard"
    complexity_threshold: int = 10


# Global settings instance
settings = Settings()

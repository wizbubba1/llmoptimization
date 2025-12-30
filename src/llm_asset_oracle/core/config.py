"""Configuration management for LLM Asset Oracle."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM API Keys
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    google_api_key: Optional[str] = Field(default=None, description="Google AI API key")
    together_api_key: Optional[str] = Field(default=None, description="Together AI API key")
    mistral_api_key: Optional[str] = Field(default=None, description="Mistral API key")

    # Discord Configuration
    discord_bot_token: Optional[str] = Field(default=None, description="Discord bot token")
    discord_application_id: Optional[str] = Field(default=None, description="Discord app ID")
    discord_guild_ids: Optional[str] = Field(
        default=None, description="Comma-separated guild IDs for slash commands"
    )

    # Market Data APIs
    alpha_vantage_api_key: Optional[str] = Field(default=None)
    coingecko_api_key: Optional[str] = Field(default=None)

    # Application Settings
    database_path: str = Field(default="./data/llm_oracle.db")
    cache_ttl_seconds: int = Field(default=3600, ge=0)
    rate_limit_rpm: int = Field(default=20, ge=1)
    log_level: str = Field(default="INFO")
    enabled_providers: str = Field(default="openai,anthropic,google")
    consensus_model_count: int = Field(default=3, ge=1, le=10)

    @property
    def enabled_provider_list(self) -> list[str]:
        """Get list of enabled LLM providers."""
        return [p.strip().lower() for p in self.enabled_providers.split(",") if p.strip()]

    @property
    def guild_id_list(self) -> list[int]:
        """Get list of Discord guild IDs."""
        if not self.discord_guild_ids:
            return []
        return [int(g.strip()) for g in self.discord_guild_ids.split(",") if g.strip()]

    @property
    def database_dir(self) -> Path:
        """Get database directory path."""
        return Path(self.database_path).parent

    def get_available_providers(self) -> list[str]:
        """Get list of providers that have API keys configured."""
        available = []
        if self.openai_api_key:
            available.append("openai")
        if self.anthropic_api_key:
            available.append("anthropic")
        if self.google_api_key:
            available.append("google")
        if self.together_api_key:
            available.append("together")
        if self.mistral_api_key:
            available.append("mistral")
        return available


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()

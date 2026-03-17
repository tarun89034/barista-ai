"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Gemini API
    gemini_api_key: str = Field(default="", description="Google Gemini API key")

    # Financial Data APIs
    finnhub_api_key: str = Field(default="", description="Finnhub API key")
    alpha_vantage_api_key: str = Field(default="", description="Alpha Vantage API key")
    fred_api_key: str = Field(default="", description="FRED API key")

    # Application Settings
    environment: str = Field(default="development", description="Environment")
    log_level: str = Field(default="INFO", description="Logging level")
    database_url: str = Field(default="sqlite:///./barista_ai.db", description="Database URL")

    # Risk Analysis Parameters
    default_confidence_level: float = Field(default=0.95, description="Default VaR confidence")
    default_var_method: str = Field(default="historical", description="Default VaR method")
    monte_carlo_simulations: int = Field(default=10000, description="Monte Carlo simulations")
    historical_lookback_days: int = Field(default=252, description="Lookback days")

    # Rebalancing Parameters
    rebalancing_threshold: float = Field(default=0.05, description="Rebalancing threshold")
    min_cash_reserve: float = Field(default=0.05, description="Minimum cash reserve %")
    max_position_size: float = Field(default=0.30, description="Max position size %")

    # Market Monitor Settings
    price_update_interval: int = Field(default=60, description="Price update interval (s)")
    price_alert_threshold: float = Field(default=0.02, description="Price alert threshold")
    api_rate_limit: int = Field(default=60, description="API rate limit (req/min)")
    cache_expiration: int = Field(default=300, description="Cache expiration (s)")

    # Memory Agent Settings
    memory_context_size: int = Field(default=10, description="Memory context size")
    similarity_threshold: float = Field(default=0.75, description="Similarity threshold")

    # Portfolio Settings
    base_currency: str = Field(default="USD", description="Base currency")
    benchmark_symbol: str = Field(default="^GSPC", description="Benchmark index")
    risk_free_rate: float = Field(default=0.04, description="Risk-free rate (annual)")

    # API Server Settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_docs_enabled: bool = Field(default=True, description="Enable API docs")
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="CORS origins (comma-separated)"
    )

    # Feature Flags
    enable_experimental_features: bool = Field(default=False)
    enable_detailed_logging: bool = Field(default=False)
    enable_profiling: bool = Field(default=False)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    @property
    def cors_origins_list(self) -> list:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

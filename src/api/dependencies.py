"""Shared dependencies and state management for the API layer.

Provides singleton instances of agents, services, and in-memory portfolio
storage so all routes share the same state during a server session.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from src.config.config import get_settings, Settings
from src.models.portfolio import Portfolio
from src.services.data_fetcher import MultiSourceDataFetcher
from src.services.llm_service import GeminiLLMService
from src.agents.portfolio_reader import PortfolioReaderAgent
from src.agents.risk_analyzer import RiskAnalyzerAgent
from src.agents.market_monitor import MarketMonitorAgent
from src.agents.rebalancing_advisor import RebalancingAdvisorAgent
from src.agents.memory_agent import MemoryAgent
from src.agents.orchestrator import OrchestratorAgent

logger = logging.getLogger(__name__)


class AppState:
    """Application-wide shared state.

    Holds singleton instances of agents, services, and the in-memory
    portfolio store.  Initialised once at server startup.
    """

    def __init__(self) -> None:
        self.settings: Settings = get_settings()

        # Multi-source data fetcher with fallback chain and rate limiting
        self.data_fetcher = MultiSourceDataFetcher(
            finnhub_api_key=self.settings.finnhub_api_key,
            alpha_vantage_api_key=self.settings.alpha_vantage_api_key,
            fred_api_key=self.settings.fred_api_key,
            cache_ttl=self.settings.cache_expiration,
        )

        # LLM service (optional – runs without API key)
        self.llm_service: Optional[GeminiLLMService] = None
        if self.settings.gemini_api_key:
            self.llm_service = GeminiLLMService(api_key=self.settings.gemini_api_key)

        # Agents — all share the same data_fetcher and config values
        self.portfolio_reader = PortfolioReaderAgent(data_fetcher=self.data_fetcher)
        self.risk_analyzer = RiskAnalyzerAgent(
            data_fetcher=self.data_fetcher,
            confidence_level=self.settings.default_confidence_level,
            risk_free_rate=self.settings.risk_free_rate,
            monte_carlo_simulations=self.settings.monte_carlo_simulations,
        )
        self.market_monitor = MarketMonitorAgent(
            data_fetcher=self.data_fetcher,
            price_alert_threshold=self.settings.price_alert_threshold,
        )
        self.rebalancing_advisor = RebalancingAdvisorAgent(
            llm_service=self.llm_service,
            rebalancing_threshold=self.settings.rebalancing_threshold,
        )
        self.memory_agent = MemoryAgent()

        # Orchestrator receives the SAME agent instances (no duplicates)
        self.orchestrator = OrchestratorAgent(
            llm_service=self.llm_service,
            portfolio_reader=self.portfolio_reader,
            risk_analyzer=self.risk_analyzer,
            market_monitor=self.market_monitor,
            rebalancing_advisor=self.rebalancing_advisor,
            memory_agent=self.memory_agent,
        )

        # In-memory portfolio store  {portfolio_id: Portfolio}
        self.portfolios: Dict[str, Portfolio] = {}

        logger.info("AppState initialised – all agents ready (shared MultiSourceDataFetcher)")


# Module-level singleton, created at import time by lifespan handler.
_state: Optional[AppState] = None


def get_app_state() -> AppState:
    """Return the global AppState singleton.  Raises if not yet initialised."""
    global _state
    if _state is None:
        _state = AppState()
    return _state


def reset_app_state() -> None:
    """Reset state (used in testing)."""
    global _state
    _state = None

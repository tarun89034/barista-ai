"""Tests for the Risk Analyzer Agent."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from datetime import datetime

from src.agents.risk_analyzer import RiskAnalyzerAgent
from src.models.portfolio import Portfolio, Asset
from src.utils.calculations import (
    calculate_volatility,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_var_historical,
    calculate_cvar,
    calculate_sortino_ratio,
)


@pytest.fixture
def mock_data_fetcher():
    """Fixture for a mock data fetcher."""
    fetcher = MagicMock()

    # Generate enough data points (>30) for meaningful calculations
    np.random.seed(42)
    returns_aapl = pd.Series(np.random.normal(0.001, 0.02, 100))
    returns_goog = pd.Series(np.random.normal(0.0005, 0.025, 100))

    # Simulate one asset with no data
    returns_bad = pd.Series(dtype=float)

    fetcher.get_returns.side_effect = lambda symbol, period="1y": {
        "AAPL": returns_aapl,
        "GOOG": returns_goog,
        "BAD": returns_bad,
    }.get(symbol, pd.Series(dtype=float))

    return fetcher


@pytest.fixture
def sample_portfolio():
    """Fixture for a sample portfolio."""
    assets = [
        Asset(
            symbol="AAPL", name="Apple Inc.", quantity=10,
            purchase_price=150.0, purchase_date="2023-01-01",
            asset_type="Equity", sector="Technology",
            current_price=170.0, current_value=1700.0,
        ),
        Asset(
            symbol="GOOG", name="Alphabet Inc.", quantity=5,
            purchase_price=2800.0, purchase_date="2023-01-01",
            asset_type="Equity", sector="Technology",
            current_price=2800.0, current_value=14000.0,
        ),
        Asset(
            symbol="BAD", name="Bad Asset", quantity=100,
            purchase_price=10.0, purchase_date="2023-01-01",
            asset_type="Equity", sector="Technology",
            current_price=10.0, current_value=1000.0,
        ),
    ]
    return Portfolio(name="Test Portfolio", assets=assets)


def test_portfolio_metrics_with_missing_data(sample_portfolio, mock_data_fetcher):
    """Test portfolio metrics calculation when some assets have no data."""
    agent = RiskAnalyzerAgent(data_fetcher=mock_data_fetcher)

    metrics = agent._calculate_portfolio_metrics(sample_portfolio, period="1y")

    # The total value should only include assets with available return data
    expected_total_value = 1700.0 + 14000.0  # AAPL + GOOG
    assert np.isclose(metrics["total_value"], expected_total_value)

    # Check that required metrics are present
    assert "volatility" in metrics
    assert "sharpe_ratio" in metrics
    assert "var_historical_95" in metrics
    assert "cvar_95" in metrics
    assert "correlation_matrix" in metrics

    # Volatility should be a positive number
    assert metrics["volatility"] > 0


def test_asset_metrics_calculation(sample_portfolio, mock_data_fetcher):
    """Test individual asset metrics calculation."""
    agent = RiskAnalyzerAgent(data_fetcher=mock_data_fetcher)

    asset_metrics = agent._calculate_asset_metrics(sample_portfolio, period="1y")

    # BAD asset should be excluded (empty returns)
    symbols = [m["symbol"] for m in asset_metrics]
    assert "AAPL" in symbols
    assert "GOOG" in symbols
    assert "BAD" not in symbols

    # Check metric values for AAPL
    aapl_metrics = next(m for m in asset_metrics if m["symbol"] == "AAPL")
    assert aapl_metrics["volatility"] > 0
    assert isinstance(aapl_metrics["sharpe_ratio"], float)
    assert 0 <= aapl_metrics["max_drawdown"] <= 1


def test_risk_summary_generation(sample_portfolio, mock_data_fetcher):
    """Test risk summary generation."""
    agent = RiskAnalyzerAgent(data_fetcher=mock_data_fetcher)

    result = agent.process(sample_portfolio, period="1y")

    assert "risk_summary" in result
    assert "risk_level" in result["risk_summary"]
    assert result["risk_summary"]["risk_level"] in ["LOW", "MODERATE", "HIGH"]
    assert "key_findings" in result["risk_summary"]


def test_full_analysis_result_structure(sample_portfolio, mock_data_fetcher):
    """Test the full analysis result has correct structure."""
    agent = RiskAnalyzerAgent(data_fetcher=mock_data_fetcher)

    result = agent.process(sample_portfolio, period="1y")

    assert "timestamp" in result
    assert "portfolio_name" in result
    assert result["portfolio_name"] == "Test Portfolio"
    assert "analysis_period" in result
    assert result["analysis_period"] == "1y"
    assert "portfolio_metrics" in result
    assert "asset_metrics" in result
    assert "risk_summary" in result


def test_calculations_module():
    """Test individual calculation functions."""
    np.random.seed(42)
    returns = pd.Series(np.random.normal(0.001, 0.02, 252))

    vol = calculate_volatility(returns)
    assert vol > 0
    # Annualized volatility should be roughly sqrt(252) * daily std
    daily_std = float(np.std(returns, ddof=1))
    expected_annual_vol = daily_std * np.sqrt(252)
    assert np.isclose(vol, expected_annual_vol, rtol=0.01)

    sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.04)
    assert isinstance(sharpe, float)

    max_dd = calculate_max_drawdown(returns)
    assert 0 <= max_dd <= 1

    var = calculate_var_historical(returns, confidence_level=0.95)
    assert isinstance(var, float)

    cvar = calculate_cvar(returns, confidence_level=0.95)
    assert isinstance(cvar, float)
    assert cvar <= var  # CVaR should be worse (more negative) than VaR

    sortino = calculate_sortino_ratio(returns)
    assert isinstance(sortino, float)

"""Tests for the Risk Analyzer Agent."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from datetime import datetime

from src.agents.risk_analyzer import RiskAnalyzerAgent
from src.models.portfolio import Portfolio, Asset

class ConcreteRiskAnalyzerAgent(RiskAnalyzerAgent):
    def process(self, *args, **kwargs):
        return self.execute(*args, **kwargs)

@pytest.fixture
def mock_data_fetcher():
    """Fixture for a mock data fetcher."""
    fetcher = MagicMock()

    # Mock return data for assets
    returns_aapl = pd.Series([0.01, 0.02, -0.01, 0.03, 0.005])
    returns_goog = pd.Series([0.02, 0.01, 0.01, -0.02, 0.015])

    # Simulate one asset with no data
    returns_bad = pd.Series([])

    fetcher.get_returns.side_effect = lambda symbol, period: {
        "AAPL": returns_aapl,
        "GOOG": returns_goog,
        "BAD": returns_bad
    }.get(symbol, pd.Series())

    return fetcher

@pytest.fixture
def sample_portfolio():
    """Fixture for a sample portfolio."""
    assets = [
        Asset(symbol="AAPL", name="Apple Inc.", quantity=10, purchase_price=150.0, purchase_date="2023-01-01", asset_type="Equity", sector="Technology"),
        Asset(symbol="GOOG", name="Alphabet Inc.", quantity=5, purchase_price=2800.0, purchase_date="2023-01-01", asset_type="Equity", sector="Technology"),
        Asset(symbol="BAD", name="Bad Asset", quantity=100, purchase_price=10.0, purchase_date="2023-01-01", asset_type="Equity", sector="Technology") # This asset has no returns
    ]
    # Set current values
    assets[0].current_value = 1700.0 # 10 * 170
    assets[1].current_value = 14000.0 # 5 * 2800
    assets[2].current_value = 1000.0 # 100 * 10

    return Portfolio(name="Test Portfolio", assets=assets)

def test_portfolio_metrics_with_missing_data(sample_portfolio, mock_data_fetcher):
    """
    Test portfolio metrics calculation when some assets are missing data.
    """
    agent = ConcreteRiskAnalyzerAgent(data_fetcher=mock_data_fetcher)

    # Execute the risk analysis
    metrics = agent._calculate_portfolio_metrics(sample_portfolio, period='1y')

    # --- Verification ---

    # The total value for weighting should only include assets with data
    expected_total_value = 1700.0 + 14000.0 # AAPL + GOOG

    assert np.isclose(metrics['total_value'], expected_total_value)

    # The weights should be calculated based on the filtered total value
    expected_weights = np.array([1700.0 / expected_total_value, 14000.0 / expected_total_value])

    # Get the returns for the assets with data
    returns_df = pd.DataFrame({
        "AAPL": mock_data_fetcher.get_returns("AAPL", '1y'),
        "GOOG": mock_data_fetcher.get_returns("GOOG", '1y')
    })

    # Calculate expected portfolio returns
    expected_portfolio_returns = (returns_df * expected_weights).sum(axis=1)

    # Expected volatility
    expected_volatility = np.std(expected_portfolio_returns)

    # Assert that the calculated volatility matches the expected value
    assert np.isclose(metrics['volatility'], expected_volatility)

"""Risk Analyzer Agent for calculating portfolio risk metrics."""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import pandas as pd
import numpy as np

from src.agents.base_agent import BaseAgent
from src.models.portfolio import Portfolio
from src.services.data_fetcher import MultiSourceDataFetcher
from src.utils.calculations import (
    calculate_var_parametric,
    calculate_var_historical,
    calculate_var_monte_carlo,
    calculate_cvar,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_volatility,
    calculate_max_drawdown,
    calculate_correlation_matrix,
)

logger = logging.getLogger(__name__)


class RiskAnalyzerAgent(BaseAgent):
    """Agent for analyzing portfolio risk metrics."""

    def __init__(
        self,
        data_fetcher: Optional[MultiSourceDataFetcher] = None,
        confidence_level: float = 0.95,
        risk_free_rate: float = 0.04,
        monte_carlo_simulations: int = 10000,
    ):
        super().__init__("RiskAnalyzer")
        self.data_fetcher = data_fetcher or MultiSourceDataFetcher()
        self.confidence_level = confidence_level
        self.risk_free_rate = risk_free_rate
        self.monte_carlo_simulations = monte_carlo_simulations
        logger.info(f"Risk Analyzer Agent initialized (confidence: {confidence_level}, mc_sims: {monte_carlo_simulations})")

    def process(self, portfolio: Portfolio, period: str = "1y") -> Dict[str, Any]:
        """Run full risk analysis on a portfolio.

        Args:
            portfolio: Portfolio object to analyze.
            period: Lookback period for historical data (default '1y').

        Returns:
            Complete risk analysis report dict.
        """
        try:
            self.update_state("status", "running")
            logger.info(f"Analyzing risk for portfolio with {len(portfolio.assets)} assets")

            returns_data = self._collect_returns_data(portfolio, period)
            asset_metrics = self._calculate_asset_metrics(portfolio, returns_data)
            portfolio_metrics = self._calculate_portfolio_metrics(portfolio, returns_data)

            risk_report = {
                "timestamp": datetime.now().isoformat(),
                "portfolio_name": portfolio.name,
                "analysis_period": period,
                "portfolio_metrics": portfolio_metrics,
                "asset_metrics": asset_metrics,
                "risk_summary": self._generate_risk_summary(portfolio_metrics),
            }

            self.update_state("status", "completed")
            logger.info("Risk analysis completed")
            return risk_report

        except Exception as e:
            self.update_state("status", "failed")
            self.handle_error(e, "Error analyzing risk")
            raise

    def _collect_returns_data(self, portfolio: Portfolio, period: str) -> Dict[str, pd.Series]:
        """Fetch returns for all assets in a single batch download."""
        symbols = [asset.symbol for asset in portfolio.assets]
        returns_data: Dict[str, pd.Series] = {}

        try:
            batch = self.data_fetcher.get_multiple_returns(symbols, period=period)
            for symbol, returns in batch.items():
                if not returns.empty and len(returns) >= 30:
                    returns_data[symbol] = returns
                else:
                    logger.warning(f"Insufficient data for {symbol}")
        except Exception as e:
            logger.error(f"Batch returns fetch failed, falling back to sequential: {e}")
            # Fallback to sequential if batch fails
            for asset in portfolio.assets:
                try:
                    returns = self.data_fetcher.get_returns(asset.symbol, period=period)
                    if not returns.empty and len(returns) >= 30:
                        returns_data[asset.symbol] = returns
                except Exception as e2:
                    logger.error(f"Error fetching returns for {asset.symbol}: {e2}")

        return returns_data

    def _calculate_asset_metrics(
        self, portfolio: Portfolio, returns_data: Dict[str, pd.Series]
    ) -> List[Dict]:
        """Calculate risk metrics for each individual asset using pre-fetched returns."""
        asset_metrics = []

        for asset in portfolio.assets:
            try:
                returns = returns_data.get(asset.symbol)
                if returns is None or returns.empty or len(returns) < 30:
                    continue

                current_val = asset.current_value if asset.current_value else asset.purchase_value

                metrics = {
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "current_value": current_val,
                    "volatility": calculate_volatility(returns),
                    "sharpe_ratio": calculate_sharpe_ratio(returns, self.risk_free_rate),
                    "sortino_ratio": calculate_sortino_ratio(returns, self.risk_free_rate / 252),
                    "max_drawdown": calculate_max_drawdown(returns),
                    "var_95": calculate_var_historical(returns, confidence_level=0.95),
                    "cvar_95": calculate_cvar(returns, confidence_level=0.95),
                    "average_return": float(returns.mean()) * 252,
                }

                asset_metrics.append(metrics)
                logger.debug(f"Calculated metrics for {asset.symbol}")

            except Exception as e:
                logger.error(f"Error calculating metrics for {asset.symbol}: {e}")

        return asset_metrics

    def _calculate_portfolio_metrics(
        self, portfolio: Portfolio, returns_data: Dict[str, pd.Series]
    ) -> Dict:
        """Calculate aggregate portfolio-level risk metrics."""
        try:
            if not returns_data:
                logger.warning("No returns data available")
                return {}

            returns_df = pd.DataFrame(returns_data).dropna()
            assets_with_returns = [
                asset for asset in portfolio.assets if asset.symbol in returns_data
            ]

            total_value = sum(
                (asset.current_value if asset.current_value else asset.purchase_value)
                for asset in assets_with_returns
            )

            if total_value == 0:
                return {}

            weights = np.array([
                (asset.current_value if asset.current_value else asset.purchase_value) / total_value
                for asset in assets_with_returns
            ])

            portfolio_returns = (returns_df * weights).sum(axis=1)

            return {
                "total_value": total_value,
                "volatility": calculate_volatility(portfolio_returns),
                "sharpe_ratio": calculate_sharpe_ratio(portfolio_returns, self.risk_free_rate),
                "sortino_ratio": calculate_sortino_ratio(portfolio_returns, self.risk_free_rate / 252),
                "max_drawdown": calculate_max_drawdown(portfolio_returns),
                "var_parametric_95": calculate_var_parametric(portfolio_returns, 0.95),
                "var_historical_95": calculate_var_historical(portfolio_returns, 0.95),
                "var_monte_carlo_95": calculate_var_monte_carlo(portfolio_returns, 0.95, self.monte_carlo_simulations),
                "cvar_95": calculate_cvar(portfolio_returns, 0.95),
                "average_return": float(portfolio_returns.mean()) * 252,
                "correlation_matrix": calculate_correlation_matrix(returns_df).to_dict(),
            }

        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return {}

    def _generate_risk_summary(self, metrics: Dict) -> Dict:
        """Generate a human-readable risk summary from portfolio metrics."""
        if not metrics:
            return {"status": "insufficient_data"}

        summary = {
            "risk_level": self._assess_risk_level(metrics),
            "key_findings": [],
        }

        volatility = metrics.get("volatility", 0)
        if volatility and volatility > 0.30:
            summary["key_findings"].append(f"High volatility: {volatility:.2%}")
        elif volatility and volatility > 0.15:
            summary["key_findings"].append(f"Moderate volatility: {volatility:.2%}")

        sharpe = metrics.get("sharpe_ratio", 0)
        if sharpe is not None:
            if sharpe > 1.0:
                summary["key_findings"].append(f"Good risk-adjusted returns (Sharpe: {sharpe:.2f})")
            elif sharpe < 0:
                summary["key_findings"].append(f"Poor risk-adjusted returns (Sharpe: {sharpe:.2f})")

        var_95 = metrics.get("var_historical_95", 0)
        if var_95:
            summary["key_findings"].append(f"95% VaR: {var_95:.2%} potential daily loss")

        max_dd = metrics.get("max_drawdown", 0)
        if max_dd and max_dd > 0.10:
            summary["key_findings"].append(f"Maximum drawdown: {max_dd:.2%}")

        return summary

    def _assess_risk_level(self, metrics: Dict) -> str:
        """Assess overall risk level based on multiple metrics."""
        volatility = metrics.get("volatility", 0) or 0
        sharpe = metrics.get("sharpe_ratio", 0) or 0

        risk_score = 0
        if volatility > 0.30:
            risk_score += 3
        elif volatility > 0.20:
            risk_score += 2
        elif volatility > 0.10:
            risk_score += 1

        if sharpe < 0:
            risk_score += 3
        elif sharpe < 0.5:
            risk_score += 2

        return "HIGH" if risk_score >= 4 else "MODERATE" if risk_score >= 2 else "LOW"

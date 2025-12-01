"""Risk Analyzer Agent for calculating portfolio risk metrics."""

from typing import Dict, List, Optional
from datetime import datetime
import logging
import pandas as pd
import numpy as np

from src.agents.base_agent import BaseAgent
from src.models.portfolio import Portfolio
from src.services.data_fetcher import YahooFinanceDataFetcher
from src.utils.calculations import (
    calculate_var_parametric,
    calculate_var_historical,
    calculate_var_monte_carlo,
    calculate_cvar,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_volatility,
    calculate_max_drawdown,
    calculate_correlation_matrix
)

logger = logging.getLogger(__name__)


class RiskAnalyzerAgent(BaseAgent):
    """Agent for analyzing portfolio risk metrics."""
    
    def __init__(self, data_fetcher: Optional[YahooFinanceDataFetcher] = None,
                 confidence_level: float = 0.95, risk_free_rate: float = 0.04):
        super().__init__("RiskAnalyzer")
        self.data_fetcher = data_fetcher or YahooFinanceDataFetcher()
        self.confidence_level = confidence_level
        self.risk_free_rate = risk_free_rate
        logger.info(f"Risk Analyzer Agent initialized (confidence: {confidence_level})")
    
    def execute(self, portfolio: Portfolio, period: str = '1y') -> Dict:
        try:
            self.update_state("running")
            logger.info(f"Analyzing risk for portfolio with {len(portfolio.assets)} assets")
            
            asset_metrics = self._calculate_asset_metrics(portfolio, period)
            portfolio_metrics = self._calculate_portfolio_metrics(portfolio, period)
            
            risk_report = {
                "timestamp": datetime.now().isoformat(),
                "portfolio_name": portfolio.name,
                "analysis_period": period,
                "portfolio_metrics": portfolio_metrics,
                "asset_metrics": asset_metrics,
                "risk_summary": self._generate_risk_summary(portfolio_metrics)
            }
            
            self.update_state("completed")
            logger.info("Risk analysis completed")
            return risk_report
            
        except Exception as e:
            self.update_state("failed")
            self.handle_error(e, "Error analyzing risk")
            raise
    
    def _calculate_asset_metrics(self, portfolio: Portfolio, period: str) -> List[Dict]:
        asset_metrics = []
        
        for asset in portfolio.assets:
            try:
                returns = self.data_fetcher.get_returns(asset.symbol, period=period)
                
                if returns.empty or len(returns) < 30:
                    logger.warning(f"Insufficient data for {asset.symbol}")
                    continue
                
                metrics = {
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "current_value": asset.current_value,
                    "volatility": calculate_volatility(returns),
                    "sharpe_ratio": calculate_sharpe_ratio(returns, self.risk_free_rate),
                    "sortino_ratio": calculate_sortino_ratio(returns, self.risk_free_rate),
                    "max_drawdown": calculate_max_drawdown(returns),
                    "var_95": calculate_var_historical(returns, confidence_level=0.95),
                    "cvar_95": calculate_cvar(returns, confidence_level=0.95),
                    "average_return": returns.mean() * 252
                }
                
                asset_metrics.append(metrics)
                logger.debug(f"Calculated metrics for {asset.symbol}")
                
            except Exception as e:
                logger.error(f"Error calculating metrics for {asset.symbol}: {e}")
        
        return asset_metrics
    
    def _calculate_portfolio_metrics(self, portfolio: Portfolio, period: str) -> Dict:
        try:
            returns_data = {}
            for asset in portfolio.assets:
                returns = self.data_fetcher.get_returns(asset.symbol, period=period)
                if not returns.empty:
                    returns_data[asset.symbol] = returns
            
            if not returns_data:
                logger.warning("No returns data available")
                return {}
            
            returns_df = pd.DataFrame(returns_data).dropna()
            total_value = sum(asset.current_value for asset in portfolio.assets)
            weights = np.array([asset.current_value / total_value for asset in portfolio.assets 
                               if asset.symbol in returns_data])
            
            portfolio_returns = (returns_df * weights).sum(axis=1)
            
            return {
                "total_value": total_value,
                "volatility": calculate_volatility(portfolio_returns),
                "sharpe_ratio": calculate_sharpe_ratio(portfolio_returns, self.risk_free_rate),
                "sortino_ratio": calculate_sortino_ratio(portfolio_returns, self.risk_free_rate),
                "max_drawdown": calculate_max_drawdown(portfolio_returns),
                "var_parametric_95": calculate_var_parametric(portfolio_returns, 0.95),
                "var_historical_95": calculate_var_historical(portfolio_returns, 0.95),
                "var_monte_carlo_95": calculate_var_monte_carlo(portfolio_returns, 0.95),
                "cvar_95": calculate_cvar(portfolio_returns, 0.95),
                "average_return": portfolio_returns.mean() * 252,
                "correlation_matrix": calculate_correlation_matrix(returns_df).to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return {}
    
    def _generate_risk_summary(self, metrics: Dict) -> Dict:
        if not metrics:
            return {"status": "insufficient_data"}
        
        summary = {
            "risk_level": self._assess_risk_level(metrics),
            "key_findings": []
        }
        
        volatility = metrics.get("volatility", 0)
        if volatility > 0.30:
            summary["key_findings"].append(f"High volatility: {volatility:.2%}")
        elif volatility > 0.15:
            summary["key_findings"].append(f"Moderate volatility: {volatility:.2%}")
        
        sharpe = metrics.get("sharpe_ratio", 0)
        if sharpe > 1.0:
            summary["key_findings"].append(f"Good risk-adjusted returns (Sharpe: {sharpe:.2f})")
        elif sharpe < 0:
            summary["key_findings"].append(f"Poor risk-adjusted returns (Sharpe: {sharpe:.2f})")
        
        var_95 = metrics.get("var_historical_95", 0)
        if var_95:
            summary["key_findings"].append(f"95% VaR: {var_95:.2%} potential daily loss")
        
        return summary
    
    def _assess_risk_level(self, metrics: Dict) -> str:
        volatility = metrics.get("volatility", 0)
        sharpe = metrics.get("sharpe_ratio", 0)
        
        risk_score = 0
        if volatility > 0.30:
            risk_score += 3
        elif volatility > 0.20:
            risk_score += 2
        
        if sharpe < 0.5:
            risk_score += 2
        
        return "HIGH" if risk_score >= 4 else "MODERATE" if risk_score >= 2 else "LOW"
"""Analysis results data models for portfolio analysis."""

from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class RiskMetrics(BaseModel):
    """Risk metrics for an asset or portfolio."""
    volatility: float = Field(..., description="Annualized volatility")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    sortino_ratio: float = Field(..., description="Sortino ratio")
    max_drawdown: float = Field(..., description="Maximum drawdown")
    var_95: float = Field(..., description="Value at Risk at 95% confidence")
    cvar_95: float = Field(..., description="Conditional VaR at 95% confidence")
    average_return: float = Field(..., description="Average annualized return")


class AssetRiskAnalysis(BaseModel):
    """Risk analysis for individual asset."""
    symbol: str
    name: str
    current_value: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    var_95: float
    cvar_95: float
    average_return: float


class RiskSummary(BaseModel):
    """Risk summary with key findings."""
    risk_level: str = Field(..., description="LOW, MODERATE, or HIGH")
    key_findings: List[str] = Field(default_factory=list)


class RiskAnalysisResult(BaseModel):
    """Complete risk analysis result."""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    portfolio_name: str
    analysis_period: str
    portfolio_metrics: Dict[str, Any]
    asset_metrics: List[Dict[str, Any]]
    risk_summary: Dict[str, Any]


class MarketAnalysisResult(BaseModel):
    """Market monitoring analysis result."""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    portfolio_name: str
    market_conditions: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    trend_signals: List[Dict[str, Any]]
    alert_count: int


class RebalancingRecommendation(BaseModel):
    """Portfolio rebalancing recommendation."""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    portfolio_name: str
    total_value: float
    current_allocation: Dict[str, float]
    target_allocation: Dict[str, float]
    drift_analysis: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    needs_rebalancing: bool


class AnalysisSummary(BaseModel):
    """Executive summary of portfolio analysis."""
    portfolio_value: float
    asset_count: int
    risk_level: str
    key_findings: List[str]
    alert_count: int = 0
    recommendation_count: int = 0


class FullAnalysisResult(BaseModel):
    """Complete portfolio analysis result from orchestrator."""
    workflow: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    portfolio: Dict[str, Any]
    risk_analysis: Dict[str, Any]
    market_monitoring: Dict[str, Any]
    rebalancing_analysis: Optional[Dict[str, Any]] = None
    summary: Dict[str, Any]
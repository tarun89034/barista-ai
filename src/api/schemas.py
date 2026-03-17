"""Pydantic schemas for API request and response payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Health / Meta ──────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0.0"


class AgentStatusResponse(BaseModel):
    agents: Dict[str, Any]


# ── Portfolio ──────────────────────────────────────────────────────────────

class AssetCreate(BaseModel):
    symbol: str
    name: str
    quantity: float = Field(gt=0)
    purchase_price: float = Field(gt=0)
    purchase_date: str = Field(description="YYYY-MM-DD")
    asset_type: str
    sector: str


class PortfolioCreate(BaseModel):
    name: str = "My Portfolio"
    assets: List[AssetCreate]
    base_currency: str = "USD"


class PortfolioSummaryResponse(BaseModel):
    portfolio_id: str
    name: str
    asset_count: int
    total_purchase_value: float
    total_current_value: float
    base_currency: str
    assets: List[Dict[str, Any]]


class PortfolioListResponse(BaseModel):
    portfolios: List[PortfolioSummaryResponse]
    count: int


# ── Analysis ──────────────────────────────────────────────────────────────

class RiskAnalysisRequest(BaseModel):
    portfolio_id: str
    period: str = "1y"


class RiskAnalysisResponse(BaseModel):
    status: str
    portfolio_name: str
    analysis_period: str
    timestamp: str
    portfolio_metrics: Dict[str, Any]
    asset_metrics: List[Dict[str, Any]]
    risk_summary: Dict[str, Any]


class MarketMonitorRequest(BaseModel):
    portfolio_id: str


class MarketMonitorResponse(BaseModel):
    status: str
    portfolio_name: str
    timestamp: str
    current_prices: Dict[str, float]
    alerts: List[Dict[str, Any]]
    alert_count: int
    market_conditions: Dict[str, Any]


class RebalancingRequest(BaseModel):
    portfolio_id: str
    risk_profile: str = "moderate"


class RebalancingResponse(BaseModel):
    status: str
    portfolio_name: str
    risk_profile: str
    total_value: float
    timestamp: str
    current_allocation: Dict[str, float]
    target_allocation: Dict[str, float]
    drift_analysis: Dict[str, float]
    needs_rebalancing: bool
    recommendations: List[Dict[str, Any]]
    llm_reasoning: Optional[str] = None


class FullAnalysisRequest(BaseModel):
    portfolio_id: str
    period: str = "1y"
    risk_profile: str = "moderate"


class FullAnalysisResponse(BaseModel):
    status: str
    workflow: str
    timestamp: str
    portfolio: Dict[str, Any]
    risk_analysis: Dict[str, Any]
    market_monitoring: Dict[str, Any]
    rebalancing: Dict[str, Any]
    llm_summary: Optional[str] = None


# ── LLM ───────────────────────────────────────────────────────────────────

class LLMInsightRequest(BaseModel):
    portfolio_id: str
    include_risk: bool = True


class LLMInsightResponse(BaseModel):
    status: str
    insight: Optional[str] = None
    message: Optional[str] = None


class LLMRiskAdviceRequest(BaseModel):
    portfolio_id: str
    period: str = "1y"


class LLMRiskAdviceResponse(BaseModel):
    status: str
    advice: Optional[str] = None
    message: Optional[str] = None


# ── Global Market ─────────────────────────────────────────────────────────

class GlobalIndexEntry(BaseModel):
    name: str
    region: str
    currency: str
    price: float
    change: float
    change_pct: float


class GlobalIndicesResponse(BaseModel):
    status: str = "ok"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    indices: Dict[str, GlobalIndexEntry]


# ── Macro Economic Indicators ─────────────────────────────────────────────

class MacroObservation(BaseModel):
    date: str
    value: float


class MacroIndicator(BaseModel):
    series_id: str
    latest_value: Optional[float] = None
    latest_date: Optional[str] = None
    recent_observations: List[MacroObservation]


class MacroIndicatorsResponse(BaseModel):
    status: str = "ok"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    indicators: Dict[str, MacroIndicator]


# ── Indian Market ─────────────────────────────────────────────────────────

class IndianIndexEntry(BaseModel):
    name: str
    price: float
    change: float
    change_pct: float


class IndianStockEntry(BaseModel):
    symbol: str
    name: str
    price: float
    change_pct: float
    currency: str = "INR"


class IndianMarketResponse(BaseModel):
    status: str = "ok"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    indices: Dict[str, IndianIndexEntry]
    top_stocks: List[IndianStockEntry]


# ── Currency ──────────────────────────────────────────────────────────────

class ExchangeRatesResponse(BaseModel):
    status: str = "ok"
    base: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    rates: Dict[str, float]


class CurrencyConvertRequest(BaseModel):
    from_currency: str = "USD"
    to_currency: str = "INR"
    amount: float = 1.0


class CurrencyConvertResponse(BaseModel):
    status: str = "ok"
    from_currency: str = Field(alias="from")
    to_currency: str = Field(alias="to")
    amount: float
    converted: float
    rate: float

    model_config = {"populate_by_name": True}

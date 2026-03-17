"""Alert data models for Barista AI."""

from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AlertType(str, Enum):
    """Alert type enumeration."""
    PRICE_CHANGE = "price_change"
    VOLUME_SPIKE = "volume_spike"
    VOLATILITY_HIGH = "volatility_high"
    RISK_THRESHOLD = "risk_threshold"
    DRAWDOWN = "drawdown"
    REBALANCING_NEEDED = "rebalancing_needed"
    TREND_CHANGE = "trend_change"
    GENERAL = "general"


class AlertSeverity(str, Enum):
    """Alert severity enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(BaseModel):
    """Base alert model."""
    alert_id: str = Field(..., description="Unique alert identifier")
    alert_type: AlertType = Field(..., description="Type of alert")
    severity: AlertSeverity = Field(..., description="Alert severity")
    symbol: str = Field(..., description="Asset symbol")
    message: str = Field(..., description="Alert message")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    acknowledged: bool = Field(default=False)
    portfolio_name: str = Field(default="")


class PriceChangeAlert(Alert):
    """Alert for significant price changes."""
    price_change_pct: float = Field(default=0.0, description="Price change percentage")
    previous_price: float = Field(default=0.0)
    current_price: float = Field(default=0.0)


class VolumeSpikeAlert(Alert):
    """Alert for volume spikes."""
    volume_ratio: float = Field(default=0.0, description="Volume relative to average")
    current_volume: float = Field(default=0.0)
    average_volume: float = Field(default=0.0)


class RiskThresholdAlert(Alert):
    """Alert for risk threshold breaches."""
    metric_name: str = Field(default="", description="Risk metric that was breached")
    metric_value: float = Field(default=0.0)
    threshold_value: float = Field(default=0.0)


class AlertHistory(BaseModel):
    """Alert history for a portfolio."""
    portfolio_name: str
    alerts: List[Alert] = Field(default_factory=list)
    total_count: int = Field(default=0)
    unacknowledged_count: int = Field(default=0)


class AlertFilter(BaseModel):
    """Filter for querying alerts."""
    alert_types: Optional[List[AlertType]] = None
    severities: Optional[List[AlertSeverity]] = None
    symbols: Optional[List[str]] = None
    acknowledged: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class AlertSummary(BaseModel):
    """Summary of alerts."""
    total_alerts: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    unacknowledged_count: int = 0
    most_recent: Optional[Alert] = None

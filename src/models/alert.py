from enum import Enum

class AlertType(Enum):
    price_change = 'price_change'
    volume_spike = 'volume_spike'
    volatility_high = 'volatility_high'
    risk_threshold = 'risk_threshold'
    drawdown = 'drawdown'
    rebalancing_needed = 'rebalancing_needed'
    trend_change = 'trend_change'
    general = 'general'

class AlertSeverity(Enum):
    low = 'low'
    medium = 'medium'
    high = 'high'
    critical = 'critical'

class Alert:
    def __init__(self, alert_id, alert_type, severity, symbol, message, timestamp, metadata, acknowledged, portfolio_name):
        self.alert_id = alert_id
        self.type = alert_type
        self.severity = severity
        self.symbol = symbol
        self.message = message
        self.timestamp = timestamp
        self.metadata = metadata
        self.acknowledged = acknowledged
        self.portfolio_name = portfolio_name

class PriceChangeAlert(Alert):
    pass

class VolumeSpikeAlert(Alert):
    pass

class RiskThresholdAlert(Alert):
    pass

class AlertHistory:
    def __init__(self, portfolio_name):
        self.portfolio_name = portfolio_name
        self.alerts = []
        self.total_count = 0
        self.unacknowledged_count = 0

class AlertFilter:
    pass

class AlertSummary:
    pass

"""Market Monitor Agent for real-time price tracking and alert generation."""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import asyncio

from src.agents.base_agent import BaseAgent
from src.models.portfolio import Portfolio
from src.models.alert import Alert, AlertType, AlertSeverity, PriceChangeAlert, VolumeSpikeAlert
from src.services.data_fetcher import MultiSourceDataFetcher

logger = logging.getLogger(__name__)


class MarketMonitorAgent(BaseAgent):
    """Agent for monitoring market data and generating alerts."""

    def __init__(
        self,
        data_fetcher: Optional[MultiSourceDataFetcher] = None,
        price_alert_threshold: float = 0.02,
        volume_spike_threshold: float = 1.5,
    ):
        super().__init__("MarketMonitor")
        self.data_fetcher = data_fetcher or MultiSourceDataFetcher()
        self.price_alert_threshold = price_alert_threshold
        self.volume_spike_threshold = volume_spike_threshold
        self.previous_prices: Dict[str, float] = {}
        self.alerts: List[Alert] = []
        logger.info("Market Monitor Agent initialized")

    def process(self, portfolio: Portfolio, **kwargs) -> Dict[str, Any]:
        """Check current market data for all portfolio assets and generate alerts.

        Args:
            portfolio: Portfolio to monitor.

        Returns:
            Dictionary containing current prices, alerts, and market conditions.
        """
        try:
            self.update_state("status", "running")
            logger.info(f"Monitoring market for {len(portfolio.assets)} assets")

            # Batch fetch all prices in a single call
            symbols = [asset.symbol for asset in portfolio.assets]
            batch_prices = self.data_fetcher.get_multiple_prices(symbols)

            current_prices = {}
            new_alerts = []

            for asset in portfolio.assets:
                try:
                    price = batch_prices.get(asset.symbol)
                    if price is None:
                        logger.warning(f"Could not fetch price for {asset.symbol}")
                        continue

                    current_prices[asset.symbol] = price

                    # Check for price change alerts
                    if asset.symbol in self.previous_prices:
                        prev_price = self.previous_prices[asset.symbol]
                        if prev_price > 0:
                            pct_change = (price - prev_price) / prev_price
                            if abs(pct_change) >= self.price_alert_threshold:
                                alert = PriceChangeAlert(
                                    alert_id=f"price_{asset.symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                                    alert_type=AlertType.PRICE_CHANGE,
                                    severity=self._determine_severity(abs(pct_change)),
                                    symbol=asset.symbol,
                                    message=f"{asset.symbol} price changed {pct_change:+.2%} (${prev_price:.2f} -> ${price:.2f})",
                                    price_change_pct=pct_change,
                                    previous_price=prev_price,
                                    current_price=price,
                                    portfolio_name=portfolio.name,
                                )
                                new_alerts.append(alert)

                    self.previous_prices[asset.symbol] = price

                except Exception as e:
                    logger.error(f"Error monitoring {asset.symbol}: {e}")

            self.alerts.extend(new_alerts)

            result = {
                "timestamp": datetime.now().isoformat(),
                "portfolio_name": portfolio.name,
                "current_prices": current_prices,
                "alerts": [a.model_dump() for a in new_alerts],
                "alert_count": len(new_alerts),
                "total_alerts_history": len(self.alerts),
                "market_conditions": self._assess_market_conditions(current_prices, portfolio),
            }

            self.update_state("status", "completed")
            return result

        except Exception as e:
            self.update_state("status", "failed")
            self.handle_error(e, "Error monitoring market")
            raise

    def _determine_severity(self, abs_pct_change: float) -> AlertSeverity:
        """Determine alert severity based on price change magnitude."""
        if abs_pct_change >= 0.10:
            return AlertSeverity.CRITICAL
        elif abs_pct_change >= 0.05:
            return AlertSeverity.HIGH
        elif abs_pct_change >= 0.03:
            return AlertSeverity.MEDIUM
        return AlertSeverity.LOW

    def _assess_market_conditions(self, current_prices: Dict[str, float],
                                   portfolio: Portfolio) -> Dict[str, Any]:
        """Assess overall market conditions based on current data."""
        if not current_prices:
            return {"status": "no_data"}

        gainers = []
        losers = []
        for symbol, price in current_prices.items():
            if symbol in self.previous_prices:
                prev = self.previous_prices[symbol]
                if prev > 0:
                    change = (price - prev) / prev
                    if change > 0:
                        gainers.append({"symbol": symbol, "change": change})
                    elif change < 0:
                        losers.append({"symbol": symbol, "change": change})

        return {
            "status": "active",
            "assets_tracked": len(current_prices),
            "gainers": sorted(gainers, key=lambda x: x["change"], reverse=True)[:5],
            "losers": sorted(losers, key=lambda x: x["change"])[:5],
        }

    def get_alerts(self, symbol: Optional[str] = None,
                   severity: Optional[AlertSeverity] = None) -> List[Dict]:
        """Get filtered alerts."""
        alerts = self.alerts
        if symbol:
            alerts = [a for a in alerts if a.symbol == symbol]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return [a.model_dump() for a in alerts]

    def clear_alerts(self) -> None:
        """Clear all stored alerts."""
        self.alerts.clear()
        logger.info("All alerts cleared")

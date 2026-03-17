"""Rebalancing Advisor Agent for portfolio allocation optimization."""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import numpy as np

from src.agents.base_agent import BaseAgent
from src.models.portfolio import Portfolio, AssetType
from src.services.llm_service import GeminiLLMService

logger = logging.getLogger(__name__)

# Default target allocations by risk profile
RISK_PROFILES = {
    "conservative": {
        "Equity": 0.30,
        "Debt": 0.40,
        "Commodity": 0.10,
        "Crypto": 0.02,
        "REIT": 0.08,
        "Cash": 0.10,
    },
    "moderate": {
        "Equity": 0.50,
        "Debt": 0.25,
        "Commodity": 0.08,
        "Crypto": 0.05,
        "REIT": 0.07,
        "Cash": 0.05,
    },
    "aggressive": {
        "Equity": 0.70,
        "Debt": 0.10,
        "Commodity": 0.05,
        "Crypto": 0.08,
        "REIT": 0.05,
        "Cash": 0.02,
    },
}


class RebalancingAdvisorAgent(BaseAgent):
    """Agent for analyzing portfolio allocation and providing rebalancing recommendations."""

    def __init__(
        self,
        risk_profile: str = "moderate",
        rebalancing_threshold: float = 0.05,
        llm_service: Optional[GeminiLLMService] = None,
    ):
        super().__init__("RebalancingAdvisor")
        self.risk_profile = risk_profile
        self.rebalancing_threshold = rebalancing_threshold
        self.target_allocation = RISK_PROFILES.get(risk_profile, RISK_PROFILES["moderate"])
        self.llm_service = llm_service
        logger.info(f"Rebalancing Advisor initialized with '{risk_profile}' profile")

    def process(self, portfolio: Portfolio, risk_profile: Optional[str] = None,
                risk_analysis: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze portfolio allocation and generate rebalancing recommendations.

        Args:
            portfolio: Portfolio to analyze.
            risk_profile: Override risk profile (conservative/moderate/aggressive).
            risk_analysis: Optional risk analysis results for context.

        Returns:
            Rebalancing recommendation dict.
        """
        try:
            self.update_state("status", "running")

            if risk_profile and risk_profile in RISK_PROFILES:
                self.risk_profile = risk_profile
                self.target_allocation = RISK_PROFILES[risk_profile]

            # Calculate current allocation
            current_allocation = self._calculate_current_allocation(portfolio)

            # Calculate drift from target
            drift = self._calculate_drift(current_allocation)

            # Determine if rebalancing is needed
            needs_rebalancing = any(
                abs(d) > self.rebalancing_threshold for d in drift.values()
            )

            # Generate trade recommendations
            recommendations = self._generate_recommendations(
                portfolio, current_allocation, drift
            )

            # Get LLM-powered reasoning if service available
            llm_reasoning = None
            if self.llm_service and needs_rebalancing:
                try:
                    llm_reasoning = self.llm_service.generate_rebalancing_recommendations(
                        portfolio.to_summary(),
                        current_allocation,
                        self.target_allocation,
                        risk_analysis,
                    )
                except Exception as e:
                    logger.warning(f"LLM reasoning unavailable: {e}")

            result = {
                "timestamp": datetime.now().isoformat(),
                "portfolio_name": portfolio.name,
                "risk_profile": self.risk_profile,
                "total_value": portfolio.total_current_value,
                "current_allocation": current_allocation,
                "target_allocation": self.target_allocation,
                "drift_analysis": drift,
                "needs_rebalancing": needs_rebalancing,
                "recommendations": recommendations,
                "llm_reasoning": llm_reasoning,
            }

            self.update_state("status", "completed")
            return result

        except Exception as e:
            self.update_state("status", "failed")
            self.handle_error(e, "Error in rebalancing analysis")
            raise

    def _calculate_current_allocation(self, portfolio: Portfolio) -> Dict[str, float]:
        """Calculate the current allocation by asset type."""
        allocation: Dict[str, float] = {}
        total_value = portfolio.total_current_value

        if total_value == 0:
            return allocation

        for asset in portfolio.assets:
            asset_type = asset.asset_type if isinstance(asset.asset_type, str) else asset.asset_type.value
            val = asset.current_value if asset.current_value else asset.purchase_value
            allocation[asset_type] = allocation.get(asset_type, 0.0) + val

        # Convert to percentages
        for key in allocation:
            allocation[key] = round(allocation[key] / total_value, 4)

        return allocation

    def _calculate_drift(self, current_allocation: Dict[str, float]) -> Dict[str, float]:
        """Calculate drift from target allocation."""
        drift = {}
        for asset_type, target_pct in self.target_allocation.items():
            current_pct = current_allocation.get(asset_type, 0.0)
            drift[asset_type] = round(current_pct - target_pct, 4)
        return drift

    def _generate_recommendations(
        self,
        portfolio: Portfolio,
        current_allocation: Dict[str, float],
        drift: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """Generate specific trade recommendations to reach target allocation."""
        recommendations = []
        total_value = portfolio.total_current_value

        if total_value == 0:
            return recommendations

        for asset_type, drift_pct in drift.items():
            if abs(drift_pct) < self.rebalancing_threshold:
                continue

            trade_value = abs(drift_pct) * total_value
            action = "SELL" if drift_pct > 0 else "BUY"

            recommendations.append({
                "asset_type": asset_type,
                "action": action,
                "current_pct": current_allocation.get(asset_type, 0.0),
                "target_pct": self.target_allocation.get(asset_type, 0.0),
                "drift_pct": drift_pct,
                "trade_value": round(trade_value, 2),
                "reason": f"{asset_type} is {'overweight' if drift_pct > 0 else 'underweight'} by {abs(drift_pct):.1%}",
            })

        return sorted(recommendations, key=lambda x: abs(x["drift_pct"]), reverse=True)

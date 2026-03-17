"""Orchestrator Agent for coordinating all sub-agents."""

from typing import Dict, Optional, Any
from datetime import datetime
import logging

from src.agents.base_agent import BaseAgent
from src.agents.portfolio_reader import PortfolioReaderAgent
from src.agents.risk_analyzer import RiskAnalyzerAgent
from src.agents.market_monitor import MarketMonitorAgent
from src.agents.rebalancing_advisor import RebalancingAdvisorAgent
from src.agents.memory_agent import MemoryAgent
from src.models.portfolio import Portfolio
from src.services.llm_service import GeminiLLMService

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Coordinates all sub-agents to perform complete portfolio analysis.

    Accepts pre-configured agent instances so that all agents share
    the same data_fetcher, config values, and caches.
    """

    def __init__(
        self,
        llm_service: Optional[GeminiLLMService] = None,
        portfolio_reader: Optional[PortfolioReaderAgent] = None,
        risk_analyzer: Optional[RiskAnalyzerAgent] = None,
        market_monitor: Optional[MarketMonitorAgent] = None,
        rebalancing_advisor: Optional[RebalancingAdvisorAgent] = None,
        memory_agent: Optional[MemoryAgent] = None,
    ):
        super().__init__("Orchestrator")
        self.llm_service = llm_service

        # Use injected agents or create defaults (for backward compat)
        self.portfolio_reader = portfolio_reader or PortfolioReaderAgent()
        self.risk_analyzer = risk_analyzer or RiskAnalyzerAgent()
        self.market_monitor = market_monitor or MarketMonitorAgent()
        self.rebalancing_advisor = rebalancing_advisor or RebalancingAdvisorAgent(
            llm_service=llm_service
        )
        self.memory_agent = memory_agent or MemoryAgent()

        logger.info("Orchestrator Agent initialized with all sub-agents (shared dependencies)")

    def process(self, workflow: str = "full_analysis", **params) -> Dict[str, Any]:
        """Dispatch a workflow.

        Args:
            workflow: Workflow type ('full_analysis', 'risk_only', 'monitor').
            **params: Additional parameters for the workflow.

        Returns:
            Workflow result dictionary.
        """
        try:
            self.update_state("status", "running")

            if workflow == "full_analysis":
                result = self.run_full_analysis(params)
            elif workflow == "risk_only":
                result = self.run_risk_analysis_only(params)
            elif workflow == "monitor":
                result = self.run_monitoring_only(params)
            else:
                logger.warning(f"Unknown workflow: {workflow}")
                return {"status": "error", "message": f"Unknown workflow: {workflow}"}

            self.update_state("status", "completed")
            return result

        except Exception as e:
            self.update_state("status", "failed")
            self.handle_error(e, f"Error executing workflow: {workflow}")
            return {"status": "error", "message": str(e)}

    def run_full_analysis(self, params: Dict) -> Dict[str, Any]:
        """Run complete analysis pipeline: read -> risk -> monitor -> rebalance -> store."""
        try:
            # Step 1: Load portfolio
            file_path = params.get("file_path", "")
            portfolio = None
            if file_path:
                portfolio = self.portfolio_reader.process(file_path)
            elif "portfolio" in params:
                portfolio = params["portfolio"]

            if portfolio is None:
                return {"status": "error", "message": "No portfolio provided"}

            # Step 2: Risk analysis
            period = params.get("period", "1y")
            risk_results = self.risk_analyzer.process(portfolio, period=period)

            # Step 3: Market monitoring
            monitoring_results = self.market_monitor.process(portfolio)

            # Step 4: Rebalancing analysis
            risk_profile = params.get("risk_profile", "moderate")
            rebalancing_results = self.rebalancing_advisor.process(
                portfolio, risk_profile=risk_profile, risk_analysis=risk_results
            )

            # Step 5: Store results in memory
            self.memory_agent.process("store", {
                "type": "full_analysis",
                "content": f"Full analysis for {portfolio.name} at {datetime.now().isoformat()}",
                "metadata": {
                    "portfolio_name": portfolio.name,
                    "risk_level": risk_results.get("risk_summary", {}).get("risk_level", "unknown"),
                    "total_value": risk_results.get("portfolio_metrics", {}).get("total_value", 0),
                },
            })

            # Step 6: Generate LLM summary if available
            llm_summary = None
            if self.llm_service:
                try:
                    llm_summary = self.llm_service.generate_portfolio_insights(
                        portfolio.to_summary(), risk_results
                    )
                except Exception as e:
                    logger.warning(f"LLM summary unavailable: {e}")

            return {
                "status": "success",
                "workflow": "full_analysis",
                "timestamp": datetime.now().isoformat(),
                "portfolio": portfolio.to_summary(),
                "risk_analysis": risk_results,
                "market_monitoring": monitoring_results,
                "rebalancing": rebalancing_results,
                "llm_summary": llm_summary,
            }

        except Exception as e:
            logger.error(f"Error in full analysis: {e}")
            return {"status": "error", "message": str(e)}

    def run_risk_analysis_only(self, params: Dict) -> Dict[str, Any]:
        """Run risk analysis only."""
        try:
            portfolio = params.get("portfolio")
            if portfolio is None:
                return {"status": "error", "message": "No portfolio provided"}

            period = params.get("period", "1y")
            risk_results = self.risk_analyzer.process(portfolio, period=period)

            return {
                "status": "success",
                "workflow": "risk_only",
                "timestamp": datetime.now().isoformat(),
                "risk_analysis": risk_results,
            }
        except Exception as e:
            logger.error(f"Error in risk analysis: {e}")
            return {"status": "error", "message": str(e)}

    def run_monitoring_only(self, params: Dict) -> Dict[str, Any]:
        """Run market monitoring only."""
        try:
            portfolio = params.get("portfolio")
            if portfolio is None:
                return {"status": "error", "message": "No portfolio provided"}

            monitoring_results = self.market_monitor.process(portfolio)

            return {
                "status": "success",
                "workflow": "monitor",
                "timestamp": datetime.now().isoformat(),
                "market_monitoring": monitoring_results,
            }
        except Exception as e:
            logger.error(f"Error in monitoring: {e}")
            return {"status": "error", "message": str(e)}

    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all sub-agents."""
        return {
            "orchestrator": self.get_info(),
            "portfolio_reader": self.portfolio_reader.get_info(),
            "risk_analyzer": self.risk_analyzer.get_info(),
            "market_monitor": self.market_monitor.get_info(),
            "rebalancing_advisor": self.rebalancing_advisor.get_info(),
            "memory_agent": self.memory_agent.get_info(),
        }

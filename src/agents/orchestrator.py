import logging
from src.agents.base_agent import BaseAgent
from src.agents.portfolio_reader import PortfolioReaderAgent
from src.agents.risk_analyzer import RiskAnalyzerAgent
from src.agents.market_monitor import MarketMonitorAgent
from src.agents.rebalancing_advisor import RebalancingAdvisorAgent
from src.agents.memory_agent import MemoryAgent
from src.models.portfolio import Portfolio

class OrchestratorAgent(BaseAgent):
    def __init__(self):
        self.portfolio_reader = PortfolioReaderAgent()
        self.risk_analyzer = RiskAnalyzerAgent()
        self.market_monitor = MarketMonitorAgent()
        self.rebalancing_advisor = RebalancingAdvisorAgent()
        self.memory_agent = MemoryAgent()
        logging.basicConfig(level=logging.INFO)

    def execute(self, workflow, params):
        try:
            if workflow == "full_analysis":
                return self.run_full_analysis(params)
            else:
                logging.warning(f"Unknown workflow: {workflow}")
                return {"status": "error", "message": "Unknown workflow"}
        except Exception as e:
            logging.error(f"Error executing workflow: {e}")
            return {"status": "error", "message": str(e)}

    def run_full_analysis(self, params):
        try:
            portfolio = self.portfolio_reader.load_portfolio(params['portfolio_id'])
            risk_results = self.run_risk_analysis(portfolio)
            monitoring_results = self.run_monitoring(portfolio)
            rebalancing_results = None
            if 'target_allocation' in params:
                rebalancing_results = self.run_rebalancing_analysis(portfolio, params['target_allocation'])
            self.memory_agent.store_results({"risk": risk_results, "monitoring": monitoring_results, "rebalancing": rebalancing_results})
            return self._generate_summary(risk_results, monitoring_results, rebalancing_results)
        except Exception as e:
            logging.error(f"Error in full analysis: {e}")
            return {"status": "error", "message": str(e)}

    def run_risk_analysis(self, portfolio):
        try:
            return self.risk_analyzer.analyze(portfolio)
        except Exception as e:
            logging.error(f"Error in risk analysis: {e}")
            return {"status": "error", "message": str(e)}

    def run_monitoring(self, portfolio):
        try:
            return self.market_monitor.monitor(portfolio)
        except Exception as e:
            logging.error(f"Error in market monitoring: {e}")
            return {"status": "error", "message": str(e)}

    def run_rebalancing_analysis(self, portfolio, target_allocation):
        try:
            return self.rebalancing_advisor.analyze(portfolio, target_allocation)
        except Exception as e:
            logging.error(f"Error in rebalancing analysis: {e}")
            return {"status": "error", "message": str(e)}

    def _generate_summary(self, risk_results, monitoring_results, rebalancing_results):
        summary = {
            "risk_analysis": risk_results,
            "monitoring": monitoring_results,
            "rebalancing": rebalancing_results
        }
        return summary

    def get_agent_status(self):
        return {
            "risk_analyzer": self.risk_analyzer.get_status(),
            "market_monitor": self.market_monitor.get_status(),
            "rebalancing_advisor": self.rebalancing_advisor.get_status(),
            "memory_agent": self.memory_agent.get_status()
        }
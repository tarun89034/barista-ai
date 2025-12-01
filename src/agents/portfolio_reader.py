"""Portfolio Reader Agent for loading and enriching portfolio data."""

from typing import Optional, List
from datetime import datetime
import logging

from src.agents.base_agent import BaseAgent
from src.models.portfolio import Portfolio, Asset
from src.utils.portfolio_parser import PortfolioParser
from src.services.data_fetcher import YahooFinanceDataFetcher
from src.utils.validators import validate_file_path

logger = logging.getLogger(__name__) 


class PortfolioReaderAgent(BaseAgent):
    """Agent for reading and enriching portfolio data."""
    
    def __init__(self, data_fetcher: Optional[YahooFinanceDataFetcher] = None):
        super().__init__("PortfolioReader")
        self.parser = PortfolioParser()
        self.data_fetcher = data_fetcher or YahooFinanceDataFetcher()
        logger.info("Portfolio Reader Agent initialized")
    
    def execute(self, file_path: str, enrich_with_prices: bool = True) -> Portfolio:
        try:
            self.update_state("running")
            logger.info(f"Reading portfolio from: {file_path}")
            
            is_valid, msg = validate_file_path(file_path, allowed_extensions=['.csv', '.xlsx', '.xls'])
            if not is_valid:
                raise ValueError(msg)
            
            portfolio = self.parser.parse_from_file(file_path)
            logger.info(f"Parsed portfolio '{portfolio.name}' with {len(portfolio.assets)} assets")
            
            if enrich_with_prices:
                portfolio = self._enrich_with_prices(portfolio)
            
            portfolio.calculate_total_value()
            self.update_state("completed")
            
            return portfolio
        except Exception as e:
            self.update_state("failed")
            self.handle_error(e, "Error reading portfolio")
            raise
    
    def _enrich_with_prices(self, portfolio: Portfolio) -> Portfolio:
        logger.info("Fetching current prices...")
        symbols = [asset.symbol for asset in portfolio.assets]
        prices = self.data_fetcher.get_multiple_prices(symbols)
        
        for asset in portfolio.assets:
            if asset.symbol in prices and prices[asset.symbol]:
                asset.current_price = prices[asset.symbol]
        
        return portfolio

"""Portfolio Reader Agent for loading and enriching portfolio data."""

from typing import Optional
import logging

from src.agents.base_agent import BaseAgent
from src.models.portfolio import Portfolio
from src.utils.portfolio_parser import PortfolioParser
from src.services.data_fetcher import MultiSourceDataFetcher
from src.utils.validators import validate_file_path

logger = logging.getLogger(__name__)


class PortfolioReaderAgent(BaseAgent):
    """Agent for reading and enriching portfolio data."""

    def __init__(self, data_fetcher: Optional[MultiSourceDataFetcher] = None):
        super().__init__("PortfolioReader")
        self.parser = PortfolioParser()
        self.data_fetcher = data_fetcher or MultiSourceDataFetcher()
        logger.info("Portfolio Reader Agent initialized")

    def process(self, file_path: str, enrich_with_prices: bool = True) -> Portfolio:
        """Process a portfolio file: parse and optionally enrich with live prices.

        Args:
            file_path: Path to CSV/Excel portfolio file.
            enrich_with_prices: Whether to fetch current market prices.

        Returns:
            Enriched Portfolio object.
        """
        try:
            self.update_state("status", "running")
            logger.info(f"Reading portfolio from: {file_path}")

            is_valid, msg = validate_file_path(file_path, allowed_extensions=[".csv", ".xlsx", ".xls"])
            if not is_valid:
                raise ValueError(msg)

            portfolio = self.parser.parse_from_file(file_path)
            logger.info(f"Parsed portfolio '{portfolio.name}' with {len(portfolio.assets)} assets")

            if enrich_with_prices:
                portfolio = self._enrich_with_prices(portfolio)

            portfolio.calculate_total_value()
            self.update_state("status", "completed")

            return portfolio
        except Exception as e:
            self.update_state("status", "failed")
            self.handle_error(e, "Error reading portfolio")
            raise

    def _enrich_with_prices(self, portfolio: Portfolio) -> Portfolio:
        """Fetch current prices and update assets."""
        logger.info("Fetching current prices...")
        symbols = [asset.symbol for asset in portfolio.assets]
        prices = self.data_fetcher.get_multiple_prices(symbols)

        for asset in portfolio.assets:
            if asset.symbol in prices and prices[asset.symbol] is not None:
                asset.current_price = prices[asset.symbol]

        return portfolio

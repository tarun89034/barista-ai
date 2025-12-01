"""Data fetcher service for retrieving market data from various APIs.

This module provides a unified interface for fetching market data from multiple sources.
"""

import yfinance as yf
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class DataFetcher(ABC):
    """Abstract base class for data fetchers."""
    
    def __init__(self, cache_duration: int = 300):
        """Initialize data fetcher.
        
        Args:
            cache_duration: Cache duration in seconds (default 5 minutes).
        """
        self.cache = {}
        self.cache_duration = cache_duration
        self.cache_timestamps = {}
        self.rate_limit_delay = 0.2
        self.last_request_time = 0
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        pass
    
    @abstractmethod
    def get_historical_data(self, symbol: str, start_date: datetime, 
                           end_date: datetime) -> pd.DataFrame:
        """Get historical price data."""
        pass
    
    def _is_cache_valid(self, symbol: str) -> bool:
        """Check if cached data is still valid."""
        if symbol not in self.cache_timestamps:
            return False
        elapsed = time.time() - self.cache_timestamps[symbol]
        return elapsed < self.cache_duration
    
    def _update_cache(self, symbol: str, data: any) -> None:
        """Update cache with new data."""
        self.cache[symbol] = data
        self.cache_timestamps[symbol] = time.time()
    
    def _rate_limit(self) -> None:
        """Implement rate limiting between API calls."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()


class YahooFinanceDataFetcher(DataFetcher):
    """Data fetcher implementation using Yahoo Finance API."""
    
    def __init__(self, cache_duration: int = 300):
        """Initialize Yahoo Finance data fetcher."""
        super().__init__(cache_duration)
        self.rate_limit_delay = 0.1
        logger.info("Initialized Yahoo Finance data fetcher")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from Yahoo Finance."""
        if self._is_cache_valid(symbol):
            return self.cache[symbol]
        
        try:
            self._rate_limit()
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1d')
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
                self._update_cache(symbol, price)
                return price
            return None
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None
    
    def get_historical_data(self, symbol: str, start_date: datetime, 
                           end_date: datetime) -> pd.DataFrame:
        """Get historical price data from Yahoo Finance."""
        try:
            self._rate_limit()
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            if df.empty:
                return pd.DataFrame()
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Optional[float]]:
        """Get current prices for multiple symbols."""
        return {symbol: self.get_current_price(symbol) for symbol in symbols}
    
    def get_returns(self, symbol: str, period: str = '1y') -> pd.Series:
        """Calculate returns for a symbol over a period."""
        try:
            self._rate_limit()
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            if df.empty:
                return pd.Series()
            return df['Close'].pct_change().dropna()
        except Exception as e:
            logger.error(f"Error calculating returns for {symbol}: {e}")
            return pd.Series()
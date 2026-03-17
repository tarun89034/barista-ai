"""Multi-source data fetcher with fallback chain, rate limiting, and global market support.

Fallback chain for price/returns: Finnhub -> Alpha Vantage -> yfinance
Additional services: FRED (macro), Currency conversion, Indian market, Global indices.

Performance: batch yf.download() for multiple tickers, ThreadPoolExecutor for FRED.
"""

import time
import threading
import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import yfinance as yf

logger = logging.getLogger(__name__)


# =============================================================================
# Rate Limiter
# =============================================================================

class RateLimiter:
    """Thread-safe token-bucket rate limiter per API source."""

    def __init__(self, max_calls: int, period_seconds: float = 60.0):
        self.max_calls = max_calls
        self.period = period_seconds
        self._timestamps: list[float] = []
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Block until a request slot is available."""
        with self._lock:
            now = time.time()
            # Purge timestamps older than the window
            self._timestamps = [t for t in self._timestamps if now - t < self.period]
            if len(self._timestamps) >= self.max_calls:
                sleep_for = self.period - (now - self._timestamps[0]) + 0.05
                if sleep_for > 0:
                    logger.debug(f"Rate limit reached, sleeping {sleep_for:.1f}s")
                    time.sleep(sleep_for)
            self._timestamps.append(time.time())

    def try_acquire(self) -> bool:
        """Try to acquire a request slot immediately without blocking."""
        with self._lock:
            now = time.time()
            self._timestamps = [t for t in self._timestamps if now - t < self.period]
            if len(self._timestamps) >= self.max_calls:
                return False
            self._timestamps.append(now)
            return True


# Pre-configured rate limiters
RATE_LIMITERS: Dict[str, RateLimiter] = {
    "finnhub": RateLimiter(max_calls=55, period_seconds=60),      # 60/min limit, 55 safe
    "alpha_vantage": RateLimiter(max_calls=4, period_seconds=60),  # 5/min limit, 4 safe
    "fred": RateLimiter(max_calls=100, period_seconds=60),         # 120/min limit, 100 safe
    "yfinance": RateLimiter(max_calls=120, period_seconds=60),     # allow bursty UI requests
    "currency": RateLimiter(max_calls=20, period_seconds=60),      # free tier safe
}


# =============================================================================
# Shared Cache
# =============================================================================

class SharedCache:
    """Thread-safe shared cache with TTL."""

    def __init__(self, default_ttl: int = 300):
        self._data: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._data and time.time() < self._expiry.get(key, 0):
                return self._data[key]
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            self._data[key] = value
            self._expiry[key] = time.time() + (ttl or self.default_ttl)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._expiry.clear()


# =============================================================================
# Abstract Base
# =============================================================================

class DataFetcher(ABC):
    """Abstract base class for data fetchers."""

    def __init__(self, cache: Optional[SharedCache] = None):
        self.cache = cache or SharedCache()

    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        pass

    @abstractmethod
    def get_historical_data(self, symbol: str, start_date: datetime,
                            end_date: datetime) -> pd.DataFrame:
        pass


# =============================================================================
# Finnhub Fetcher
# =============================================================================

class FinnhubFetcher:
    """Fetch data from Finnhub REST API."""

    BASE = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str, cache: SharedCache):
        self.api_key = api_key
        self.cache = cache
        self.limiter = RATE_LIMITERS["finnhub"]
        self._disabled_until = 0.0

    def _get(self, endpoint: str, params: Dict) -> Optional[Dict]:
        if not self.api_key:
            return None
        if time.time() < self._disabled_until:
            return None
        if not self.limiter.try_acquire():
            return None
        params["token"] = self.api_key
        try:
            r = requests.get(f"{self.BASE}{endpoint}", params=params, timeout=2)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (401, 403):
                self._disabled_until = time.time() + 1800
            logger.warning(f"Finnhub {endpoint} returned {r.status_code}")
        except Exception as e:
            # Disable for 10min on connection errors (DNS, network, etc.)
            self._disabled_until = time.time() + 600
            logger.warning(f"Finnhub unreachable (disabled 10min): {e}")
        return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        ck = f"finnhub_price_{symbol}"
        cached = self.cache.get(ck)
        if cached is not None:
            return cached
        data = self._get("/quote", {"symbol": symbol})
        if data and data.get("c") and data["c"] > 0:
            price = float(data["c"])
            self.cache.set(ck, price, ttl=120)
            return price
        return None

    def get_returns(self, symbol: str, days: int = 365) -> Optional[pd.Series]:
        ck = f"finnhub_returns_{symbol}_{days}"
        cached = self.cache.get(ck)
        if cached is not None:
            return cached
        now = int(time.time())
        start = now - days * 86400
        data = self._get("/stock/candle", {
            "symbol": symbol, "resolution": "D", "from": start, "to": now
        })
        if data and data.get("s") == "ok" and data.get("c"):
            closes = pd.Series(data["c"], dtype=float)
            returns = closes.pct_change().dropna()
            if len(returns) >= 20:
                self.cache.set(ck, returns, ttl=600)
                return returns
        return None


# =============================================================================
# Alpha Vantage Fetcher
# =============================================================================

class AlphaVantageFetcher:
    """Fetch data from Alpha Vantage REST API."""

    BASE = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str, cache: SharedCache):
        self.api_key = api_key
        self.cache = cache
        self.limiter = RATE_LIMITERS["alpha_vantage"]
        self._disabled_until = 0.0

    def _get(self, params: Dict) -> Optional[Dict]:
        if not self.api_key:
            return None
        if time.time() < self._disabled_until:
            return None
        if not self.limiter.try_acquire():
            return None
        params["apikey"] = self.api_key
        try:
            r = requests.get(self.BASE, params=params, timeout=3)
            if r.status_code == 200:
                data = r.json()
                # Alpha Vantage returns error messages inside JSON
                if "Error Message" in data or "Note" in data:
                    if "Note" in data:
                        self._disabled_until = time.time() + 300
                    logger.warning(f"Alpha Vantage error: {data.get('Error Message') or data.get('Note')}")
                    return None
                return data
        except Exception as e:
            # Disable for 10min on connection errors
            self._disabled_until = time.time() + 600
            logger.warning(f"Alpha Vantage unreachable (disabled 10min): {e}")
        return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        ck = f"av_price_{symbol}"
        cached = self.cache.get(ck)
        if cached is not None:
            return cached
        data = self._get({"function": "GLOBAL_QUOTE", "symbol": symbol})
        if data and "Global Quote" in data:
            price_str = data["Global Quote"].get("05. price")
            if price_str:
                price = float(price_str)
                self.cache.set(ck, price, ttl=120)
                return price
        return None

    def get_returns(self, symbol: str, days: int = 365) -> Optional[pd.Series]:
        ck = f"av_returns_{symbol}_{days}"
        cached = self.cache.get(ck)
        if cached is not None:
            return cached
        data = self._get({
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "full" if days > 100 else "compact",
        })
        if data and "Time Series (Daily)" in data:
            ts = data["Time Series (Daily)"]
            closes = []
            dates = sorted(ts.keys(), reverse=True)[:days]
            for d in reversed(dates):
                closes.append(float(ts[d]["4. close"]))
            if len(closes) >= 20:
                series = pd.Series(closes, dtype=float)
                returns = series.pct_change().dropna()
                self.cache.set(ck, returns, ttl=600)
                return returns
        return None


# =============================================================================
# Yahoo Finance Fetcher (fallback)
# =============================================================================

class YahooFinanceFetcher:
    """Fetch data from Yahoo Finance via yfinance."""

    def __init__(self, cache: SharedCache):
        self.cache = cache
        self.limiter = RATE_LIMITERS["yfinance"]

    def get_current_price(self, symbol: str) -> Optional[float]:
        ck = f"yf_price_{symbol}"
        cached = self.cache.get(ck)
        if cached is not None:
            return cached
        if not self.limiter.try_acquire():
            return None
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
                self.cache.set(ck, price, ttl=120)
                return price
        except Exception as e:
            logger.warning(f"yfinance price error for {symbol}: {e}")
        return None

    def get_returns(self, symbol: str, period: str = "1y") -> Optional[pd.Series]:
        ck = f"yf_returns_{symbol}_{period}"
        cached = self.cache.get(ck)
        if isinstance(cached, pd.Series):
            return cached
        if not self.limiter.try_acquire():
            return None
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            if isinstance(df, pd.DataFrame) and not df.empty and len(df) >= 20:
                close_series = df["Close"]
                if not isinstance(close_series, pd.Series):
                    return None
                returns = close_series.pct_change().dropna()
                if isinstance(returns, pd.Series):
                    self.cache.set(ck, returns, ttl=600)
                    return returns
        except Exception as e:
            logger.warning(f"yfinance returns error for {symbol}: {e}")
        return None

    def get_historical_data(self, symbol: str, start_date: datetime,
                            end_date: datetime) -> pd.DataFrame:
        if not self.limiter.try_acquire():
            return pd.DataFrame()
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            if isinstance(df, pd.DataFrame) and not df.empty:
                subset = df.loc[:, ["Open", "High", "Low", "Close", "Volume"]]
                return pd.DataFrame(subset)
        except Exception as e:
            logger.warning(f"yfinance historical error for {symbol}: {e}")
        return pd.DataFrame()

    # ── Batch methods (single yf.download call for many tickers) ──────

    def get_batch_prices(self, symbols: List[str]) -> Dict[str, Optional[float]]:
        """Fetch current prices for multiple symbols in a single yf.download() call."""
        result: Dict[str, Optional[float]] = {s: None for s in symbols}
        if not symbols:
            return result

        # Check cache first, collect uncached symbols
        uncached = []
        for s in symbols:
            ck = f"yf_price_{s}"
            cached = self.cache.get(ck)
            if cached is not None:
                result[s] = cached
            else:
                uncached.append(s)

        if not uncached:
            return result

        if not self.limiter.try_acquire():
            return result

        try:
            logger.info(f"Batch downloading prices for {len(uncached)} tickers")
            df = yf.download(uncached, period="5d", group_by="ticker",
                             threads=True, progress=False)
            if df.empty:
                return result

            if len(uncached) == 1:
                # Single ticker: columns are just OHLCV directly
                sym = uncached[0]
                if "Close" in df.columns and not df["Close"].dropna().empty:
                    price = float(df["Close"].dropna().iloc[-1])
                    result[sym] = price
                    self.cache.set(f"yf_price_{sym}", price, ttl=120)
            else:
                # Multiple tickers: MultiIndex columns (ticker, OHLCV)
                for sym in uncached:
                    try:
                        if sym in df.columns.get_level_values(0):
                            close_data = df[sym]["Close"].dropna()
                            if not close_data.empty:
                                price = float(close_data.iloc[-1])
                                result[sym] = price
                                self.cache.set(f"yf_price_{sym}", price, ttl=120)
                    except Exception as e:
                        logger.warning(f"Error extracting price for {sym}: {e}")
        except Exception as e:
            logger.warning(f"Batch price download failed: {e}")
            # Fallback: try individually for any that failed
            for sym in uncached:
                if result[sym] is None:
                    result[sym] = self.get_current_price(sym)

        return result

    def get_batch_returns(self, symbols: List[str], period: str = "1y") -> Dict[str, Optional[pd.Series]]:
        """Fetch daily returns for multiple symbols in a single yf.download() call."""
        result: Dict[str, Optional[pd.Series]] = {s: None for s in symbols}
        if not symbols:
            return result

        # Check cache first
        uncached = []
        for s in symbols:
            ck = f"yf_returns_{s}_{period}"
            cached = self.cache.get(ck)
            if isinstance(cached, pd.Series):
                result[s] = cached
            else:
                uncached.append(s)

        if not uncached:
            return result

        if not self.limiter.try_acquire():
            return result

        try:
            logger.info(f"Batch downloading returns for {len(uncached)} tickers (period={period})")
            df = yf.download(uncached, period=period, group_by="ticker",
                             threads=True, progress=False)
            if df.empty:
                return result

            if len(uncached) == 1:
                sym = uncached[0]
                if "Close" in df.columns:
                    close_series = df["Close"].dropna()
                    if len(close_series) >= 20:
                        returns = close_series.pct_change().dropna()
                        if isinstance(returns, pd.Series) and len(returns) >= 20:
                            self.cache.set(f"yf_returns_{sym}_{period}", returns, ttl=600)
                            result[sym] = returns
            else:
                for sym in uncached:
                    try:
                        if sym in df.columns.get_level_values(0):
                            close_data = df[sym]["Close"].dropna()
                            if len(close_data) >= 20:
                                returns = close_data.pct_change().dropna()
                                if isinstance(returns, pd.Series) and len(returns) >= 20:
                                    self.cache.set(f"yf_returns_{sym}_{period}", returns, ttl=600)
                                    result[sym] = returns
                    except Exception as e:
                        logger.warning(f"Error extracting returns for {sym}: {e}")
        except Exception as e:
            logger.warning(f"Batch returns download failed: {e}")
            # Fallback: try individually
            for sym in uncached:
                if result[sym] is None:
                    result[sym] = self.get_returns(sym, period)

        return result

    def get_batch_snapshot(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch price + change data for multiple symbols (used by global indices).

        Returns dict of symbol -> {price, prev_close} for each symbol.
        """
        result: Dict[str, Dict[str, Any]] = {}
        if not symbols:
            return result

        if not self.limiter.try_acquire():
            return result

        try:
            logger.info(f"Batch downloading snapshots for {len(symbols)} tickers")
            df = yf.download(symbols, period="5d", group_by="ticker",
                             threads=True, progress=False)
            if df.empty:
                return result

            if len(symbols) == 1:
                sym = symbols[0]
                if "Close" in df.columns:
                    closes = df["Close"].dropna()
                    if len(closes) >= 2:
                        result[sym] = {
                            "price": float(closes.iloc[-1]),
                            "prev_close": float(closes.iloc[-2]),
                        }
                    elif len(closes) == 1:
                        result[sym] = {"price": float(closes.iloc[-1]), "prev_close": None}
            else:
                for sym in symbols:
                    try:
                        if sym in df.columns.get_level_values(0):
                            closes = df[sym]["Close"].dropna()
                            if len(closes) >= 2:
                                result[sym] = {
                                    "price": float(closes.iloc[-1]),
                                    "prev_close": float(closes.iloc[-2]),
                                }
                            elif len(closes) == 1:
                                result[sym] = {"price": float(closes.iloc[-1]), "prev_close": None}
                    except Exception as e:
                        logger.warning(f"Error extracting snapshot for {sym}: {e}")
        except Exception as e:
            logger.warning(f"Batch snapshot download failed: {e}")

        return result


# =============================================================================
# FRED Fetcher (Macro Economic Indicators)
# =============================================================================

class FREDFetcher:
    """Fetch economic indicators from FRED (Federal Reserve Economic Data)."""

    BASE = "https://api.stlouisfed.org/fred/series/observations"

    # Key FRED series IDs
    SERIES = {
        "fed_funds_rate": "FEDFUNDS",
        "treasury_10y": "DGS10",
        "treasury_2y": "DGS2",
        "cpi": "CPIAUCSL",
        "unemployment": "UNRATE",
        "gdp": "GDP",
        "inflation_expectations": "T5YIE",
        "vix": "VIXCLS",
    }

    def __init__(self, api_key: str, cache: SharedCache):
        self.api_key = api_key
        self.cache = cache
        self.limiter = RATE_LIMITERS["fred"]

    def get_indicator(self, series_id: str, limit: int = 12) -> Optional[List[Dict]]:
        """Fetch recent observations for a FRED series."""
        if not self.api_key:
            return None
        ck = f"fred_{series_id}_{limit}"
        cached = self.cache.get(ck)
        if cached is not None:
            return cached
        if not self.limiter.try_acquire():
            return None
        try:
            r = requests.get(self.BASE, params={
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": limit,
            }, timeout=10)
            if r.status_code == 200:
                data = r.json()
                obs = data.get("observations", [])
                result = [
                    {"date": o["date"], "value": float(o["value"])}
                    for o in obs if o.get("value") and o["value"] != "."
                ]
                self.cache.set(ck, result, ttl=3600)  # 1hr cache for macro data
                return result
        except Exception as e:
            logger.warning(f"FRED request failed for {series_id}: {e}")
        return None

    def get_all_indicators(self) -> Dict[str, Any]:
        """Fetch all key macro indicators in parallel using ThreadPoolExecutor."""
        ck = "fred_all_indicators"
        cached = self.cache.get(ck)
        if cached is not None:
            return cached
        result = {}

        def _fetch_one(name: str, series_id: str) -> Tuple[str, Optional[Dict]]:
            obs = self.get_indicator(series_id, limit=6)
            if obs:
                return name, {
                    "series_id": series_id,
                    "latest_value": obs[0]["value"] if obs else None,
                    "latest_date": obs[0]["date"] if obs else None,
                    "recent_observations": obs[:6],
                }
            return name, None

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(_fetch_one, name, sid): name
                for name, sid in self.SERIES.items()
            }
            for future in as_completed(futures):
                try:
                    name, data = future.result(timeout=15)
                    if data:
                        result[name] = data
                except Exception as e:
                    logger.warning(f"FRED parallel fetch error: {e}")

        if result:
            self.cache.set(ck, result, ttl=3600)
        return result


# =============================================================================
# Currency Service
# =============================================================================

class CurrencyService:
    """Currency conversion using frankfurter.app (free, no API key)."""

    BASE = "https://api.frankfurter.app"

    def __init__(self, cache: SharedCache):
        self.cache = cache
        self.limiter = RATE_LIMITERS["currency"]

    def get_rates(self, base: str = "USD") -> Optional[Dict[str, float]]:
        """Get exchange rates relative to base currency."""
        ck = f"fx_rates_{base}"
        cached = self.cache.get(ck)
        if cached is not None:
            return cached
        if not self.limiter.try_acquire():
            return None
        try:
            r = requests.get(f"{self.BASE}/latest", params={"from": base}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                rates = data.get("rates", {})
                if rates:
                    self.cache.set(ck, rates, ttl=1800)  # 30min cache
                    return rates
        except Exception as e:
            logger.warning(f"Currency rate fetch failed: {e}")
        return None

    def convert(self, amount: float, from_currency: str, to_currency: str) -> Optional[Dict]:
        """Convert amount between currencies."""
        if from_currency == to_currency:
            return {"from": from_currency, "to": to_currency, "amount": amount,
                    "converted": amount, "rate": 1.0}
        rates = self.get_rates(from_currency)
        if rates and to_currency in rates:
            rate = rates[to_currency]
            return {
                "from": from_currency,
                "to": to_currency,
                "amount": amount,
                "converted": round(amount * rate, 4),
                "rate": rate,
            }
        return None

    def get_supported_currencies(self) -> Optional[List[str]]:
        """Get list of supported currency codes."""
        ck = "fx_currencies"
        cached = self.cache.get(ck)
        if cached is not None:
            return cached
        if not self.limiter.try_acquire():
            return None
        try:
            r = requests.get(f"{self.BASE}/currencies", timeout=10)
            if r.status_code == 200:
                currencies = list(r.json().keys())
                self.cache.set(ck, currencies, ttl=86400)  # 24hr cache
                return currencies
        except Exception as e:
            logger.warning(f"Currency list fetch failed: {e}")
        return None


# =============================================================================
# Global Market Fetcher (major world indices via yfinance)
# =============================================================================

GLOBAL_INDICES = {
    # US
    "^GSPC": {"name": "S&P 500", "region": "US", "currency": "USD"},
    "^DJI": {"name": "Dow Jones", "region": "US", "currency": "USD"},
    "^IXIC": {"name": "NASDAQ Composite", "region": "US", "currency": "USD"},
    # Europe
    "^FTSE": {"name": "FTSE 100", "region": "UK", "currency": "GBP"},
    "^GDAXI": {"name": "DAX", "region": "Germany", "currency": "EUR"},
    "^FCHI": {"name": "CAC 40", "region": "France", "currency": "EUR"},
    # Asia
    "^N225": {"name": "Nikkei 225", "region": "Japan", "currency": "JPY"},
    "^HSI": {"name": "Hang Seng", "region": "Hong Kong", "currency": "HKD"},
    "000001.SS": {"name": "Shanghai Composite", "region": "China", "currency": "CNY"},
    # India
    "^NSEI": {"name": "NIFTY 50", "region": "India", "currency": "INR"},
    "^BSESN": {"name": "BSE SENSEX", "region": "India", "currency": "INR"},
}

INDIAN_TOP_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "MARUTI.NS", "TITAN.NS",
]


class GlobalMarketFetcher:
    """Fetch global market index data via yfinance (batch download)."""

    def __init__(self, cache: SharedCache):
        self.cache = cache
        self.yf = YahooFinanceFetcher(cache)

    def get_global_indices(self) -> Dict[str, Any]:
        """Fetch snapshot of all global indices in a single batch download."""
        ck = "global_indices_snapshot"
        cached = self.cache.get(ck)
        if cached is not None:
            return cached

        symbols = list(GLOBAL_INDICES.keys())
        snapshot = self.yf.get_batch_snapshot(symbols)

        result = {}
        for symbol, meta in GLOBAL_INDICES.items():
            if symbol in snapshot:
                data = snapshot[symbol]
                current = data["price"]
                prev = data.get("prev_close")
                if prev and prev > 0:
                    change = current - prev
                    change_pct = (change / prev) * 100
                    result[symbol] = {
                        **meta,
                        "price": round(current, 2),
                        "change": round(change, 2),
                        "change_pct": round(change_pct, 2),
                    }
                else:
                    result[symbol] = {**meta, "price": round(current, 2),
                                      "change": 0, "change_pct": 0}

        if result:
            self.cache.set(ck, result, ttl=300)
        return result

    def get_indian_market(self) -> Dict[str, Any]:
        """Fetch Indian market data in a single batch download."""
        ck = "indian_market"
        cached = self.cache.get(ck)
        if cached is not None:
            return cached

        # Batch all Indian tickers (indices + top stocks) in one download
        index_syms = ["^NSEI", "^BSESN"]
        stock_syms = INDIAN_TOP_STOCKS[:10]
        all_syms = index_syms + stock_syms

        snapshot = self.yf.get_batch_snapshot(all_syms)

        # Build indices dict
        indices = {}
        for sym in index_syms:
            if sym in snapshot:
                data = snapshot[sym]
                current = data["price"]
                prev = data.get("prev_close")
                if prev and prev > 0:
                    indices[sym] = {
                        "name": GLOBAL_INDICES[sym]["name"],
                        "price": round(current, 2),
                        "change": round(current - prev, 2),
                        "change_pct": round(((current - prev) / prev) * 100, 2),
                    }

        # Build top stocks list
        stocks = []
        for sym in stock_syms:
            if sym in snapshot:
                data = snapshot[sym]
                current = data["price"]
                prev = data.get("prev_close")
                change_pct = 0.0
                if prev and prev > 0:
                    change_pct = ((current - prev) / prev) * 100
                stocks.append({
                    "symbol": sym,
                    "name": sym.replace(".NS", ""),
                    "price": round(current, 2),
                    "change_pct": round(change_pct, 2),
                    "currency": "INR",
                })

        result = {"indices": indices, "top_stocks": stocks}
        if indices:
            self.cache.set(ck, result, ttl=300)
        return result


# =============================================================================
# Multi-Source Data Fetcher (unified interface with fallback)
# =============================================================================

class MultiSourceDataFetcher(DataFetcher):
    """Unified data fetcher with fallback chain: Finnhub -> Alpha Vantage -> yfinance.

    Also provides access to FRED, currency conversion, global markets, and Indian markets.
    """

    def __init__(
        self,
        finnhub_api_key: str = "",
        alpha_vantage_api_key: str = "",
        fred_api_key: str = "",
        cache_ttl: int = 300,
    ):
        cache = SharedCache(default_ttl=cache_ttl)
        super().__init__(cache)

        # Primary data sources (fallback chain order)
        self.finnhub = FinnhubFetcher(finnhub_api_key, cache) if finnhub_api_key else None
        self.alpha_vantage = AlphaVantageFetcher(alpha_vantage_api_key, cache) if alpha_vantage_api_key else None
        self.yfinance = YahooFinanceFetcher(cache)

        # Specialized services
        self.fred = FREDFetcher(fred_api_key, cache) if fred_api_key else None
        self.currency = CurrencyService(cache)
        self.global_market = GlobalMarketFetcher(cache)

        sources = []
        if self.finnhub:
            sources.append("Finnhub")
        if self.alpha_vantage:
            sources.append("AlphaVantage")
        sources.append("yfinance")
        logger.info(f"MultiSourceDataFetcher initialized. Fallback chain: {' -> '.join(sources)}")

    # ── Price (fallback chain) ────────────────────────────────────────

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price with fallback: Finnhub -> Alpha Vantage -> yfinance."""
        # Try Finnhub first (fastest, highest rate limit)
        if self.finnhub:
            price = self.finnhub.get_current_price(symbol)
            if price is not None:
                logger.debug(f"Price for {symbol} from Finnhub: {price}")
                return price

        # Fallback to Alpha Vantage
        if self.alpha_vantage:
            price = self.alpha_vantage.get_current_price(symbol)
            if price is not None:
                logger.debug(f"Price for {symbol} from AlphaVantage: {price}")
                return price

        # Final fallback: yfinance
        price = self.yfinance.get_current_price(symbol)
        if price is not None:
            logger.debug(f"Price for {symbol} from yfinance: {price}")
        return price

    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Optional[float]]:
        """Get current prices for multiple symbols using batch yfinance download.

        Strategy: probe Finnhub with first symbol. If it works, use it for all.
        If it fails, skip entirely and go straight to batch yfinance.
        Same for Alpha Vantage (but limited by rate, so only use for a few).
        """
        result: Dict[str, Optional[float]] = {s: None for s in symbols}
        remaining = list(symbols)

        # Probe Finnhub with first symbol; if it fails, skip entirely
        if self.finnhub and remaining:
            probe = self.finnhub.get_current_price(remaining[0])
            if probe is not None:
                result[remaining[0]] = probe
                remaining = remaining[1:]
                # Finnhub works — try the rest
                still_needed = []
                for s in remaining:
                    price = self.finnhub.get_current_price(s)
                    if price is not None:
                        result[s] = price
                    else:
                        still_needed.append(s)
                remaining = still_needed
            # If probe failed, skip Finnhub entirely for this batch

        # Alpha Vantage: only try up to 3 (low rate limit)
        if self.alpha_vantage and remaining:
            still_needed = []
            tried = 0
            for s in remaining:
                if tried >= 3:
                    still_needed.append(s)
                    continue
                price = self.alpha_vantage.get_current_price(s)
                tried += 1
                if price is not None:
                    result[s] = price
                else:
                    still_needed.append(s)
            remaining = still_needed

        # Batch the rest via yfinance (single download call)
        if remaining:
            batch_prices = self.yfinance.get_batch_prices(remaining)
            for s, price in batch_prices.items():
                if price is not None:
                    result[s] = price

        return result

    def get_multiple_returns(self, symbols: List[str], period: str = "1y") -> Dict[str, pd.Series]:
        """Get returns for multiple symbols using batch yfinance download.

        Returns only symbols with sufficient data (>= 20 data points).
        """
        result: Dict[str, pd.Series] = {}

        # Batch download via yfinance (most reliable for historical data)
        batch = self.yfinance.get_batch_returns(symbols, period)
        for s, returns in batch.items():
            if returns is not None and len(returns) >= 20:
                result[s] = returns

        return result

    # ── Returns (fallback chain) ──────────────────────────────────────

    def get_returns(self, symbol: str, period: str = "1y") -> pd.Series:
        """Get daily returns with fallback chain."""
        days = self._period_to_days(period)

        # Try Finnhub
        if self.finnhub:
            returns = self.finnhub.get_returns(symbol, days)
            if returns is not None and len(returns) >= 20:
                return returns

        # Try Alpha Vantage
        if self.alpha_vantage:
            returns = self.alpha_vantage.get_returns(symbol, days)
            if returns is not None and len(returns) >= 20:
                return returns

        # Fallback: yfinance
        returns = self.yfinance.get_returns(symbol, period)
        if returns is not None:
            return returns
        return pd.Series(dtype=float)

    def get_benchmark_returns(self, symbol: str = "^GSPC", period: str = "1y") -> pd.Series:
        """Get benchmark returns (uses yfinance directly for index data)."""
        returns = self.yfinance.get_returns(symbol, period)
        return returns if returns is not None else pd.Series(dtype=float)

    # ── Historical Data ───────────────────────────────────────────────

    def get_historical_data(self, symbol: str, start_date: datetime,
                            end_date: datetime) -> pd.DataFrame:
        """Get historical OHLCV data (yfinance is best for this)."""
        return self.yfinance.get_historical_data(symbol, start_date, end_date)

    # ── FRED Macro ────────────────────────────────────────────────────

    def get_macro_indicators(self) -> Dict[str, Any]:
        """Get all FRED macro economic indicators."""
        if self.fred:
            return self.fred.get_all_indicators()
        return {}

    def get_macro_indicator(self, series_id: str, limit: int = 12) -> Optional[List[Dict]]:
        """Get a specific FRED indicator."""
        if self.fred:
            return self.fred.get_indicator(series_id, limit)
        return None

    # ── Currency ──────────────────────────────────────────────────────

    def get_exchange_rates(self, base: str = "USD") -> Optional[Dict[str, float]]:
        """Get exchange rates for a base currency."""
        return self.currency.get_rates(base)

    def convert_currency(self, amount: float, from_curr: str, to_curr: str) -> Optional[Dict]:
        """Convert between currencies."""
        return self.currency.convert(amount, from_curr, to_curr)

    # ── Global Markets ────────────────────────────────────────────────

    def get_global_indices(self) -> Dict[str, Any]:
        """Get snapshot of global market indices."""
        return self.global_market.get_global_indices()

    def get_indian_market(self) -> Dict[str, Any]:
        """Get Indian market data."""
        return self.global_market.get_indian_market()

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _period_to_days(period: str) -> int:
        """Convert period string to days."""
        mapping = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
        return mapping.get(period, 365)


# =============================================================================
# Backward-compatible alias (so existing imports still work)
# =============================================================================

class YahooFinanceDataFetcher(MultiSourceDataFetcher):
    """Backward-compatible alias for MultiSourceDataFetcher.

    When constructed without API keys (like existing code does), it behaves
    exactly like the old Yahoo-only fetcher. When API keys are injected,
    it gains the full multi-source fallback chain.
    """

    def __init__(self, cache_duration: int = 300, **kwargs):
        super().__init__(cache_ttl=cache_duration, **kwargs)

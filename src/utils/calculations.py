"""Financial calculations module for Barista AI.

Provides risk metrics calculations including VaR, volatility, Sharpe ratio,
beta, drawdowns, and correlation analysis.
"""

from typing import Optional

import numpy as np
import pandas as pd
import scipy.stats as stats
import logging

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252


def calculate_variance(returns: pd.Series) -> float:
    """Calculate variance of returns."""
    if returns.empty or len(returns) < 2:
        return np.nan
    return float(np.var(returns, ddof=1))


def calculate_volatility(returns: pd.Series, annualize: bool = True) -> float:
    """Calculate volatility (standard deviation) of returns.

    Args:
        returns: Series of periodic returns.
        annualize: If True, annualize the volatility assuming daily returns.

    Returns:
        Annualized volatility if annualize=True, else daily volatility.
    """
    if returns.empty or len(returns) < 2:
        return np.nan
    vol = float(np.std(returns, ddof=1))
    if annualize:
        vol *= np.sqrt(TRADING_DAYS_PER_YEAR)
    return vol


def calculate_var_parametric(returns: pd.Series, confidence_level: float = 0.95) -> float:
    """Calculate parametric Value-at-Risk assuming normal distribution.

    Returns the daily VaR (negative number represents potential loss).
    """
    if returns.empty or len(returns) < 2:
        return np.nan
    mean = float(np.mean(returns))
    sigma = float(np.std(returns, ddof=1))
    var = mean - sigma * stats.norm.ppf(confidence_level)
    return float(var)


def calculate_var_historical(returns: pd.Series, confidence_level: float = 0.95) -> float:
    """Calculate historical Value-at-Risk from actual return distribution."""
    if returns.empty or len(returns) < 2:
        return np.nan
    return float(np.percentile(returns, (1 - confidence_level) * 100))


def calculate_var_monte_carlo(returns: pd.Series, confidence_level: float = 0.95,
                               n_simulations: int = 10000) -> float:
    """Calculate Monte Carlo Value-at-Risk using simulated returns."""
    if returns.empty or len(returns) < 2:
        return np.nan
    mean = float(np.mean(returns))
    sigma = float(np.std(returns, ddof=1))
    simulations = np.random.normal(mean, sigma, n_simulations)
    return float(np.percentile(simulations, (1 - confidence_level) * 100))


def calculate_cvar(returns: pd.Series, confidence_level: float = 0.95) -> float:
    """Calculate Conditional Value-at-Risk (Expected Shortfall).

    CVaR is the expected loss given that the loss exceeds VaR.
    """
    if returns.empty or len(returns) < 2:
        return np.nan
    var = calculate_var_historical(returns, confidence_level=confidence_level)
    if np.isnan(var):
        return np.nan
    tail = returns[returns <= var]
    if tail.empty:
        return var  # fallback to VaR if no observations in the tail
    return float(tail.mean())


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.04) -> float:
    """Calculate annualized Sharpe ratio.

    Args:
        returns: Series of daily returns.
        risk_free_rate: Annual risk-free rate (default 4%).

    Returns:
        Annualized Sharpe ratio.
    """
    if returns.empty or len(returns) < 2:
        return np.nan
    daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
    excess_returns = returns - daily_rf
    mean_excess = float(np.mean(excess_returns))
    vol = float(np.std(returns, ddof=1))
    if vol == 0:
        return np.nan
    return float((mean_excess / vol) * np.sqrt(TRADING_DAYS_PER_YEAR))


def calculate_beta(asset_returns: pd.Series, market_returns: pd.Series) -> float:
    """Calculate beta of asset relative to market.

    Args:
        asset_returns: Series of asset returns.
        market_returns: Series of market/benchmark returns.

    Returns:
        Beta coefficient.
    """
    if asset_returns.empty or market_returns.empty:
        return np.nan
    if len(asset_returns) < 2 or len(market_returns) < 2:
        return np.nan
    # Align the series
    combined = pd.concat([asset_returns, market_returns], axis=1).dropna()
    if len(combined) < 2:
        return np.nan
    covariance = np.cov(combined.iloc[:, 0], combined.iloc[:, 1])[0][1]
    market_variance = float(np.var(combined.iloc[:, 1], ddof=1))
    if market_variance == 0:
        return np.nan
    return float(covariance / market_variance)


def calculate_sortino_ratio(returns: pd.Series, target_return: float = 0.0) -> float:
    """Calculate Sortino ratio (penalizes only downside volatility).

    Args:
        returns: Series of daily returns.
        target_return: Minimum acceptable return (daily).

    Returns:
        Annualized Sortino ratio.
    """
    if returns.empty or len(returns) < 2:
        return np.nan
    downside_returns = returns[returns < target_return]
    if downside_returns.empty or len(downside_returns) < 2:
        return np.nan
    downside_std = float(np.std(downside_returns, ddof=1))
    if downside_std == 0:
        return np.nan
    mean_return = float(np.mean(returns))
    return float(((mean_return - target_return) / downside_std) * np.sqrt(TRADING_DAYS_PER_YEAR))


def calculate_information_ratio(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Calculate Information Ratio (active return / tracking error)."""
    if returns.empty or benchmark_returns.empty:
        return np.nan
    combined = pd.concat([returns, benchmark_returns], axis=1).dropna()
    if len(combined) < 2:
        return np.nan
    active_return = combined.iloc[:, 0] - combined.iloc[:, 1]
    tracking_error = float(np.std(active_return, ddof=1))
    if tracking_error == 0:
        return np.nan
    return float(np.mean(active_return) / tracking_error)


def calculate_treynor_ratio(returns: pd.Series, benchmark_returns: pd.Series,
                             risk_free_rate: float = 0.04) -> float:
    """Calculate Treynor Ratio (excess return per unit of systematic risk)."""
    if returns.empty or benchmark_returns.empty:
        return np.nan
    beta = calculate_beta(returns, benchmark_returns)
    if np.isnan(beta) or beta == 0:
        return np.nan
    daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
    annualized_return = float(np.mean(returns)) * TRADING_DAYS_PER_YEAR
    return float((annualized_return - risk_free_rate) / beta)


def calculate_calmar_ratio(returns: pd.Series) -> float:
    """Calculate Calmar Ratio (annualized return / max drawdown)."""
    if returns.empty or len(returns) < 2:
        return np.nan
    max_dd = calculate_max_drawdown(returns)
    if max_dd == 0 or np.isnan(max_dd):
        return np.nan
    annualized_return = float(np.mean(returns)) * TRADING_DAYS_PER_YEAR
    return float(annualized_return / max_dd)


def calculate_max_drawdown(returns: pd.Series) -> float:
    """Calculate maximum drawdown from a returns series.

    Converts returns to a cumulative wealth index, then calculates the
    maximum peak-to-trough decline.

    Args:
        returns: Series of periodic returns.

    Returns:
        Maximum drawdown as a positive fraction (e.g. 0.20 = 20% drawdown).
    """
    if returns.empty or len(returns) < 2:
        return np.nan
    # Build cumulative wealth index
    wealth = (1 + returns).cumprod()
    peak = wealth.cummax()
    drawdown = (wealth - peak) / peak
    max_dd = float(drawdown.min())
    return abs(max_dd)


def calculate_correlation_matrix(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate correlation matrix from a DataFrame of returns."""
    if data.empty:
        return pd.DataFrame()
    return data.corr()


def portfolio_metrics(returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> dict:
    """Calculate a suite of portfolio metrics.

    Args:
        returns: Portfolio daily returns series.
        benchmark_returns: Optional benchmark returns for beta calculation.

    Returns:
        Dictionary of key risk metrics.
    """
    metrics = {
        "volatility": calculate_volatility(returns),
        "var_95": calculate_var_historical(returns),
        "cvar_95": calculate_cvar(returns),
        "sharpe_ratio": calculate_sharpe_ratio(returns),
        "sortino_ratio": calculate_sortino_ratio(returns),
        "max_drawdown": calculate_max_drawdown(returns),
    }

    if benchmark_returns is not None and not benchmark_returns.empty:
        metrics["beta"] = calculate_beta(returns, benchmark_returns)
    else:
        metrics["beta"] = np.nan

    return metrics


logger.info("Financial calculations module loaded successfully.")

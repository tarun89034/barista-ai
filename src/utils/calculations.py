import numpy as np
import pandas as pd
import scipy.stats as stats
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_variance(price_series: pd.Series) -> float:
    return np.var(price_series)

def calculate_volatility(price_series: pd.Series) -> float:
    return np.std(price_series)

def calculate_var_parametric(price_series: pd.Series, confidence_level: float = 0.95) -> float:
    mean = np.mean(price_series)
    sigma = calculate_volatility(price_series)
    var = mean - sigma * stats.norm.ppf(confidence_level)
    return var

def calculate_var_historical(price_series: pd.Series, confidence_level: float = 0.95) -> float:
    return np.percentile(price_series, (1 - confidence_level) * 100)

def calculate_var_monte_carlo(price_series: pd.Series, confidence_level: float = 0.95) -> float:
    simulations = np.random.normal(np.mean(price_series), np.std(price_series), 10000)
    return np.percentile(simulations, (1 - confidence_level) * 100)

def calculate_cvar(price_series: pd.Series, confidence_level: float = 0.95) -> float:
    var = calculate_var_historical(price_series, confidence_level=confidence_level)
    cvar = price_series[price_series <= var].mean()
    return cvar

def calculate_sharpe_ratio(price_series: pd.Series, risk_free_rate: float = 0.01) -> float:
    avg_return = np.mean(price_series) - risk_free_rate
    volatility = calculate_volatility(price_series)
    if volatility == 0: return np.nan
    return avg_return / volatility

def calculate_beta(asset_returns: pd.Series, market_returns: pd.Series) -> float:
    covariance = np.cov(asset_returns, market_returns)[0][1]
    market_variance = calculate_variance(market_returns)
    if market_variance == 0: return np.nan
    return covariance / market_variance

def calculate_sortino_ratio(price_series: pd.Series, target_return: float = 0) -> float:
    downside_returns = price_series[price_series < target_return]
    expected_downside_return = np.mean(downside_returns)
    if expected_downside_return == 0: return np.nan
    return (np.mean(price_series) - target_return) / np.std(downside_returns)

def calculate_information_ratio(price_series: pd.Series, benchmark_series: pd.Series) -> float:
    active_return = price_series - benchmark_series
    return np.mean(active_return) / np.std(active_return)

def calculate_treynor_ratio(price_series: pd.Series, benchmark_returns: pd.Series, risk_free_rate: float = 0.01) -> float:
    return (np.mean(price_series) - risk_free_rate) / calculate_beta(_series, benchmark_returns)

def calculate_calmar_ratio(price_series: pd.Series) -> float:
    max_drawdown = calculate_max_drawdown(price_series)
    annual_return = np.mean(price_series)
    if max_drawdown == 0: return np.nan
    return annual_return / max_drawdown

def calculate_max_drawdown(price_series: pd.Series) -> float:
    peak = price_series[0]
    max_dd = 0
    for price in price_series:
        if price > peak:
            peak = price
        drawdown = (peak - price) / peak
        max_dd = max(max_dd, drawdown)
    return max_dd

def calculate_correlation_matrix(data: pd.DataFrame) -> pd.DataFrame:
    return data.corr()

def portfolio_metrics(returns: pd.Series) -> dict:
    metrics = {
        'Volatility': calculate_volatility(returns),
        'VaR (95%)': calculate_var_historical(returns),
        'CVaR (95%)': calculate_cvar(returns),
        'Sharpe Ratio': calculate_sharpe_ratio(returns),
        'Beta': calculate_beta(returns, returns.mean()),
        'Sortino Ratio': calculate_sortino_ratio(returns)
    }
    return metrics

# Example log
logging.info("Financial calculations module loaded successfully.")

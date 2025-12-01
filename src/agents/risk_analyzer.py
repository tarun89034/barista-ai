# Risk Analyzer Agent

class RiskAnalyzer:
    """
    A Risk Analyzer Agent that calculates portfolio risk metrics including:
    - Value at Risk (VaR)
    - Sharpe Ratio
    - Volatility
    - Generates risk summaries
    """

    def __init__(self, portfolio_returns):
        self.portfolio_returns = portfolio_returns

    def calculate_var(self, confidence_level=0.95):
        """
        Calculate the Value at Risk (VaR) of the portfolio.
        """
        return -self.portfolio_returns.quantile(1 - confidence_level)

    def calculate_sharpe_ratio(self, risk_free_rate=0.01):
        """
        Calculate the Sharpe Ratio of the portfolio.
        """
        excess_return = self.portfolio_returns.mean() - risk_free_rate
        return excess_return / self.portfolio_returns.std()

    def calculate_volatility(self):
        """
        Calculate the volatility of the portfolio returns.
        """
        return self.portfolio_returns.std()

    def generate_risk_summary(self):
        """
        Generate a summary of the portfolio risk metrics.
        """
        var = self.calculate_var()
        sharpe_ratio = self.calculate_sharpe_ratio()
        volatility = self.calculate_volatility()
        return {
            'Value at Risk (VaR)': var,
            'Sharpe Ratio': sharpe_ratio,
            'Volatility': volatility
        }

# Example usage:
# portfolio_returns = pd.Series([...])  # Replace with actual returns
# analyzer = RiskAnalyzer(portfolio_returns)
# summary = analyzer.generate_risk_summary()
# print(summary)
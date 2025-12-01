# Data Directory

This directory contains portfolio data files for the Barista AI system.

## Sample Portfolio

The `sample_portfolio.csv` file contains a diverse sample portfolio that demonstrates the multi-asset capabilities of Barista AI.

### Portfolio Composition

The sample portfolio includes:

- **Technology Stocks** (40%): AAPL, MSFT, GOOGL, NVDA
- **Other Equities** (30%): AMZN, TSLA, JPM, JNJ, V
- **Cryptocurrencies** (15%): BTC-USD, ETH-USD
- **Fixed Income** (10%): TLT, AGG (Treasury and Investment Grade Bonds)
- **Commodities** (3%): GLD (Gold ETF)
- **Real Estate** (2%): VNQ (REIT)

Total Portfolio Value: ~$100,000 (based on purchase prices)

## Portfolio File Format

To analyze your own portfolio, create a CSV file with the following columns:

| Column Name      | Description                                    | Example              |
|------------------|------------------------------------------------|----------------------|
| `Symbol`         | Ticker symbol (use Yahoo Finance format)       | AAPL, BTC-USD        |
| `Name`           | Full name of the asset                         | Apple Inc.           |
| `Quantity`       | Number of shares/units held                    | 50                   |
| `Purchase Price` | Price per unit at purchase                     | 150.00               |
| `Purchase Date`  | Date of purchase (YYYY-MM-DD)                  | 2023-01-15           |
| `Asset Type`     | Type of asset                                  | Equity, Crypto, Debt |
| `Sector`         | Industry sector or category                    | Technology           |

### Supported Asset Types

- **Equity**: Stocks, ETFs
- **Crypto**: Cryptocurrencies (use `-USD` suffix, e.g., BTC-USD)
- **Debt**: Bonds, Treasury securities
- **Commodity**: Gold, Silver, Oil ETFs
- **REIT**: Real Estate Investment Trusts

### Example CSV Format

```csv
Symbol,Name,Quantity,Purchase Price,Purchase Date,Asset Type,Sector
AAPL,Apple Inc.,50,150.00,2023-01-15,Equity,Technology
BTC-USD,Bitcoin,0.5,45000.00,2023-04-05,Crypto,Cryptocurrency
GLD,SPDR Gold Trust,100,180.00,2023-05-12,Commodity,Gold
```

## Using Your Own Portfolio

1. Create a CSV file following the format above
2. Save it in the `data/` directory
3. Run the analysis

## Data Privacy

⚠️ **Important**: Portfolio data files (except `sample_portfolio.csv`) are ignored by git to protect your privacy.
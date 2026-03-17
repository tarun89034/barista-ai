"""Portfolio parser for CSV and Excel files."""

import pandas as pd
from datetime import datetime
from typing import List
from pathlib import Path
import logging

from src.models.portfolio import Portfolio, Asset, AssetType

logger = logging.getLogger(__name__)


class PortfolioParser:
    """Parse portfolio data from CSV and Excel files."""

    SUPPORTED_FORMATS = [".csv", ".xlsx", ".xls"]

    # Map various column name conventions to our internal names
    COLUMN_ALIASES = {
        "symbol": ["symbol", "ticker", "Symbol", "Ticker", "SYMBOL"],
        "name": ["name", "Name", "NAME", "asset_name", "Asset Name"],
        "quantity": ["quantity", "Quantity", "QUANTITY", "shares", "Shares", "units", "Units"],
        "purchase_price": [
            "purchase_price", "Purchase Price", "purchase price",
            "cost_basis", "Cost Basis", "price", "Price",
        ],
        "purchase_date": [
            "purchase_date", "Purchase Date", "purchase date",
            "date", "Date", "buy_date",
        ],
        "asset_type": [
            "asset_type", "Asset Type", "asset type",
            "type", "Type", "category", "Category",
        ],
        "sector": ["sector", "Sector", "SECTOR", "industry", "Industry"],
    }

    def __init__(self):
        self.supported_formats = self.SUPPORTED_FORMATS

    def parse_from_file(self, file_path: str) -> Portfolio:
        """Parse a portfolio file into a Portfolio object.

        Args:
            file_path: Path to CSV or Excel file.

        Returns:
            Portfolio object with parsed assets.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        if path.suffix.lower() == ".csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        # Normalize column names
        df = self._normalize_columns(df)

        assets = self._parse_dataframe(df)
        return Portfolio(name=path.stem, assets=assets)

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to our internal format."""
        column_mapping = {}
        for internal_name, aliases in self.COLUMN_ALIASES.items():
            for alias in aliases:
                if alias in df.columns:
                    column_mapping[alias] = internal_name
                    break

        if column_mapping:
            df = df.rename(columns=column_mapping)
        return df

    def _parse_dataframe(self, df: pd.DataFrame) -> List[Asset]:
        """Parse a normalized DataFrame into Asset objects."""
        required = ["symbol", "name", "quantity", "purchase_price",
                     "purchase_date", "asset_type", "sector"]

        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}. "
                             f"Available columns: {list(df.columns)}")

        assets = []
        for idx, row in df.iterrows():
            try:
                # Parse date
                purchase_date = row["purchase_date"]
                if isinstance(purchase_date, str):
                    purchase_date = datetime.strptime(purchase_date, "%Y-%m-%d")

                asset = Asset(
                    symbol=str(row["symbol"]).strip(),
                    name=str(row["name"]).strip(),
                    quantity=float(row["quantity"]),
                    purchase_price=float(row["purchase_price"]),
                    purchase_date=purchase_date,
                    asset_type=self._parse_asset_type(str(row["asset_type"])),
                    sector=str(row["sector"]).strip(),
                )
                assets.append(asset)
            except Exception as e:
                logger.error(f"Error parsing row {idx}: {e}")
                raise

        return assets

    def _parse_asset_type(self, asset_type_str: str) -> AssetType:
        """Parse asset type string to AssetType enum."""
        mapping = {
            "equity": AssetType.EQUITY,
            "stock": AssetType.EQUITY,
            "crypto": AssetType.CRYPTO,
            "cryptocurrency": AssetType.CRYPTO,
            "debt": AssetType.DEBT,
            "bond": AssetType.DEBT,
            "commodity": AssetType.COMMODITY,
            "reit": AssetType.REIT,
            "cash": AssetType.CASH,
        }

        key = asset_type_str.strip().lower()
        if key in mapping:
            return mapping[key]
        raise ValueError(f"Unknown asset type: '{asset_type_str}'. "
                         f"Supported types: {list(mapping.keys())}")

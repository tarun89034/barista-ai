"""Portfolio parser for CSV and Excel files."""

import pandas as pd
from datetime import datetime
from typing import List
from pathlib import Path
import logging

from src.models.portfolio import Portfolio, Asset, AssetType

logger = logging.getLogger(__name__)


class PortfolioParser:
    def __init__(self):
        self.supported_formats = ['.csv', '.xlsx', '.xls']
    
    def parse_from_file(self, file_path: str) -> Portfolio:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if path.suffix == '.csv':
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        assets = self._parse_dataframe(df)
        return Portfolio(name=path.stem, assets=assets)
    
    def _parse_dataframe(self, df: pd.DataFrame) -> List[Asset]:
        required = ['symbol', 'name', 'quantity', 'purchase_price', 
                   'purchase_date', 'asset_type', 'sector']
        
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
        
        assets = []
        for idx, row in df.iterrows():
            try:
                if isinstance(row['purchase_date'], str):
                    purchase_date = datetime.strptime(row['purchase_date'], '%Y-%m-%d')
                else:
                    purchase_date = row['purchase_date']
                
                asset = Asset(
                    symbol=str(row['symbol']).strip(),
                    name=str(row['name']).strip(),
                    quantity=float(row['quantity']),
                    purchase_price=float(row['purchase_price']),
                    purchase_date=purchase_date,
                    asset_type=self._parse_asset_type(row['asset_type']),
                    sector=str(row['sector']).strip()
                )
                assets.append(asset)
            except Exception as e:
                logger.error(f"Error parsing row {idx}: {e}")
                raise
        
        return assets
    
    def _parse_asset_type(self, asset_type_str: str) -> AssetType:
        mapping = {
            'equity': AssetType.EQUITY,
            'stock': AssetType.EQUITY,
            'crypto': AssetType.CRYPTO,
            'cryptocurrency': AssetType.CRYPTO,
            'debt': AssetType.DEBT,
            'bond': AssetType.DEBT,
            'commodity': AssetType.COMMODITY,
            'reit': AssetType.REIT,
            'cash': AssetType.CASH
        }
        
        key = asset_type_str.strip().lower()
        if key in mapping:
            return mapping[key]
        raise ValueError(f"Unknown asset type: {asset_type_str}")

"""Data models for Barista AI portfolio management system."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class AssetType(str, Enum):
    """Asset type enumeration."""
    EQUITY = "Equity"
    CRYPTO = "Crypto"
    DEBT = "Debt"
    COMMODITY = "Commodity"
    REIT = "REIT"
    CASH = "Cash"


class Asset(BaseModel):
    """Model representing a single asset in the portfolio."""

    symbol: str = Field(..., description="Ticker symbol")
    name: str = Field(..., description="Full name of the asset")
    quantity: float = Field(..., gt=0, description="Number of shares/units")
    purchase_price: float = Field(..., gt=0, description="Purchase price per unit")
    purchase_date: datetime = Field(..., description="Purchase date")
    asset_type: AssetType = Field(..., description="Type of asset")
    sector: str = Field(..., description="Industry sector")
    current_price: Optional[float] = Field(None, description="Current market price")
    current_value: Optional[float] = Field(None, description="Current total value")

    @field_validator("purchase_date", mode="before")
    @classmethod
    def parse_date(cls, value):
        """Parse date string to datetime."""
        if isinstance(value, str):
            return datetime.strptime(value, "%Y-%m-%d")
        return value

    @property
    def purchase_value(self) -> float:
        """Calculate purchase value."""
        return self.quantity * self.purchase_price

    model_config = {"use_enum_values": True}


class Portfolio(BaseModel):
    """Model representing a portfolio of assets."""

    name: str = Field(default="My Portfolio", description="Portfolio name")
    assets: List[Asset] = Field(default_factory=list, description="List of assets")
    base_currency: str = Field(default="USD", description="Base currency")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def total_purchase_value(self) -> float:
        """Calculate total purchase value of portfolio."""
        return sum(asset.purchase_value for asset in self.assets)

    @property
    def total_current_value(self) -> float:
        """Calculate total current value of portfolio."""
        return sum(
            asset.current_value for asset in self.assets
            if asset.current_value is not None
        )

    def calculate_total_value(self) -> float:
        """Calculate and update current values for all assets."""
        for asset in self.assets:
            if asset.current_price is not None:
                asset.current_value = asset.quantity * asset.current_price
            elif asset.current_value is None:
                asset.current_value = asset.purchase_value
        return self.total_current_value

    def to_summary(self) -> Dict[str, Any]:
        """Generate a portfolio summary dict."""
        return {
            "name": self.name,
            "asset_count": len(self.assets),
            "total_purchase_value": self.total_purchase_value,
            "total_current_value": self.total_current_value,
            "base_currency": self.base_currency,
            "assets": [
                {
                    "symbol": a.symbol,
                    "name": a.name,
                    "asset_type": a.asset_type,
                    "quantity": a.quantity,
                    "purchase_price": a.purchase_price,
                    "current_price": a.current_price,
                    "current_value": a.current_value,
                    "sector": a.sector,
                }
                for a in self.assets
            ],
        }

    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()}
    }

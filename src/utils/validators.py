"""Data validation utilities for Barista AI."""

import re
import pandas as pd
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def validate_symbol(symbol: str) -> Tuple[bool, str]:
    """Validate if a symbol has valid format."""
    if not symbol or not isinstance(symbol, str):
        return False, "Symbol must be a non-empty string"
    
    symbol = symbol.strip()
    if len(symbol) == 0:
        return False, "Symbol cannot be empty"
    if len(symbol) > 10:
        return False, "Symbol is too long (max 10 characters)"
    if not re.match(r'^[A-Z0-9.\-]+$', symbol.upper()):
        return False, "Symbol contains invalid characters"
    
    return True, f"Symbol {symbol} is valid"

def validate_date_range(start_date: datetime, end_date: datetime) -> Tuple[bool, str]:
    """Validate date range."""
    if not isinstance(start_date, datetime):
        return False, "Start date must be a datetime object"
    if not isinstance(end_date, datetime):
        return False, "End date must be a datetime object"
    if start_date >= end_date:
        return False, "Start date must be before end date"
    if end_date > datetime.now():
        return False, "End date cannot be in the future"
    
    return True, "Date range is valid"

def validate_positive_number(value: float, name: str = "Value", 
                            allow_zero: bool = False) -> Tuple[bool, str]:
    """Validate that a number is positive."""
    try:
        value = float(value)
    except (ValueError, TypeError):
        return False, f"{name} must be a number"
    
    if allow_zero:
        if value < 0:
            return False, f"{name} must be non-negative"
    else:
        if value <= 0:
            return False, f"{name} must be positive"
    
    if not pd.notna(value):
        return False, f"{name} cannot be NaN"
    
    return True, f"{name} is valid"

def validate_percentage(value: float, name: str = "Percentage") -> Tuple[bool, str]:
    """Validate that a value is a valid percentage (0-100)."""
    try:
        value = float(value)
    except (ValueError, TypeError):
        return False, f"{name} must be a number"
    
    if not 0 <= value <= 100:
        return False, f"{name} must be between 0 and 100"
    
    return True, f"{name} is valid"

def validate_portfolio_data(df: pd.DataFrame) -> List[str]:
    """Validate portfolio DataFrame structure and data."""
    errors = []
    
    if df.empty:
        errors.append("Portfolio data is empty")
        return errors
    
    required_columns = ['symbol', 'name', 'quantity', 'purchase_price', 
                       'purchase_date', 'asset_type', 'sector']
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        return errors
    
    for idx, row in df.iterrows():
        row_prefix = f"Row {idx + 1}"
        
        is_valid, msg = validate_symbol(str(row['symbol']))
        if not is_valid:
            errors.append(f"{row_prefix}: {msg}")
        
        is_valid, msg = validate_positive_number(row['quantity'], "Quantity")
        if not is_valid:
            errors.append(f"{row_prefix}: {msg}")
        
        is_valid, msg = validate_positive_number(row['purchase_price'], "Purchase price")
        if not is_valid:
            errors.append(f"{row_prefix}: {msg}")
    
    return errors

def validate_api_key(api_key: str, key_name: str = "API key") -> Tuple[bool, str]:
    """Validate API key format."""
    if not api_key or not isinstance(api_key, str):
        return False, f"{key_name} must be a non-empty string"
    
    api_key = api_key.strip()
    if len(api_key) == 0:
        return False, f"{key_name} cannot be empty"
    if len(api_key) < 10:
        return False, f"{key_name} is too short"
    
    placeholder_patterns = ['your_', 'xxx', 'placeholder', 'replace']
    if any(pattern in api_key.lower() for pattern in placeholder_patterns):
        return False, f"{key_name} appears to be a placeholder"
    
    return True, f"{key_name} format is valid"

def validate_file_path(file_path: str, allowed_extensions: Optional[List[str]] = None) -> Tuple[bool, str]:
    """Validate file path and format."""
    if not file_path or not isinstance(file_path, str):
        return False, "File path must be a non-empty string"
    
    path = Path(file_path)
    if not path.exists():
        return False, f"File does not exist: {file_path}"
    if not path.is_file():
        return False, f"Path is not a file: {file_path}"
    
    if allowed_extensions:
        if path.suffix.lower() not in [ext.lower() for ext in allowed_extensions]:
            return False, f"File extension must be one of: {', '.join(allowed_extensions)}"
    
    return True, f"File path is valid"

def validate_confidence_level(confidence_level: float) -> Tuple[bool, str]:
    """Validate confidence level for risk calculations."""
    try:
        confidence_level = float(confidence_level)
    except (ValueError, TypeError):
        return False, "Confidence level must be a number"
    
    if not 0 < confidence_level < 1:
        return False, "Confidence level must be between 0 and 1"
    
    return True, f"Confidence level {confidence_level} is valid"
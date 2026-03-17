"""Market data routes: global indices, macro indicators, Indian market."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from functools import partial

from fastapi import APIRouter, HTTPException

from src.api.dependencies import get_app_state
from src.api.schemas import (
    GlobalIndicesResponse,
    MacroIndicatorsResponse,
    IndianMarketResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/global", response_model=GlobalIndicesResponse)
async def get_global_indices():
    """Get snapshot of major global market indices."""
    state = get_app_state()
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, state.data_fetcher.get_global_indices)
        return GlobalIndicesResponse(
            indices={k: v for k, v in data.items()},
        )
    except Exception as e:
        logger.error(f"Error fetching global indices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/macro", response_model=MacroIndicatorsResponse)
async def get_macro_indicators():
    """Get FRED macro economic indicators (Fed Funds Rate, 10Y Treasury, CPI, etc.)."""
    state = get_app_state()
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, state.data_fetcher.get_macro_indicators)
        if not data:
            return MacroIndicatorsResponse(
                status="unavailable",
                indicators={},
            )
        return MacroIndicatorsResponse(indicators=data)
    except Exception as e:
        logger.error(f"Error fetching macro indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indian", response_model=IndianMarketResponse)
async def get_indian_market():
    """Get Indian market data: NIFTY 50, SENSEX, and top NSE stocks."""
    state = get_app_state()
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, state.data_fetcher.get_indian_market)
        return IndianMarketResponse(
            indices=data.get("indices", {}),
            top_stocks=data.get("top_stocks", []),
        )
    except Exception as e:
        logger.error(f"Error fetching Indian market data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

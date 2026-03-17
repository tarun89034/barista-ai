"""Currency conversion routes: exchange rates and conversion."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from functools import partial

from fastapi import APIRouter, HTTPException, Query

from src.api.dependencies import get_app_state
from src.api.schemas import ExchangeRatesResponse, CurrencyConvertResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/currency", tags=["currency"])


@router.get("/rates", response_model=ExchangeRatesResponse)
async def get_exchange_rates(base: str = Query(default="USD", description="Base currency code")):
    """Get exchange rates relative to a base currency."""
    state = get_app_state()
    try:
        loop = asyncio.get_event_loop()
        rates = await loop.run_in_executor(
            None, partial(state.data_fetcher.get_exchange_rates, base.upper())
        )
        if rates is None:
            raise HTTPException(status_code=503, detail="Currency service unavailable")
        return ExchangeRatesResponse(base=base.upper(), rates=rates)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching exchange rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert", response_model=CurrencyConvertResponse)
async def convert_currency(
    from_currency: str = Query(alias="from", default="USD", description="Source currency"),
    to_currency: str = Query(alias="to", default="INR", description="Target currency"),
    amount: float = Query(default=1.0, gt=0, description="Amount to convert"),
):
    """Convert an amount between currencies."""
    state = get_app_state()
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            partial(state.data_fetcher.convert_currency, amount, from_currency.upper(), to_currency.upper()),
        )
        if result is None:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot convert {from_currency} to {to_currency}",
            )
        return CurrencyConvertResponse(
            **{
                "from": result["from"],
                "to": result["to"],
                "amount": result["amount"],
                "converted": result["converted"],
                "rate": result["rate"],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting currency: {e}")
        raise HTTPException(status_code=500, detail=str(e))

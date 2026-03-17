"""Portfolio management routes – upload, CRUD, enrichment."""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict

from fastapi import APIRouter, File, HTTPException, UploadFile

from src.api.dependencies import get_app_state
from src.api.schemas import (
    PortfolioCreate,
    PortfolioListResponse,
    PortfolioSummaryResponse,
)
from src.models.portfolio import Asset, Portfolio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


# ── Helpers ────────────────────────────────────────────────────────────────

def _portfolio_to_summary(pid: str, p: Portfolio) -> PortfolioSummaryResponse:
    summary = p.to_summary()
    return PortfolioSummaryResponse(
        portfolio_id=pid,
        name=summary["name"],
        asset_count=summary["asset_count"],
        total_purchase_value=summary["total_purchase_value"],
        total_current_value=summary["total_current_value"],
        base_currency=summary["base_currency"],
        assets=summary["assets"],
    )


# ── Routes ─────────────────────────────────────────────────────────────────

@router.get("", response_model=PortfolioListResponse)
async def list_portfolios():
    """List all portfolios currently loaded in memory."""
    state = get_app_state()
    items = [
        _portfolio_to_summary(pid, p)
        for pid, p in state.portfolios.items()
    ]
    return PortfolioListResponse(portfolios=items, count=len(items))


@router.get("/{portfolio_id}", response_model=PortfolioSummaryResponse)
async def get_portfolio(portfolio_id: str):
    """Get a single portfolio by ID."""
    state = get_app_state()
    if portfolio_id not in state.portfolios:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return _portfolio_to_summary(portfolio_id, state.portfolios[portfolio_id])


@router.post("", response_model=PortfolioSummaryResponse, status_code=201)
async def create_portfolio(body: PortfolioCreate):
    """Create a portfolio from JSON payload and enrich with live prices."""
    state = get_app_state()
    try:
        assets = [Asset(**a.model_dump()) for a in body.assets]
        portfolio = Portfolio(
            name=body.name,
            assets=assets,
            base_currency=body.base_currency,
        )

        # Enrich with live prices
        symbols = [a.symbol for a in portfolio.assets]
        prices = state.data_fetcher.get_multiple_prices(symbols)
        for asset in portfolio.assets:
            if asset.symbol in prices and prices[asset.symbol] is not None:
                asset.current_price = prices[asset.symbol]
        portfolio.calculate_total_value()

        pid = str(uuid.uuid4())[:8]
        state.portfolios[pid] = portfolio
        logger.info(f"Created portfolio '{portfolio.name}' with id={pid}")
        return _portfolio_to_summary(pid, portfolio)

    except Exception as e:
        logger.error(f"Error creating portfolio: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload", response_model=PortfolioSummaryResponse, status_code=201)
async def upload_portfolio(file: UploadFile = File(...)):
    """Upload a CSV/Excel portfolio file, parse and enrich it."""
    state = get_app_state()

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".csv", ".xlsx", ".xls"):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")

    # Save to temp location
    tmp_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "uploads")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, f"{uuid.uuid4().hex[:8]}_{file.filename}")

    try:
        contents = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(contents)

        portfolio = state.portfolio_reader.process(tmp_path, enrich_with_prices=True)
        pid = str(uuid.uuid4())[:8]
        state.portfolios[pid] = portfolio

        logger.info(f"Uploaded portfolio '{portfolio.name}' with id={pid}")
        return _portfolio_to_summary(pid, portfolio)

    except Exception as e:
        logger.error(f"Error uploading portfolio: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/load-sample", response_model=PortfolioSummaryResponse, status_code=201)
async def load_sample_portfolio():
    """Load the built-in sample portfolio (data/sample_portfolio.csv)."""
    state = get_app_state()
    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "sample_portfolio.csv")
    sample_path = os.path.normpath(sample_path)

    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="Sample portfolio file not found")

    try:
        portfolio = state.portfolio_reader.process(sample_path, enrich_with_prices=True)
        pid = str(uuid.uuid4())[:8]
        state.portfolios[pid] = portfolio
        logger.info(f"Loaded sample portfolio with id={pid}")
        return _portfolio_to_summary(pid, portfolio)
    except Exception as e:
        logger.error(f"Error loading sample portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{portfolio_id}")
async def delete_portfolio(portfolio_id: str):
    """Delete a portfolio from memory."""
    state = get_app_state()
    if portfolio_id not in state.portfolios:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    del state.portfolios[portfolio_id]
    return {"status": "deleted", "portfolio_id": portfolio_id}

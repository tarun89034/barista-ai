"""Analysis routes – risk, market monitoring, rebalancing, LLM insights."""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from src.api.dependencies import get_app_state
from src.api.schemas import (
    FullAnalysisRequest,
    FullAnalysisResponse,
    LLMInsightRequest,
    LLMInsightResponse,
    LLMRiskAdviceRequest,
    LLMRiskAdviceResponse,
    MarketMonitorRequest,
    MarketMonitorResponse,
    RebalancingRequest,
    RebalancingResponse,
    RiskAnalysisRequest,
    RiskAnalysisResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_portfolio(portfolio_id: str):
    state = get_app_state()
    if portfolio_id not in state.portfolios:
        raise HTTPException(status_code=404, detail="Portfolio not found. Load a portfolio first.")
    return state.portfolios[portfolio_id]


# ── Risk Analysis ──────────────────────────────────────────────────────────

@router.post("/risk", response_model=RiskAnalysisResponse)
async def run_risk_analysis(body: RiskAnalysisRequest):
    """Run risk analysis on a loaded portfolio."""
    state = get_app_state()
    portfolio = _get_portfolio(body.portfolio_id)

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, partial(state.risk_analyzer.process, portfolio, period=body.period)
        )
        return RiskAnalysisResponse(
            status="success",
            portfolio_name=result.get("portfolio_name", portfolio.name),
            analysis_period=result.get("analysis_period", body.period),
            timestamp=result.get("timestamp", ""),
            portfolio_metrics=result.get("portfolio_metrics", {}),
            asset_metrics=result.get("asset_metrics", []),
            risk_summary=result.get("risk_summary", {}),
        )
    except Exception as e:
        logger.error(f"Risk analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Market Monitoring ──────────────────────────────────────────────────────

@router.post("/market", response_model=MarketMonitorResponse)
async def run_market_monitor(body: MarketMonitorRequest):
    """Run market monitoring to get current prices and alerts."""
    state = get_app_state()
    portfolio = _get_portfolio(body.portfolio_id)

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, partial(state.market_monitor.process, portfolio)
        )
        return MarketMonitorResponse(
            status="success",
            portfolio_name=result.get("portfolio_name", portfolio.name),
            timestamp=result.get("timestamp", ""),
            current_prices=result.get("current_prices", {}),
            alerts=result.get("alerts", []),
            alert_count=result.get("alert_count", 0),
            market_conditions=result.get("market_conditions", {}),
        )
    except Exception as e:
        logger.error(f"Market monitoring failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Rebalancing ────────────────────────────────────────────────────────────

@router.post("/rebalancing", response_model=RebalancingResponse)
async def run_rebalancing(body: RebalancingRequest):
    """Run rebalancing analysis on a loaded portfolio."""
    state = get_app_state()
    portfolio = _get_portfolio(body.portfolio_id)

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            partial(state.rebalancing_advisor.process, portfolio, risk_profile=body.risk_profile),
        )
        return RebalancingResponse(
            status="success",
            portfolio_name=result.get("portfolio_name", portfolio.name),
            risk_profile=result.get("risk_profile", body.risk_profile),
            total_value=result.get("total_value", 0),
            timestamp=result.get("timestamp", ""),
            current_allocation=result.get("current_allocation", {}),
            target_allocation=result.get("target_allocation", {}),
            drift_analysis=result.get("drift_analysis", {}),
            needs_rebalancing=result.get("needs_rebalancing", False),
            recommendations=result.get("recommendations", []),
            llm_reasoning=result.get("llm_reasoning"),
        )
    except Exception as e:
        logger.error(f"Rebalancing analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Full Analysis ──────────────────────────────────────────────────────────

@router.post("/full", response_model=FullAnalysisResponse)
async def run_full_analysis(body: FullAnalysisRequest):
    """Run the complete analysis pipeline (risk + market + rebalancing + LLM)."""
    state = get_app_state()
    portfolio = _get_portfolio(body.portfolio_id)

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                state.orchestrator.run_full_analysis,
                {
                    "portfolio": portfolio,
                    "period": body.period,
                    "risk_profile": body.risk_profile,
                },
            ),
        )

        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "Analysis failed"))

        return FullAnalysisResponse(
            status="success",
            workflow="full_analysis",
            timestamp=result.get("timestamp", ""),
            portfolio=result.get("portfolio", {}),
            risk_analysis=result.get("risk_analysis", {}),
            market_monitoring=result.get("market_monitoring", {}),
            rebalancing=result.get("rebalancing", {}),
            llm_summary=result.get("llm_summary"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Full analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── LLM Insights ──────────────────────────────────────────────────────────

@router.post("/insights", response_model=LLMInsightResponse)
async def get_llm_insights(body: LLMInsightRequest):
    """Get AI-generated portfolio insights from Gemini."""
    state = get_app_state()
    portfolio = _get_portfolio(body.portfolio_id)

    if not state.llm_service or not state.llm_service.available:
        return LLMInsightResponse(
            status="unavailable",
            message="Gemini LLM service not configured. Set GEMINI_API_KEY in .env",
        )

    try:
        loop = asyncio.get_event_loop()
        risk_data = None
        if body.include_risk:
            risk_data = await loop.run_in_executor(
                None, partial(state.risk_analyzer.process, portfolio)
            )

        insight = await loop.run_in_executor(
            None,
            partial(state.llm_service.generate_portfolio_insights, portfolio.to_summary(), risk_data),
        )
        return LLMInsightResponse(status="success", insight=insight)
    except Exception as e:
        logger.error(f"LLM insight generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk-advice", response_model=LLMRiskAdviceResponse)
async def get_risk_advice(body: LLMRiskAdviceRequest):
    """Get AI-generated risk advice from Gemini."""
    state = get_app_state()
    portfolio = _get_portfolio(body.portfolio_id)

    if not state.llm_service or not state.llm_service.available:
        return LLMRiskAdviceResponse(
            status="unavailable",
            message="Gemini LLM service not configured. Set GEMINI_API_KEY in .env",
        )

    try:
        loop = asyncio.get_event_loop()
        risk_result = await loop.run_in_executor(
            None, partial(state.risk_analyzer.process, portfolio, period=body.period)
        )
        advice = await loop.run_in_executor(
            None,
            partial(state.llm_service.provide_risk_advice, risk_result.get("portfolio_metrics", {})),
        )
        return LLMRiskAdviceResponse(status="success", advice=advice)
    except Exception as e:
        logger.error(f"Risk advice generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

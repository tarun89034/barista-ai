"""WebSocket route for real-time market data streaming."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.dependencies import get_app_state

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manage active WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active_connections.add(ws)
        logger.info(f"WebSocket connected. Active: {len(self.active_connections)}")

    def disconnect(self, ws: WebSocket) -> None:
        self.active_connections.discard(ws)
        logger.info(f"WebSocket disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, data: Dict[str, Any]) -> None:
        """Send data to all connected clients."""
        dead: list[WebSocket] = []
        for ws in self.active_connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active_connections.discard(ws)


manager = ConnectionManager()


@router.websocket("/ws/market/{portfolio_id}")
async def market_stream(ws: WebSocket, portfolio_id: str):
    """Stream real-time market updates for a portfolio.

    Sends price snapshots at the configured interval (default 30s).
    Clients can send JSON messages:
        {"action": "refresh"}  - force an immediate update
        {"action": "stop"}     - close the connection
    """
    state = get_app_state()
    update_interval = state.settings.price_update_interval
    if portfolio_id not in state.portfolios:
        await ws.close(code=4004, reason="Portfolio not found")
        return

    await manager.connect(ws)

    try:
        portfolio = state.portfolios[portfolio_id]

        # Send initial snapshot immediately
        snapshot = _build_snapshot(state, portfolio)
        await ws.send_json(snapshot)

        while True:
            # Wait for either a client message or the refresh interval
            try:
                msg_text = await asyncio.wait_for(ws.receive_text(), timeout=float(update_interval))
                try:
                    msg = json.loads(msg_text)
                except json.JSONDecodeError:
                    msg = {}

                action = msg.get("action", "")
                if action == "stop":
                    break
                elif action == "refresh":
                    # Re-read portfolio in case it was updated
                    if portfolio_id in state.portfolios:
                        portfolio = state.portfolios[portfolio_id]
                    snapshot = _build_snapshot(state, portfolio)
                    await ws.send_json(snapshot)
            except asyncio.TimeoutError:
                # Periodic refresh
                if portfolio_id in state.portfolios:
                    portfolio = state.portfolios[portfolio_id]
                snapshot = _build_snapshot(state, portfolio)
                await ws.send_json(snapshot)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(ws)


def _build_snapshot(state, portfolio) -> Dict[str, Any]:
    """Build a price snapshot using the market monitor agent."""
    try:
        result = state.market_monitor.process(portfolio)
        return {
            "type": "market_update",
            "timestamp": datetime.now().isoformat(),
            "portfolio_name": portfolio.name,
            "current_prices": result.get("current_prices", {}),
            "alerts": result.get("alerts", []),
            "alert_count": result.get("alert_count", 0),
            "market_conditions": result.get("market_conditions", {}),
        }
    except Exception as e:
        logger.error(f"Error building snapshot: {e}")
        return {
            "type": "error",
            "timestamp": datetime.now().isoformat(),
            "message": str(e),
        }

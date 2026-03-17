"""FastAPI application factory for Barista AI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.api.dependencies import get_app_state
from src.api.schemas import AgentStatusResponse, HealthResponse
from src.config.config import get_settings

logger = logging.getLogger(__name__)

# Path to the Next.js static export (built by `npm run build` in frontend/)
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "out"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle handler."""
    logger.info("Barista AI API starting up...")
    # Eagerly initialise shared state (agents, services)
    state = get_app_state()
    logger.info("All agents initialised. API ready.")
    if FRONTEND_DIR.is_dir():
        logger.info("Frontend static files found at %s", FRONTEND_DIR)
    else:
        logger.warning(
            "Frontend static files NOT found at %s — only the API will be served. "
            "Run `cd frontend && npm run build` to generate them.",
            FRONTEND_DIR,
        )
    yield
    logger.info("Barista AI API shutting down...")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Barista AI – Portfolio Risk Management",
        description=(
            "Multi-agent AI system for portfolio analysis, risk management, "
            "market monitoring, and rebalancing recommendations."
        ),
        version="1.0.0",
        docs_url="/docs" if settings.api_docs_enabled else None,
        redoc_url="/redoc" if settings.api_docs_enabled else None,
        lifespan=lifespan,
    )

    # ── CORS ───────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Routes ─────────────────────────────────────────────────────
    from src.api.routes.portfolio import router as portfolio_router
    from src.api.routes.analysis import router as analysis_router
    from src.api.routes.websocket import router as ws_router
    from src.api.routes.market import router as market_router
    from src.api.routes.currency import router as currency_router

    app.include_router(portfolio_router, prefix="/api/v1")
    app.include_router(analysis_router, prefix="/api/v1")
    app.include_router(ws_router, prefix="/api/v1")
    app.include_router(market_router, prefix="/api/v1")
    app.include_router(currency_router, prefix="/api/v1")

    # ── Health / Status endpoints ──────────────────────────────────────

    @app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
    async def health():
        return HealthResponse()

    @app.get("/api/v1/agents/status", response_model=AgentStatusResponse, tags=["agents"])
    async def agent_status():
        state = get_app_state()
        return AgentStatusResponse(agents=state.orchestrator.get_agent_status())

    # ── Frontend static file serving ───────────────────────────────────
    # Serve the Next.js static export so the entire app is a single process.
    # The _next/ directory contains hashed JS/CSS chunks.
    if FRONTEND_DIR.is_dir():
        next_assets = FRONTEND_DIR / "_next"
        if next_assets.is_dir():
            app.mount(
                "/_next",
                StaticFiles(directory=str(next_assets)),
                name="next-assets",
            )

        # Serve favicon
        @app.get("/favicon.ico", include_in_schema=False)
        async def favicon():
            fav = FRONTEND_DIR / "favicon.ico"
            if fav.is_file():
                return FileResponse(str(fav))
            return HTMLResponse("", status_code=404)

        # Catch-all: serve pre-rendered HTML pages from the static export.
        # This MUST be registered last so it doesn't shadow API routes.
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_frontend(request: Request, full_path: str):
            # Ignore API paths (shouldn't reach here, but guard anyway)
            if full_path.startswith("api/"):
                return HTMLResponse("Not Found", status_code=404)

            # Try exact file first (e.g. "robots.txt")
            candidate = FRONTEND_DIR / full_path
            if candidate.is_file():
                return FileResponse(str(candidate))

            # Try directory index (e.g. "/risk" -> "/risk/index.html")
            candidate_dir = FRONTEND_DIR / full_path / "index.html"
            if candidate_dir.is_file():
                return FileResponse(str(candidate_dir))

            # Fall back to root index.html (SPA client-side routing)
            root_index = FRONTEND_DIR / "index.html"
            if root_index.is_file():
                return FileResponse(str(root_index))

            return HTMLResponse("Not Found", status_code=404)

    return app

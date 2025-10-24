# apps/api/main.py
from __future__ import annotations

import os
import logging
from typing import Iterable

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from apps.api.routers.optimize import router as optimize_router
from apps.api.routers.health import router as health_router

# Any top-level prefixes that should NOT be captured by the SPA fallback.
SPA_EXCLUDE_PREFIXES: tuple[str, ...] = (
    "optimize",
    "assets",
    "api",
    "health",
    "version",
)


def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("api")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("[API] %(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(h)
    logger.propagate = False
    return logger


def _is_spa_excluded(path: str, exclude_prefixes: Iterable[str]) -> bool:
    clean = path.lstrip("/")
    head = clean.split("/", 1)[0] if clean else ""
    return head in exclude_prefixes


def create_app() -> FastAPI:
    app = FastAPI(title="Demonized Orb Optimizer API", version="1.0.0")

    # ---- Logger ----
    logger = _setup_logger()
    app.state.logger = logger

    # ---- Middleware ----
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    # ---- Routers ----
    app.include_router(optimize_router, tags=["optimize"])
    app.include_router(health_router, tags=["meta"])

    # ---- Frontend (static) ----
    dist = os.getenv("FRONTEND_DIST", "")
    if dist and os.path.isdir(dist):
        assets_dir = os.path.join(dist, "assets")
        if os.path.isdir(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        index_file = os.path.join(dist, "index.html")

        # NOTE: don't annotate return type with a union of response classes.
        @app.get("/", include_in_schema=False, response_model=None)
        async def index():
            if os.path.isfile(index_file):
                return FileResponse(index_file)
            return PlainTextResponse("Frontend not built", status_code=503)

        @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
        async def spa_fallback(full_path: str, request: Request):
            # Don't intercept API/health/etc.
            if _is_spa_excluded(full_path, SPA_EXCLUDE_PREFIXES):
                return JSONResponse({"error": "Not found"}, status_code=404)
            if os.path.isfile(index_file):
                return FileResponse(index_file)
            return JSONResponse({"error": "Frontend not available"}, status_code=503)

        logger.info("Frontend mounted from %s", dist)
    else:
        logger.warning("FRONTEND_DIST not set or missing. API will run without serving the UI.")

    return app


app = create_app()

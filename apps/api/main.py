# apps/api/main.py
from __future__ import annotations

import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers import health, optimize


def create_app() -> FastAPI:
    app = FastAPI(title="Orb Optimizer API", version="0.1.0")

    # ---------- Logging ----------
    # Create a logger specifically for the API layer
    logger = logging.getLogger("orb_api")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[API] %(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # FastAPI uses uvicorn’s logger; we can adjust its format slightly if desired
    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.handlers.clear()
    uvicorn_logger.addHandler(handler)

    # Store the logger on the app so routers can access it
    app.state.logger = logger
    logger.info("🛰️  Orb Optimizer API starting up...")

    # ---------- Routers ----------
    app.include_router(health.router, prefix="", tags=["health"])
    app.include_router(optimize.router, prefix="", tags=["optimize"])

    # ---------- CORS ----------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------- Optional static build ----------
    build_dir = Path(__file__).resolve().parents[2] / "web" / "dist"
    if build_dir.exists():
        app.mount("/assets", StaticFiles(directory=build_dir / "assets"), name="assets")
        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            from fastapi.responses import FileResponse
            return FileResponse(build_dir / "index.html")

    return app


app = create_app()

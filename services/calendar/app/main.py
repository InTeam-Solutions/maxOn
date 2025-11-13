from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request

from app.config import Settings, get_settings
from app.db import init_db
from app.routes import calendars as calendars_routes
from app.routes import events as events_routes
from app.routes import ics as ics_routes


def create_app(*, override_settings: Optional[Settings] = None, skip_db_init: bool = False) -> FastAPI:
    settings = override_settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not skip_db_init:
            await init_db()
        yield

    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    logger = logging.getLogger("calendar-service")

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %s (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        return response

    app.include_router(calendars_routes.router)
    app.include_router(ics_routes.router)
    app.include_router(events_routes.router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

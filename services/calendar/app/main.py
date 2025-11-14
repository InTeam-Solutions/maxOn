from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request

from app.config import Settings, get_settings
from app.db import init_db, get_session
from app.routes import calendars as calendars_routes
from app.routes import events as events_routes
from app.routes import ics as ics_routes
from app.services import external_calendars as external_calendars_service


async def sync_external_calendars_task():
    """Background task to sync external calendars every 10 seconds."""
    logger = logging.getLogger("calendar-service.sync")
    logger.info("Starting external calendar sync task")

    while True:
        try:
            await asyncio.sleep(10)  # Wait 10 seconds

            async for session in get_session():
                try:
                    calendars = await external_calendars_service.get_external_calendars_for_sync(session)
                    logger.info(f"Syncing {len(calendars)} external calendars")

                    for ext_cal in calendars:
                        try:
                            result = await external_calendars_service.sync_external_calendar(session, ext_cal)
                            logger.info(
                                f"Synced calendar {ext_cal.id}: "
                                f"+{result.events_added} -{result.events_removed} ~{result.events_updated}"
                            )
                        except Exception as e:
                            logger.error(f"Error syncing calendar {ext_cal.id}: {e}")
                except Exception as e:
                    logger.error(f"Error in sync iteration: {e}")
        except Exception as e:
            logger.error(f"Error in sync task: {e}")
            await asyncio.sleep(10)


def create_app(*, override_settings: Optional[Settings] = None, skip_db_init: bool = False) -> FastAPI:
    settings = override_settings or get_settings()
    sync_task = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal sync_task
        if not skip_db_init:
            await init_db()

        # Start background sync task
        sync_task = asyncio.create_task(sync_external_calendars_task())

        yield

        # Cancel background task on shutdown
        if sync_task:
            sync_task.cancel()
            try:
                await sync_task
            except asyncio.CancelledError:
                pass

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

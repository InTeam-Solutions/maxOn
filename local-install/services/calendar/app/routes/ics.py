from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_session
from app.services import calendars as calendars_service
from app.services import ics as ics_service

router = APIRouter(tags=["ics"])


@router.get("/calendar/{public_token}.ics", response_class=Response)
async def download_ics(
    public_token: str,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    calendar = await calendars_service.get_calendar_by_token(session, public_token)
    if calendar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    events = await ics_service.fetch_events_for_feed(session, calendar.id, settings)
    payload = ics_service.build_ics(calendar, events, settings)

    response = Response(content=payload, media_type="text/calendar; charset=utf-8")
    response.headers["Content-Disposition"] = f"attachment; filename=calendar-{calendar.id}.ics"
    response.headers["Cache-Control"] = f"public, max-age={settings.ics_cache_seconds}"
    response.headers["ETag"] = hashlib.sha256(payload).hexdigest()
    return response

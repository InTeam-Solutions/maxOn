from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.db import get_session
from app.services import calendars as calendars_service
from app.services import events as events_service

router = APIRouter(prefix="/api/calendars", tags=["events"])


@router.post(
    "/{calendar_id}/events",
    response_model=schemas.EventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_event(
    calendar_id: UUID,
    payload: schemas.EventCreate,
    session: AsyncSession = Depends(get_session),
) -> schemas.EventResponse:
    calendar = await calendars_service.get_calendar(session, calendar_id)
    if calendar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    event = await events_service.create_event(session, calendar=calendar, payload=payload)
    return schemas.EventResponse.model_validate(event)


@router.get("/{calendar_id}/events", response_model=list[schemas.EventResponse])
async def list_events(
    calendar_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[schemas.EventResponse]:
    calendar = await calendars_service.get_calendar(session, calendar_id)
    if calendar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    events = await events_service.list_events(session, calendar_id)
    return [schemas.EventResponse.model_validate(event) for event in events]

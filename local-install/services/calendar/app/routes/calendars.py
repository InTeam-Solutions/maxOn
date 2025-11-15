from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.config import Settings, get_settings
from app.db import get_session
from app.services import calendars as calendars_service
from app.services import external_calendars as external_calendars_service

router = APIRouter(prefix="/api/calendars", tags=["calendars"])


@router.post("/", response_model=schemas.CalendarResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar(
    payload: schemas.CalendarCreate,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> schemas.CalendarResponse:
    calendar = await calendars_service.create_calendar(
        session, name=payload.name, user_id=payload.user_id
    )
    return schemas.CalendarResponse(
        id=calendar.id,
        user_id=calendar.user_id,
        name=calendar.name,
        public_ics_url=settings.build_public_ics_url(calendar.public_token),
    )


@router.get("/users/{user_id}/calendar", response_model=schemas.CalendarResponse)
async def get_calendar_for_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> schemas.CalendarResponse:
    calendar = await calendars_service.get_calendar_by_user(session, user_id=user_id)
    if calendar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")
    return schemas.CalendarResponse(
        id=calendar.id,
        user_id=calendar.user_id,
        name=calendar.name,
        public_ics_url=settings.build_public_ics_url(calendar.public_token),
    )


@router.post("/users/{user_id}/calendar", response_model=schemas.CalendarResponse)
async def ensure_calendar_for_user(
    user_id: int,
    payload: schemas.CalendarEnsureRequest | None = None,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> schemas.CalendarResponse:
    calendar = await calendars_service.ensure_calendar(
        session,
        user_id=user_id,
        name=payload.name if payload else None,
    )
    return schemas.CalendarResponse(
        id=calendar.id,
        user_id=calendar.user_id,
        name=calendar.name,
        public_ics_url=settings.build_public_ics_url(calendar.public_token),
    )


@router.get("/{calendar_id}", response_model=schemas.CalendarDetailResponse)
async def get_calendar(
    calendar_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> schemas.CalendarDetailResponse:
    calendar = await calendars_service.get_calendar(session, calendar_id)
    if calendar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    events = await calendars_service.list_events_for_calendar(session, calendar_id)
    return schemas.CalendarDetailResponse(
        id=calendar.id,
        user_id=calendar.user_id,
        name=calendar.name,
        public_ics_url=settings.build_public_ics_url(calendar.public_token),
        events=[schemas.EventResponse.model_validate(event) for event in events],
    )


@router.post("/users/{user_id}/external")
async def add_external_calendar(
    user_id: int,
    payload: schemas.ExternalCalendarCreate,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Add an external calendar subscription and sync it."""
    # Ensure user has a calendar
    calendar = await calendars_service.ensure_calendar(session, user_id=user_id)

    # Create external calendar
    external_calendar = await external_calendars_service.create_external_calendar(
        session, calendar.id, payload
    )

    # Sync immediately
    try:
        sync_result = await external_calendars_service.sync_external_calendar(
            session, external_calendar
        )
        return {
            "external_calendar_id": str(external_calendar.id),
            "events_synced": sync_result.events_added,
            "message": "External calendar added and synced successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to sync external calendar: {str(e)}"
        )

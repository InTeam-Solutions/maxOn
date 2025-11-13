from __future__ import annotations

from datetime import timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.schemas import EventCreate


async def create_event(
    session: AsyncSession,
    *,
    calendar: models.Calendar,
    payload: EventCreate,
) -> models.Event:
    start_dt = payload.start_datetime.astimezone(timezone.utc)
    end_dt = start_dt + timedelta(minutes=payload.duration_minutes)

    event = models.Event(
        calendar_id=calendar.id,
        title=payload.title,
        brief_description=payload.brief_description,
        start_datetime=start_dt,
        end_datetime=end_dt,
        duration_minutes=payload.duration_minutes,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def get_event(session: AsyncSession, event_id: UUID) -> Optional[models.Event]:
    result = await session.execute(select(models.Event).where(models.Event.id == event_id))
    return result.scalar_one_or_none()


async def list_events(session: AsyncSession, calendar_id: UUID) -> list[models.Event]:
    result = await session.execute(
        select(models.Event)
        .where(models.Event.calendar_id == calendar_id)
        .order_by(models.Event.start_datetime)
    )
    return list(result.scalars())

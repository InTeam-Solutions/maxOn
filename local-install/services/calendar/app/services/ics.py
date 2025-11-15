from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable
from uuid import UUID

from icalendar import Calendar, Event
from urllib.parse import urlparse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.config import Settings


async def fetch_events_for_feed(
    session: AsyncSession,
    calendar_id: UUID,
    settings: Settings,
) -> list[models.Event]:
    now = datetime.now(timezone.utc)
    stmt = select(models.Event).where(models.Event.calendar_id == calendar_id)

    if settings.ics_past_days is not None:
        earliest = now - timedelta(days=settings.ics_past_days)
        stmt = stmt.where(models.Event.end_datetime >= earliest)
    if settings.ics_future_days is not None:
        latest = now + timedelta(days=settings.ics_future_days)
        stmt = stmt.where(models.Event.start_datetime <= latest)

    stmt = stmt.order_by(models.Event.start_datetime)
    result = await session.execute(stmt)
    return list(result.scalars())


def build_ics(calendar: models.Calendar, events: Iterable[models.Event], settings: Settings) -> bytes:
    feed = Calendar()
    feed.add("prodid", f"-//{settings.app_name}//Calendar Feed//EN")
    feed.add("version", "2.0")
    feed.add("calscale", "GREGORIAN")

    for event in events:
        feed.add_component(_event_component(event, settings))

    return feed.to_ical()


def _event_component(event: models.Event, settings: Settings) -> Event:
    component = Event()
    parsed = urlparse(settings.public_base_url)
    host = parsed.netloc or parsed.path or "maxon-calendar"
    component.add("uid", f"{event.id}@{host}")
    component.add("dtstamp", event.created_at or datetime.now(timezone.utc))
    component.add("dtstart", event.start_datetime)
    component.add("dtend", event.end_datetime)
    component.add("summary", event.title)
    if event.brief_description:
        component.add("description", event.brief_description)
    component.add("status", event.status or "CONFIRMED")
    return component

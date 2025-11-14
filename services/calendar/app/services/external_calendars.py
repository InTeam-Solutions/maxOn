from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import httpx
from icalendar import Calendar as ICalendar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas

logger = logging.getLogger(__name__)


async def create_external_calendar(
    session: AsyncSession,
    calendar_id: UUID,
    data: schemas.ExternalCalendarCreate,
) -> models.ExternalCalendar:
    """Create a new external calendar subscription."""
    external_calendar = models.ExternalCalendar(
        calendar_id=calendar_id,
        url=data.url,
        name=data.name,
    )
    session.add(external_calendar)
    await session.commit()
    await session.refresh(external_calendar)
    return external_calendar


async def sync_external_calendar(
    session: AsyncSession,
    external_calendar: models.ExternalCalendar,
) -> schemas.ExternalCalendarSyncResult:
    """Fetch and sync events from an external calendar."""
    try:
        # Fetch the ICS file
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(external_calendar.url)
            response.raise_for_status()
            ics_content = response.content

        # Parse the ICS file
        cal = ICalendar.from_ical(ics_content)

        # Get calendar name if not set
        if not external_calendar.name:
            calendar_name = cal.get("x-wr-calname") or cal.get("name")
            if calendar_name:
                external_calendar.name = str(calendar_name)

        # Track sync stats
        events_added = 0
        events_updated = 0
        events_removed = 0

        # Get existing events from this external calendar
        stmt = select(models.Event).where(
            models.Event.external_calendar_id == external_calendar.id
        )
        result = await session.execute(stmt)
        existing_events = {e.external_event_uid: e for e in result.scalars()}

        # Process events from the ICS file
        seen_uids = set()
        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            try:
                uid = str(component.get("uid", ""))
                if not uid:
                    continue

                seen_uids.add(uid)

                # Parse event data
                title = str(component.get("summary", "Untitled Event"))
                description = component.get("description")
                brief_description = str(description) if description else None

                # Get start and end times
                dtstart = component.get("dtstart").dt
                dtend = component.get("dtend")

                # Handle all-day events
                if isinstance(dtstart, datetime):
                    start_datetime = dtstart
                    if start_datetime.tzinfo is None:
                        start_datetime = start_datetime.replace(tzinfo=timezone.utc)
                else:
                    # All-day event - convert date to datetime
                    start_datetime = datetime.combine(
                        dtstart, datetime.min.time()
                    ).replace(tzinfo=timezone.utc)

                if dtend:
                    end_dt = dtend.dt
                    if isinstance(end_dt, datetime):
                        end_datetime = end_dt
                        if end_datetime.tzinfo is None:
                            end_datetime = end_datetime.replace(tzinfo=timezone.utc)
                    else:
                        end_datetime = datetime.combine(
                            end_dt, datetime.min.time()
                        ).replace(tzinfo=timezone.utc)
                else:
                    # If no end time, default to 1 hour duration
                    from datetime import timedelta
                    end_datetime = start_datetime + timedelta(hours=1)

                duration_minutes = int((end_datetime - start_datetime).total_seconds() / 60)

                # Create or update event
                if uid in existing_events:
                    # Update existing event
                    event = existing_events[uid]
                    event.title = title
                    event.brief_description = brief_description
                    event.start_datetime = start_datetime
                    event.end_datetime = end_datetime
                    event.duration_minutes = duration_minutes
                    events_updated += 1
                else:
                    # Create new event
                    event = models.Event(
                        calendar_id=external_calendar.calendar_id,
                        external_calendar_id=external_calendar.id,
                        external_event_uid=uid,
                        title=title,
                        brief_description=brief_description,
                        start_datetime=start_datetime,
                        end_datetime=end_datetime,
                        duration_minutes=duration_minutes,
                        status="CONFIRMED",
                    )
                    session.add(event)
                    events_added += 1

            except Exception as e:
                logger.error(f"Error processing event: {e}")
                continue

        # Remove events that no longer exist in the external calendar
        for uid, event in existing_events.items():
            if uid not in seen_uids:
                await session.delete(event)
                events_removed += 1

        # Update last synced time
        external_calendar.last_synced_at = datetime.now(timezone.utc)

        await session.commit()

        return schemas.ExternalCalendarSyncResult(
            external_calendar_id=external_calendar.id,
            events_synced=len(seen_uids),
            events_added=events_added,
            events_updated=events_updated,
            events_removed=events_removed,
        )

    except Exception as e:
        logger.error(f"Error syncing external calendar {external_calendar.id}: {e}")
        raise


async def get_external_calendars_for_sync(
    session: AsyncSession,
) -> list[models.ExternalCalendar]:
    """Get all active external calendars that need syncing."""
    stmt = select(models.ExternalCalendar).where(
        models.ExternalCalendar.is_active == True
    )
    result = await session.execute(stmt)
    return list(result.scalars())

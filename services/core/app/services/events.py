from typing import List, Dict, Any, Optional
from datetime import date as date_type, time as time_type
from dateutil import parser as dtparser
from sqlalchemy.orm import Session

from app.models.event import Event


def parse_date(date_str: str) -> date_type:
    """Parse date string to date object"""
    return dtparser.parse(date_str).date()


def parse_time(time_str: Optional[str]) -> Optional[time_type]:
    """Parse time string to time object"""
    if not time_str:
        return None
    t = dtparser.parse(time_str).time()
    return t.replace(second=0, microsecond=0)


def create_event(
    session: Session,
    user_id: str,
    title: str,
    date: str,
    time: Optional[str] = None,
    repeat: Optional[str] = None,
    notes: Optional[str] = None,
    event_type: Optional[str] = "user",
    linked_step_id: Optional[int] = None,
    linked_goal_id: Optional[int] = None
) -> Dict[str, Any]:
    """Create a new event"""
    event = Event(
        user_id=user_id,
        title=title.strip(),
        date=parse_date(date),
        time=parse_time(time),
        repeat=repeat,
        notes=notes,
        event_type=event_type,
        linked_step_id=linked_step_id,
        linked_goal_id=linked_goal_id,
    )
    session.add(event)
    session.flush()
    return event.to_dict()


def get_event(session: Session, event_id: int, user_id: str) -> Optional[Dict[str, Any]]:
    """Get a single event by ID"""
    event = session.query(Event).filter(
        Event.id == event_id,
        Event.user_id == user_id
    ).first()
    return event.to_dict() if event else None


def search_events(
    session: Session,
    user_id: str,
    title_query: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    time: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Search events with filters"""
    q = session.query(Event).filter(Event.user_id == user_id)

    if title_query:
        pattern = f"%{title_query.strip()}%"
        q = q.filter(Event.title.ilike(pattern))

    if start_date:
        q = q.filter(Event.date >= parse_date(start_date))

    if end_date:
        q = q.filter(Event.date <= parse_date(end_date))

    if time:
        q = q.filter(Event.time == parse_time(time))

    q = q.order_by(Event.date.asc(), Event.time.asc().nullsfirst()).limit(limit)

    return [event.to_dict() for event in q.all()]


def update_event(
    session: Session,
    event_id: int,
    user_id: str,
    title: Optional[str] = None,
    date: Optional[str] = None,
    time: Optional[str] = None,
    repeat: Optional[str] = None,
    notes: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Update an existing event"""
    event = session.query(Event).filter(
        Event.id == event_id,
        Event.user_id == user_id
    ).first()

    if not event:
        return None

    if title is not None:
        event.title = title.strip()
    if date is not None:
        event.date = parse_date(date)
    if time is not None:
        event.time = parse_time(time)
    if repeat is not None:
        event.repeat = repeat
    if notes is not None:
        event.notes = notes

    session.flush()
    return event.to_dict()


def delete_event(session: Session, event_id: int, user_id: str) -> bool:
    """Delete an event"""
    event = session.query(Event).filter(
        Event.id == event_id,
        Event.user_id == user_id
    ).first()

    if not event:
        return False

    session.delete(event)
    session.flush()
    return True
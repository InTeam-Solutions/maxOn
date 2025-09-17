from __future__ import annotations

from typing import List, Optional, Dict, Any, Tuple
from uuid import uuid4

from dateutil import parser as dtparser

from mvp.core.db import get_db, Base
from mvp.core.models import Event
from mvp.core.selectors import EventSelector, EventPatch
from mvp.core.sets import save_set, get_items_from_set

# --- Схема ----
def ensure_schema():
    db = get_db()
    Base.metadata.create_all(bind=db.engine)

# --- Утилиты парсинга ---
def _parse_date(date_str: str):
    return dtparser.parse(date_str).date()

def _parse_time(time_str: Optional[str]):
    if not time_str:
        return None
    t = dtparser.parse(time_str).time()
    return t.replace(second=0, microsecond=0)

# --- Быстрый CRUD (create) ---
def add_event(user_id: str, title: str, date: str, time: Optional[str] = None,
              repeat: Optional[str] = None, notes: Optional[str] = None) -> Dict[str, Any]:
    db = get_db()
    with db.session_ctx() as s:
        ev = Event(
            user_id=user_id,
            title=title.strip(),
            date=_parse_date(date),
            time=_parse_time(time),
            repeat=repeat,
            notes=notes,
        )
        s.add(ev)
        s.flush()
        return ev.to_dict()

# --- Поиск событий (ILIKE + фильтры по датам/времени) ---
def search_events(user_id: str, selector: EventSelector) -> Tuple[str, List[Dict[str, Any]]]:
    db = get_db()
    with db.session_ctx() as s:
        q = s.query(Event).filter(Event.user_id == user_id)

        if selector.id:
            q = q.filter(Event.id == selector.id)

        if selector.start_date:
            q = q.filter(Event.date >= _parse_date(selector.start_date))
        if selector.end_date:
            q = q.filter(Event.date <= _parse_date(selector.end_date))

        if selector.time:
            q = q.filter(Event.time == _parse_time(selector.time))

        if selector.title_query:
            pattern = f"%{selector.title_query.strip()}%"
            q = q.filter(Event.title.ilike(pattern))

        q = q.order_by(Event.date.asc(), Event.time.asc().nullsfirst()).limit(selector.limit)
        items = [e.to_dict() for e in q.all()]
        
        set_id = save_set(user_id, items)
        return set_id, items

# --- Универсальная мутация (create/update/delete) + dry_run ---
def mutate_events(user_id: str, operation: str, selector: EventSelector,
                  patch: Optional[EventPatch], dry_run: bool) -> Dict[str, Any]:
    """
    operation: 'create' | 'update' | 'delete'
    selector: критерии отбора (или set_id+ordinal)
    patch: поля для изменения/создания (для update/create)
    dry_run: если True — возвращаем только preview
    """
    db = get_db()

    # CREATE
    if operation == "create":
        if not patch or not patch.title or not patch.start_date:
            raise ValueError("Для create обязательны 'title' и 'start_date'")
        if dry_run:
            return {"preview": [{
                "title": patch.title,
                "date": patch.start_date,
                "time": patch.time,
                "repeat": patch.repeat,
                "notes": patch.notes,
            }]}
        created = add_event(
            user_id=user_id,
            title=patch.title,
            date=patch.start_date,
            time=patch.time,
            repeat=patch.repeat,
            notes=patch.notes,
        )
        return {"changed": [created]}

    # UPDATE / DELETE → определяем целевые события
    if selector.set_id and selector.ordinal:
        items = get_items_from_set(selector.set_id, user_id)
        if not items:
            return {"changed": [], "preview": []}
        idx = max(0, min(len(items) - 1, (selector.ordinal or 1) - 1))
        targets = [items[idx]]
    else:
        _, targets = search_events(user_id, selector)

    if not targets:
        return {"changed": [], "preview": []}

    if dry_run:
        return {"preview": targets}

    # Выполнение
    with db.session_ctx() as s:
        if operation == "delete":
            ids = [t["id"] for t in targets]
            for i in ids:
                ev = s.query(Event).filter(Event.id == i, Event.user_id == user_id).first()
                if ev:
                    s.delete(ev)
            s.flush()
            return {"changed": [{"id": i} for i in ids]}

        if operation == "update":
            out = []
            for t in targets:
                ev = s.query(Event).filter(Event.id == t["id"], Event.user_id == user_id).first()
                if not ev:
                    continue
                if patch:
                    if patch.title is not None:
                        ev.title = patch.title.strip()
                    if patch.start_date is not None:
                        ev.date = _parse_date(patch.start_date)
                    if patch.time is not None:
                        ev.time = _parse_time(patch.time)
                    if patch.repeat is not None:
                        ev.repeat = patch.repeat
                    if patch.notes is not None:
                        ev.notes = patch.notes
                s.flush()
                out.append(ev.to_dict())
            return {"changed": out}

    return {"changed": []}

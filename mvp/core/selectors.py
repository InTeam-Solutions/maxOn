# mvp/core/selectors.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class EventSelector:
    # прямые фильтры
    id: Optional[int] = None
    title_query: Optional[str] = None
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None    # YYYY-MM-DD
    time: Optional[str] = None        # HH:MM
    fuzzy: bool = True
    limit: int = 50

    # ссылочные фильтры (указание на ранее найденный набор)
    set_id: Optional[str] = None
    ordinal: Optional[int] = None     # 1-based индекс в наборе


@dataclass
class EventPatch:
    # что изменить/создать
    title: Optional[str] = None
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None    # (резерв)
    time: Optional[str] = None        # HH:MM
    repeat: Optional[str] = None
    notes: Optional[str] = None

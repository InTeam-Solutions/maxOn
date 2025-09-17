# mvp/core/sets.py
from typing import Dict, List, Any
from uuid import uuid4

# set_id -> user_id -> items
_LAST_SETS: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

def save_set(user_id: str, items: List[Dict[str, Any]]) -> str:
    """
    Сохраняем набор событий для конкретного пользователя.
    """
    set_id = str(uuid4())
    if set_id not in _LAST_SETS:
        _LAST_SETS[set_id] = {}
    _LAST_SETS[set_id][user_id] = items
    return set_id

def get_items_from_set(set_id: str, user_id: str) -> List[Dict[str, Any]]:
    """
    Получаем сохранённый результат поиска по set_id для конкретного пользователя.
    """
    return _LAST_SETS.get(set_id, {}).get(user_id, [])

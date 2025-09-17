from typing import List, Dict, Any, Optional

# set_id → user_id → items
_LAST_SETS: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}


def save_items_set(set_id: str, user_id: str, items: List[Dict[str, Any]]):
    """
    Сохраняем набор результатов поиска для конкретного пользователя.
    """
    if set_id not in _LAST_SETS:
        _LAST_SETS[set_id] = {}
    _LAST_SETS[set_id][user_id] = items


def get_items_from_set(set_id: str, user_id: str) -> Optional[List[Dict[str, Any]]]:
    """
    Получаем сохранённый результат поиска по set_id для конкретного пользователя.
    """
    return _LAST_SETS.get(set_id, {}).get(user_id)


def render_events(items: List[Dict[str, Any]], title: Optional[str] = None) -> str:
    """
    Рендерим события в текст (для UI).
    """
    if not items:
        return "События не найдены."

    lines = []
    if title:
        lines.append(f"<b>{title}</b>\n")

    for i, e in enumerate(items, 1):
        date = e.get("date") or ""
        time = e.get("time") or ""
        tt = f"{date} {time}".strip()
        lines.append(f"{i}. <b>{e.get('title','(без названия)')}</b> — {tt}")

    return "\n".join(lines)

from typing import List, Dict, Any, Optional
from mvp.core.sets import get_items_from_set

# set_id → user_id → items

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

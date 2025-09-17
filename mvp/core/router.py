from typing import Any, Dict

from mvp.core.events import ensure_schema, search_events, mutate_events
from mvp.core.selectors import EventSelector, EventPatch


def _ok(intent, text, needs_followup=False, context=None, **extra):
    return {
        "intent": intent,
        "text": text,
        "needs_followup": needs_followup,
        "context": context or {},
        **extra,
    }


def _err(intent, text, **extra):
    return {
        "intent": intent or "unknown",
        "text": text,
        "error": True,
        "needs_followup": True,
        "context": extra,
    }


def handle_intent(parsed: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Поддерживаемые интенты Core:
      - small_talk
      - event.search   (вернёт result + set_id; обычно needs_followup=True)
      - event.mutate   (create/update/delete + dry_run)

    Формат дат: YYYY-MM-DD. Время: HH:MM.
    """
    intent = (parsed or {}).get("intent")
    text = (parsed or {}).get("text", "")

    if not intent:
        return _err("unknown", "Не передан intent")

    if intent == "small_talk":
        return _ok(intent, text)

    try:
        if intent == "event.search":
            sel = EventSelector(
                id=parsed.get("id"),
                title_query=parsed.get("title") or parsed.get("title_query"),
                start_date=parsed.get("start_date"),
                end_date=parsed.get("end_date"),
                time=parsed.get("time"),
                fuzzy=True if parsed.get("fuzzy", True) else False,
                limit=int(parsed.get("limit", 50) or 50),
                set_id=parsed.get("set_id"),
                ordinal=parsed.get("ordinal"),
            )
            set_id, items = search_events(user_id, sel)
            return _ok(
                intent,
                text or "Результаты поиска",
                needs_followup=True,  # обычно после поиска нужен рендер или уточнение
                context={"count": len(items), "set_id": set_id},
                result=items,
                set_id=set_id,
            )

        if intent == "event.mutate":
            operation = parsed.get("operation")  # 'create' | 'update' | 'delete'
            dry_run = bool(parsed.get("dry_run", False))

            sel = EventSelector(
                id=parsed.get("id"),
                title_query=parsed.get("title") or parsed.get("title_query"),
                start_date=parsed.get("start_date"),
                end_date=parsed.get("end_date"),
                time=parsed.get("time"),
                fuzzy=True if parsed.get("fuzzy", True) else False,
                limit=int(parsed.get("limit", 50) or 50),
                set_id=parsed.get("set_id"),
                ordinal=parsed.get("ordinal"),
            )

            patch = None
            if operation in ("create", "update"):
                patch = EventPatch(
                    title=parsed.get("new_title") or (parsed.get("title") if operation == "create" else None),
                    start_date=parsed.get("new_start_date") or (parsed.get("start_date") if operation == "create" else None),
                    time=parsed.get("new_time"),
                    repeat=parsed.get("new_repeat"),
                    notes=parsed.get("new_notes"),
                )

            result = mutate_events(user_id, operation, sel, patch, dry_run)

            changed = result.get("changed", [])
            needs = dry_run or (operation != "create" and len(changed) != 1)

            return _ok(
                intent,
                text or "Операция выполнена",
                needs_followup=needs,
                context={"operation": operation, **result},
                result=result,
            )

        return _err(intent, f"Неизвестный intent: {intent}")

    except Exception as e:
        return _err(intent, f"Ошибка: {e}")

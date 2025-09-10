from core_backend import events

def handle_intent(parsed: dict):
    intent = parsed.get("intent")
    data = parsed.get("data", {})

    if intent == "add_event":
        return events.add_event(
            title=data.get("title", "Событие"),
            date=data.get("date"),
            time=data.get("time"),
            repeat=data.get("repeat")
        )

    elif intent == "list_events":
        return events.list_events()

    # TODO: добавить обработку для целей и товаров
    elif intent == "add_goal":
        return {"message": f"Цель добавлена: {data.get('title')}"}

    elif intent == "add_product":
        return {"message": f"Товар добавлен: {data.get('name')}"}

    return {"error": f"Неизвестный интент: {intent}"}

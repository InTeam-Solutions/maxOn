"""
Formatter for rendering events, goals, and products in Telegram HTML format
"""
from typing import List, Dict, Any


def render_events(events: List[Dict[str, Any]], title: str = "События") -> str:
    """Render list of events as HTML table for Telegram"""
    if not events:
        return f"📅 <b>{title}</b>\n\n<i>Событий не найдено.</i>"

    lines = [f"📅 <b>{title}</b>\n"]

    for idx, event in enumerate(events, 1):
        date = event.get("date", "?")
        time = event.get("time", "")
        event_title = event.get("title", "Без названия")
        repeat = event.get("repeat")
        notes = event.get("notes", "")

        # Format date nicely
        try:
            from datetime import datetime
            date_obj = datetime.fromisoformat(date)
            weekday = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date_obj.weekday()]
            date_formatted = f"{weekday}, {date_obj.strftime('%d.%m.%Y')}"
        except:
            date_formatted = date

        time_str = f" в <b>{time}</b>" if time else ""
        repeat_str = f" 🔁 <i>{repeat}</i>" if repeat else ""
        notes_str = f"\n      💬 <i>{notes}</i>" if notes else ""

        lines.append(f"\n{idx}. <b>{event_title}</b>")
        lines.append(f"      📆 {date_formatted}{time_str}{repeat_str}{notes_str}")

    return "\n".join(lines)


def render_goals(goals: List[Dict[str, Any]], title: str = "Цели") -> str:
    """Render list of goals as HTML for Telegram"""
    if not goals:
        return f"🎯 <b>{title}</b>\n\n<i>Целей пока нет. Создай свою первую цель!</i>"

    lines = [f"🎯 <b>{title}</b>\n"]

    for idx, goal in enumerate(goals, 1):
        goal_title = goal.get("title", "Без названия")
        description = goal.get("description", "")
        status = goal.get("status", "active")
        progress = goal.get("progress_percent", 0)
        steps = goal.get("steps", [])
        steps_count = len(steps)
        completed_steps = len([s for s in steps if s.get("status") == "completed"])

        # Status emoji
        if status == "completed":
            status_emoji = "✅"
        elif status == "archived":
            status_emoji = "📦"
        else:
            status_emoji = "🎯"

        # Progress bar (10 blocks)
        filled = int(progress / 10)
        progress_bar = "█" * filled + "░" * (10 - filled)

        lines.append(f"\n{idx}. {status_emoji} <b>{goal_title}</b>")

        if description:
            lines.append(f"      💡 <i>{description[:100]}...</i>" if len(description) > 100 else f"      💡 <i>{description}</i>")

        lines.append(f"      {progress_bar} <b>{progress:.0f}%</b>")

        if steps_count > 0:
            lines.append(f"      📋 Шагов: {completed_steps}/{steps_count}")

            # Show first 3 steps
            for step_idx, step in enumerate(steps[:3], 1):
                step_title = step.get("title", "")
                step_status = step.get("status", "pending")

                if step_status == "completed":
                    step_emoji = "✅"
                elif step_status == "in_progress":
                    step_emoji = "🔄"
                else:
                    step_emoji = "⭕"

                lines.append(f"         {step_emoji} <i>{step_title}</i>")

            if steps_count > 3:
                lines.append(f"         <i>...и еще {steps_count - 3}</i>")

    return "\n".join(lines)


def render_products(products: List[Dict[str, Any]], title: str = "Товары") -> str:
    """Render list of products as HTML for Telegram"""
    if not products:
        return f"<b>{title}</b>\n\nНичего не найдено."

    lines = [f"<b>{title}</b>\n"]

    for idx, product in enumerate(products, 1):
        product_title = product.get("title", "Без названия")
        price = product.get("price", 0)
        marketplace = product.get("marketplace", "")
        url = product.get("url", "")

        price_str = f"{price:.2f} ₽" if price else "Цена не указана"
        marketplace_str = f" ({marketplace})" if marketplace else ""

        lines.append(f"{idx}. <b>{product_title}</b>")
        lines.append(f"   💰 {price_str}{marketplace_str}")
        if url:
            lines.append(f"   🔗 {url}")

    return "\n".join(lines)


def render_goals_list(goals: List[Dict[str, Any]], title: str = "🎯 Твои цели") -> str:
    """Render goals as a simple list with buttons (for hierarchical navigation)"""
    if not goals:
        return f"{title}\n\n<i>Целей пока нет. Создай свою первую цель!</i>"

    lines = [f"<b>{title}</b>\n"]

    for idx, goal in enumerate(goals, 1):
        goal_title = goal.get("title", "Без названия")
        status = goal.get("status", "active")
        progress = goal.get("progress_percent", 0)

        # Status emoji
        if status == "completed":
            status_emoji = "✅"
        elif status == "archived":
            status_emoji = "📦"
        else:
            status_emoji = "🎯"

        lines.append(f"{idx}. {status_emoji} <b>{goal_title}</b> ({progress:.0f}%)")

    return "\n".join(lines)


def render_goal_detail(goal: Dict[str, Any]) -> str:
    """Render detailed view of a single goal with all steps"""
    goal_title = goal.get("title", "Без названия")
    description = goal.get("description", "")
    status = goal.get("status", "active")
    progress = goal.get("progress_percent", 0)
    steps = goal.get("steps", [])
    steps_count = len(steps)
    completed_steps = len([s for s in steps if s.get("status") == "completed"])

    # Status emoji
    if status == "completed":
        status_emoji = "✅"
    elif status == "archived":
        status_emoji = "📦"
    else:
        status_emoji = "🎯"

    # Progress bar (10 blocks)
    filled = int(progress / 10)
    progress_bar = "█" * filled + "░" * (10 - filled)

    lines = [f"{status_emoji} <b>{goal_title}</b>\n"]

    if description:
        lines.append(f"💡 <i>{description}</i>\n")

    lines.append(f"{progress_bar} <b>{progress:.0f}%</b>")
    lines.append(f"📋 Шагов выполнено: {completed_steps}/{steps_count}\n")

    if steps_count > 0:
        lines.append("<b>Шаги:</b>")
        for step_idx, step in enumerate(steps, 1):
            step_title = step.get("title", "")
            step_status = step.get("status", "pending")

            if step_status == "completed":
                step_emoji = "✅"
            elif step_status == "in_progress":
                step_emoji = "🔄"
            else:
                step_emoji = "⭕"

            lines.append(f"{step_idx}. {step_emoji} <i>{step_title}</i>")

    return "\n".join(lines)


def render_cart(cart_items: List[Dict[str, Any]], title: str = "Корзина") -> str:
    """Render shopping cart as HTML for Telegram"""
    if not cart_items:
        return f"<b>{title}</b>\n\nКорзина пуста."

    lines = [f"<b>{title}</b>\n"]
    total = 0.0

    for idx, item in enumerate(cart_items, 1):
        product = item.get("product", {})
        quantity = item.get("quantity", 1)
        product_title = product.get("title", "Без названия")
        price = product.get("price", 0)
        subtotal = price * quantity

        lines.append(f"{idx}. <b>{product_title}</b>")
        lines.append(f"   {quantity} × {price:.2f} ₽ = {subtotal:.2f} ₽")

        total += subtotal

    lines.append(f"\n<b>Итого: {total:.2f} ₽</b>")

    return "\n".join(lines)

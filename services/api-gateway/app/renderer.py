"""
Formatter for rendering events, goals, and products in Telegram HTML format
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
import calendar


def render_events(events: List[Dict[str, Any]], title: str = "События") -> str:
    """Render list of events grouped by date for Telegram"""
    if not events:
        return f"📅 <b>{title}</b>\n\n<i>Событий не найдено.</i>"

    # Group events by date
    from collections import defaultdict
    events_by_date = defaultdict(list)

    for event in events:
        date = event.get("date", "?")
        events_by_date[date].append(event)

    # Sort dates
    sorted_dates = sorted(events_by_date.keys())

    lines = [f"📅 <b>{title}</b>\n"]

    for date in sorted_dates:
        # Format date header
        try:
            date_obj = datetime.fromisoformat(date)
            weekday_full = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"][date_obj.weekday()]
            date_short = date_obj.strftime('%d.%m')
            lines.append(f"\n━━━ <b>{weekday_full}, {date_short}</b> ━━━")
        except:
            lines.append(f"\n━━━ <b>{date}</b> ━━━")

        # Sort events by time for this date
        date_events = sorted(events_by_date[date], key=lambda e: e.get("time_start", e.get("time", "00:00")))

        for event in date_events:
            time_start = event.get("time_start", event.get("time", ""))
            duration_minutes = event.get("duration_minutes")
            event_title = event.get("title", "Без названия")
            notes = event.get("notes", "")

            # Remove seconds from time
            if time_start and len(time_start) > 5:
                time_start = time_start[:5]  # Keep only HH:MM

            # Truncate long titles
            if len(event_title) > 60:
                event_title = event_title[:57] + "..."

            # Format duration
            duration_str = ""
            if duration_minutes:
                if duration_minutes < 60:
                    duration_str = f" <i>({duration_minutes}мин)</i>"
                else:
                    hours = duration_minutes / 60
                    if hours == int(hours):
                        duration_str = f" <i>({int(hours)}ч)</i>"
                    else:
                        duration_str = f" <i>({hours:.1f}ч)</i>"

            time_str = f"⏰ <b>{time_start}</b>" if time_start else "⏰ <b>--:--</b>"
            lines.append(f"{time_str}  {event_title}{duration_str}")

            # Only show notes if they're different from title and not too long
            if notes and notes not in event_title and not notes.startswith("Шаг"):
                if len(notes) > 50:
                    lines.append(f"   💬 <i>{notes[:47]}...</i>")
                else:
                    lines.append(f"   💬 <i>{notes}</i>")

            # Add spacing between events
            lines.append("")

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


def create_calendar_keyboard(year: int = None, month: int = None):
    """Create inline keyboard with calendar for date selection"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    # Get calendar data
    cal = calendar.monthcalendar(year, month)
    month_names = ["", "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
                   "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]

    # Create keyboard
    keyboard = []

    # Header with month and year (compact)
    keyboard.append([
        InlineKeyboardButton(text="◀", callback_data=f"cal_prev_{year}_{month}"),
        InlineKeyboardButton(text=f"{month_names[month]} '{year % 100}", callback_data="cal_ignore"),
        InlineKeyboardButton(text="▶", callback_data=f"cal_next_{year}_{month}")
    ])

    # Weekday names (compact single letters)
    weekdays = ["П", "В", "С", "Ч", "П", "С", "В"]
    keyboard.append([InlineKeyboardButton(text=day, callback_data="cal_ignore") for day in weekdays])

    # Calendar days - only show weeks with future dates
    current_date = now.date()
    for week in cal:
        # Check if this week has any future dates
        has_future = False
        for day in week:
            if day > 0:
                date = datetime(year, month, day).date()
                if date >= current_date:
                    has_future = True
                    break

        if not has_future:
            continue  # Skip past weeks

        row = []
        for day in week:
            if day == 0:
                # Empty cell - use invisible space
                row.append(InlineKeyboardButton(text="·", callback_data="cal_ignore"))
            else:
                date = datetime(year, month, day).date()
                if date < current_date:
                    # Past date - show dimmed
                    row.append(InlineKeyboardButton(text="·", callback_data="cal_ignore"))
                else:
                    # Future or today - selectable
                    callback_data = f"cal_select_{year}_{month:02d}_{day:02d}"
                    if date == current_date:
                        text = f"[{day}]"  # Today in brackets
                    else:
                        text = str(day)
                    row.append(InlineKeyboardButton(text=text, callback_data=callback_data))
        keyboard.append(row)

    # Quick date buttons for common choices
    today = now.date()
    tomorrow = today + timedelta(days=1)
    week_later = today + timedelta(days=7)

    quick_buttons = []
    if tomorrow.month == month and tomorrow.year == year:
        quick_buttons.append(
            InlineKeyboardButton(
                text="Завтра",
                callback_data=f"cal_select_{tomorrow.year}_{tomorrow.month:02d}_{tomorrow.day:02d}"
            )
        )
    if week_later.month == month and week_later.year == year:
        quick_buttons.append(
            InlineKeyboardButton(
                text="Через неделю",
                callback_data=f"cal_select_{week_later.year}_{week_later.month:02d}_{week_later.day:02d}"
            )
        )

    if quick_buttons:
        keyboard.append(quick_buttons)

    # Cancel button
    keyboard.append([InlineKeyboardButton(text="✕ Отмена", callback_data="cal_cancel")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

import os
import logging
import asyncio
import calendar as calendar_module
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
from maxapi import Bot, Dispatcher, F
from maxapi.enums.attachment import AttachmentType
from maxapi.enums.parse_mode import ParseMode
from maxapi.types import (
    BotCommand,
    CallbackButton,
    Command,
    CommandStart,
    MessageCallback,
    MessageCreated,
)

from app.max_adapter import build_inline_keyboard, keyboard_from_pairs, send_typing
from app.renderer import (
    render_events,
    render_goals,
    render_products,
    render_cart,
    render_goals_list,
    render_goal_detail,
)
from shared.utils.analytics import track_event, increment_user_counter, set_user_profile

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# --- Configuration ---
BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8001")
CORE_SERVICE_URL = os.getenv("CORE_SERVICE_URL", "http://core:8004")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://llm:8003")
CONTEXT_SERVICE_URL = os.getenv("CONTEXT_SERVICE_URL", "http://context:8002")
CALENDAR_SERVICE_URL = os.getenv("CALENDAR_SERVICE_URL")

if not BOT_TOKEN:
    raise RuntimeError("MAX_BOT_TOKEN or TELEGRAM_BOT_TOKEN is required")

# --- Bot initialization ---
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# HTTP client for Orchestrator and other services
http_client = httpx.AsyncClient(timeout=30.0)

WEEKDAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTH_NAMES = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]
MAX_LEADERBOARD_USERS = 10

# --- Helper builders ---

def _attachments(markup):
    return [markup] if markup else None


def main_menu_keyboard():
    return keyboard_from_pairs([
        [("🎯 Мои цели", "show_goals"), ("📅 Календарь", "show_events")],
        [("📊 Статистика", "show_stats"), ("🏆 Лидерборд", "leaderboard")],
        [("🗓 Расписание", "calendar_view_week"), ("🔗 Подписка", "calendar_link")],
        [("➕ Новая цель", "new_goal"), ("➕ Событие", "new_event")],
    ])


def single_menu_button(text: str, payload: str):
    return keyboard_from_pairs([[(text, payload)]])


async def fetch_calendar_link(user_id: str) -> Optional[str]:
    if not CALENDAR_SERVICE_URL:
        return None
    try:
        response = await http_client.post(
            f"{CALENDAR_SERVICE_URL}/api/calendars/users/{user_id}/calendar",
            json={},
        )
        if response.status_code >= 400:
            logger.warning("Failed to fetch calendar link for %s: %s", user_id, response.text)
            return None
        data = response.json()
        return data.get("public_ics_url")
    except Exception as exc:
        logger.error("Calendar link request failed for %s: %s", user_id, exc)
        return None


async def fetch_goals_for_user_raw(user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"user_id": user_id}
    if status:
        params["status"] = status
    try:
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals",
            params=params
        )
        if response.status_code == 200:
            return response.json()
        logger.warning("Failed to load goals for %s: %s", user_id, response.text)
    except Exception as exc:
        logger.error("Goal request failed for %s: %s", user_id, exc)
    return []


async def fetch_events_range(user_id: str, start: date, end: date) -> List[Dict[str, Any]]:
    try:
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/events",
            params={
                "user_id": user_id,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            }
        )
        if response.status_code == 200:
            return response.json()
        logger.warning("Failed to load events for %s: %s", user_id, response.text)
    except Exception as exc:
        logger.error("Event request failed for %s: %s", user_id, exc)
    return []


def _safe_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _format_weekday(d: date) -> str:
    return f"{WEEKDAY_NAMES[d.weekday()]} {d.strftime('%d.%m')}"


def _event_datetime(event: Dict[str, Any]) -> Optional[datetime]:
    event_date = _safe_date(event.get("date"))
    if not event_date:
        return None
    event_time_str = event.get("time")
    event_time_obj: Optional[time] = None
    if event_time_str:
        try:
            event_time_obj = datetime.strptime(event_time_str, "%H:%M").time()
        except ValueError:
            event_time_obj = None
    return datetime.combine(event_date, event_time_obj or time.min)


def _format_period(start: date, end: date) -> str:
    if start.month == end.month:
        month_name = MONTH_NAMES[start.month - 1]
        return f"{start.day}–{end.day} {month_name}"
    return f"{start.strftime('%d.%m')} – {end.strftime('%d.%m')}"


async def build_personal_stats(user_id: str) -> str:
    goals = await fetch_goals_for_user_raw(user_id)
    today = date.today()
    week_start = today - timedelta(days=7)

    if not goals:
        return (
            "📊 <b>Личная статистика</b>\n\n"
            "У тебя пока нет целей — самое время поставить первую и получить план действий! "
            "Нажми «➕ Новая цель» в главном меню."
        )

    total_goals = len(goals)
    active_goals = sum(1 for goal in goals if goal.get("status") == "active")
    completed_goals = sum(1 for goal in goals if goal.get("status") == "completed")
    avg_progress = sum(goal.get("progress_percent", 0) for goal in goals) / max(total_goals, 1)

    total_steps = sum(len(goal.get("steps", [])) for goal in goals)
    completed_steps = sum(
        1 for goal in goals for step_item in goal.get("steps", [])
        if step_item.get("status") == "completed"
    )
    steps_last_week = 0
    for goal in goals:
        for step_item in goal.get("steps", []):
            if step_item.get("status") != "completed":
                continue
            completed_at = _safe_date(step_item.get("completed_at"))
            if completed_at and completed_at >= week_start:
                steps_last_week += 1

    next_deadline = min(
        (parsed for parsed in (_safe_date(goal.get("target_date")) for goal in goals) if parsed),
        default=None
    )

    events_next_week = await fetch_events_range(user_id, today, today + timedelta(days=7))
    upcoming_events = len(events_next_week)
    next_event = None
    if events_next_week:
        events_sorted = sorted(
            (evt for evt in events_next_week if _event_datetime(evt)),
            key=lambda evt: _event_datetime(evt)
        )
        if events_sorted:
            next_event = events_sorted[0]

    lines = [
        "📊 <b>Личная статистика</b>",
        f"Всего целей: <b>{total_goals}</b> (активных — <b>{active_goals}</b>, завершённых — <b>{completed_goals}</b>)",
        f"Средний прогресс: <b>{avg_progress:.0f}%</b>",
    ]

    if total_steps:
        lines.append(f"Шагов выполнено: <b>{completed_steps}/{total_steps}</b>")
    lines.append(f"За 7 дней закрыто шагов: <b>{steps_last_week}</b>")

    if next_deadline:
        lines.append(f"Ближайший дедлайн цели: <b>{_format_weekday(next_deadline)}</b>")

    if upcoming_events:
        lines.append(f"События на неделе: <b>{upcoming_events}</b>")
        if next_event:
            event_date = _safe_date(next_event.get("date"))
            when = _format_weekday(event_date) if event_date else "скоро"
            time_hint = next_event.get("time")
            time_part = f" в {time_hint}" if time_hint else ""
            lines.append(f"Следующее: {when}{time_part} — <i>{next_event.get('title', 'Событие')}</i>")

    return "\n".join(lines)


async def show_personal_stats(chat_id: Optional[int], user_id: str, bot_instance: Bot):
    await send_typing(bot_instance, chat_id)
    stats_text = await build_personal_stats(user_id)
    keyboard = keyboard_from_pairs([
        [("🎯 Цели", "show_goals"), ("🏠 Меню", "main_menu")],
        [("🏆 Лидерборд", "leaderboard")],
    ])
    await bot_instance.send_message(
        chat_id=chat_id,
        text=stats_text,
        attachments=_attachments(keyboard),
        parse_mode=ParseMode.HTML,
    )


async def _user_goals_summary(user_id: str) -> Dict[str, Any]:
    goals = await fetch_goals_for_user_raw(user_id)
    total = len(goals)
    completed = sum(1 for goal in goals if goal.get("status") == "completed")
    avg_progress = sum(goal.get("progress_percent", 0) for goal in goals) / max(total, 1)
    return {
        "user_id": user_id,
        "avg_progress": avg_progress,
        "completed": completed,
        "total": total,
    }


async def build_leaderboard(user_id: str) -> str:
    user_ids: List[str] = []
    try:
        response = await http_client.get(f"{CORE_SERVICE_URL}/api/users")
        if response.status_code == 200:
            user_ids = [
                u.get("user_id")
                for u in response.json()
                if u.get("user_id")
            ]
        else:
            logger.warning("Failed to fetch users for leaderboard: %s", response.text)
    except Exception as exc:
        logger.error("User list request failed: %s", exc)

    if user_id not in user_ids:
        user_ids.insert(0, user_id)

    user_ids = user_ids[:MAX_LEADERBOARD_USERS]

    summaries = await asyncio.gather(*[_user_goals_summary(uid) for uid in user_ids])
    entries = [summary for summary in summaries if summary]

    if not entries:
        return (
            "🏆 <b>Лидерборд</b>\n\n"
            "Пока нет достаточно данных, чтобы построить рейтинг. "
            "Создай цель и продвинься по шагам, чтобы появиться в списке лидеров!"
        )

    entries_sorted = sorted(
        entries,
        key=lambda item: (item["avg_progress"], item["completed"]),
        reverse=True
    )

    lines = [
        "🏆 <b>Лидерборд</b>",
        "Лучшие по среднему прогрессу целей:",
    ]

    display_entries = entries_sorted[:5]
    for idx, entry in enumerate(display_entries, start=1):
        marker = "⭐️ " if entry["user_id"] == user_id else ""
        label = "Ты" if entry["user_id"] == user_id else f"ID {entry['user_id']}"
        lines.append(
            f"{idx}. {marker}{label} — <b>{entry['avg_progress']:.0f}%</b> "
            f"(закрыто целей: {entry['completed']}/{entry['total']})"
        )

    current_rank = next(
        (idx for idx, entry in enumerate(entries_sorted, start=1) if entry["user_id"] == user_id),
        None
    )
    if current_rank and current_rank > len(display_entries):
        own_entry = next(entry for entry in entries_sorted if entry["user_id"] == user_id)
        lines.append("")
        lines.append(
            f"Ты на {current_rank}-м месте с прогрессом {own_entry['avg_progress']:.0f}% "
            f"({own_entry['completed']} завершённых целей)."
        )

    return "\n".join(lines)


async def show_leaderboard(chat_id: Optional[int], user_id: str, bot_instance: Bot):
    await send_typing(bot_instance, chat_id)
    text = await build_leaderboard(user_id)
    keyboard = keyboard_from_pairs([
        [("📊 Статистика", "show_stats"), ("🏠 Меню", "main_menu")],
    ])
    await bot_instance.send_message(
        chat_id=chat_id,
        text=text,
        attachments=_attachments(keyboard),
        parse_mode=ParseMode.HTML,
    )


def _calendar_period(period: str) -> Tuple[date, date]:
    today = date.today()
    if period == "today":
        return today, today
    if period == "month":
        last_day = calendar_module.monthrange(today.year, today.month)[1]
        return today.replace(day=1), date(today.year, today.month, last_day)
    # Default: week
    return today, today + timedelta(days=6)


def calendar_view_keyboard(active: str):
    labels = [
        ("calendar_view_today", "Сегодня"),
        ("calendar_view_week", "Неделя"),
        ("calendar_view_month", "Месяц"),
    ]
    filter_row = [
        CallbackButton(
            text=("• " if active == payload else "") + label,
            payload=payload
        )
        for payload, label in labels
    ]
    action_rows = [
        [
            CallbackButton(text="➕ Событие", payload="new_event"),
            CallbackButton(text="🏠 Меню", payload="main_menu"),
        ],
        [CallbackButton(text="🔗 Подписка", payload="calendar_link")],
    ]
    return build_inline_keyboard([filter_row, *action_rows])


def _render_day_block(day: date, events: List[Dict[str, Any]]) -> List[str]:
    lines = [f"<b>{_format_weekday(day)}</b>"]
    if not events:
        lines.append("  <i>Нет событий</i>")
        return lines

    for event in sorted(events, key=lambda e: (e.get("time") or "24:00", e.get("title", "")))[:4]:
        time_hint = event.get("time") or "весь день"
        title = event.get("title", "Событие")
        lines.append(f"  • {time_hint} — {title}")
    if len(events) > 4:
        lines.append(f"  … и ещё {len(events) - 4}")
    return lines


async def build_calendar_overview(user_id: str, period: str) -> str:
    start, end = _calendar_period(period)
    events = await fetch_events_range(user_id, start, end)

    title_map = {
        "today": "Сегодня",
        "week": "Неделя",
        "month": "Месяц",
    }
    title = title_map.get(period, "Неделя")

    lines = [
        f"🗓 <b>{title}</b>",
        _format_period(start, end),
        "",
    ]

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for event in events:
        event_date = _safe_date(event.get("date"))
        if not event_date:
            continue
        grouped.setdefault(event_date.isoformat(), []).append(event)

    if period == "month":
        lines.append(f"Всего событий в этом месяце: <b>{len(events)}</b>")
        upcoming = sorted(
            (evt for evt in events if _event_datetime(evt)),
            key=_event_datetime
        )[:5]
        if upcoming:
            lines.append("")
            lines.append("<b>Ближайшие события:</b>")
            for event in upcoming:
                event_date = _safe_date(event.get("date"))
                when = _format_weekday(event_date) if event_date else "Скоро"
                time_hint = event.get("time")
                title = event.get("title", "Событие")
                lines.append(f"• {when}{f' в {time_hint}' if time_hint else ''} — {title}")
        elif not events:
            lines.append("")
            lines.append("<i>В этом месяце пока нет событий.</i>")
        return "\n".join(lines)

    current = start
    while current <= end:
        lines.extend(_render_day_block(current, grouped.get(current.isoformat(), [])))
        lines.append("")
        current += timedelta(days=1)

    return "\n".join(lines).strip()


async def show_calendar_overview(chat_id: Optional[int], user_id: str, bot_instance: Bot, period: str):
    await send_typing(bot_instance, chat_id)
    text = await build_calendar_overview(user_id, period)
    keyboard = calendar_view_keyboard(period)
    await bot_instance.send_message(
        chat_id=chat_id,
        text=text,
        attachments=_attachments(keyboard),
        parse_mode=ParseMode.HTML,
    )

# --- Core functions ---

async def get_dashboard_stats(user_id: str) -> str:
    """Get user dashboard with upcoming events and goals progress"""
    try:
        from datetime import datetime, timedelta
        import random

        stats_lines: List[str] = []

        today = datetime.now().date()
        three_days = today + timedelta(days=3)

        events_response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/events",
            params={
                "user_id": user_id,
                "start_date": today.isoformat(),
                "end_date": three_days.isoformat()
            }
        )

        if events_response.status_code == 200:
            events = events_response.json()
            if events:
                stats_lines.append("📅 <b>Ближайшие события:</b>")
                for event in events[:3]:
                    title = event.get("title", "Событие")
                    date = event.get("date", "")
                    time = event.get("time", "")

                    try:
                        date_obj = datetime.fromisoformat(date)
                        weekday = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date_obj.weekday()]
                        date_str = f"{weekday}, {date_obj.strftime('%d.%m')}"
                    except Exception:
                        date_str = date

                    time_str = f" в {time}" if time else ""
                    stats_lines.append(f"  • {title} — {date_str}{time_str}")
                stats_lines.append("")

        goals_response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals",
            params={"user_id": user_id, "status": "active"}
        )

        if goals_response.status_code == 200:
            goals = goals_response.json()
            if goals:
                stats_lines.append("🎯 <b>Твои цели:</b>")
                total_progress = sum(g.get("progress_percent", 0) for g in goals) / len(goals)
                stats_lines.append(f"  Общий прогресс: <b>{total_progress:.0f}%</b>")

                stats_lines.append(f"  Активных целей: <b>{len(goals)}</b>")

                random_goal = random.choice(goals)
                goal_title = random_goal.get("title", "")
                goal_progress = random_goal.get("progress_percent", 0)

                if goal_progress < 30:
                    motivation = "Начни работать над ней сегодня! 💪"
                elif goal_progress < 70:
                    motivation = "Продолжай в том же духе! 🔥"
                else:
                    motivation = "Ты почти у цели! 🚀"

                stats_lines.append(f"\n💡 <i>Напоминаю о цели: {goal_title}</i>")
                stats_lines.append(f"  {motivation}")
            else:
                stats_lines.append("🎯 <i>У тебя пока нет целей. Создай свою первую!</i>")

        if not stats_lines:
            return "📊 <i>Пока нет данных для отображения</i>"

        return "\n".join(stats_lines)

    except Exception as e:
        logger.exception(f"Error getting dashboard stats: {e}")
        return "📊 <i>Не удалось загрузить статистику</i>"


async def show_goals_for_user(chat_id: Optional[int], user_id: str, bot_instance: Bot):
    await send_typing(bot_instance, chat_id)

    try:
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals",
            params={"user_id": user_id, "status": "active"}
        )

        if response.status_code == 200:
            goals = response.json()

            if goals:
                rendered = render_goals_list(goals, title="🎯 Твои цели")

                goal_buttons: List[List[CallbackButton]] = []
                for idx, goal in enumerate(goals, 1):
                    goal_id = goal.get("id")
                    goal_title = goal.get("title", "Без названия")
                    button_text = goal_title[:35] + "..." if len(goal_title) > 35 else goal_title
                    goal_buttons.append([
                        CallbackButton(text=f"{idx}. {button_text}", payload=f"view_goal_{goal_id}")
                    ])

                goal_buttons.append([
                    CallbackButton(text="➕ Новая цель", payload="new_goal"),
                    CallbackButton(text="🏠 Меню", payload="main_menu"),
                ])

                keyboard = build_inline_keyboard(goal_buttons)
                await bot_instance.send_message(
                    chat_id=chat_id,
                    text=rendered,
                    attachments=_attachments(keyboard),
                    parse_mode=ParseMode.HTML
                )
            else:
                keyboard = single_menu_button("➕ Создать первую цель", "new_goal")
                await bot_instance.send_message(
                    chat_id=chat_id,
                    text=(
                        "🎯 <b>Твои цели</b>\n\n"
                        "<i>Целей пока нет. Создай свою первую цель!</i>"
                    ),
                    attachments=_attachments(keyboard),
                    parse_mode=ParseMode.HTML
                )
        else:
            raise RuntimeError(f"Core Service returned {response.status_code}")

    except Exception as e:
        logger.exception(f"Error loading goals: {e}")
        keyboard = single_menu_button("🏠 Главное меню", "main_menu")
        await bot_instance.send_message(
            chat_id=chat_id,
            text=(
                "😔 Не удалось загрузить цели.\n\n"
                "Попробуй ещё раз или вернись в меню."
            ),
            attachments=_attachments(keyboard),
        )


async def show_events_for_user(chat_id: Optional[int], user_id: str, bot_instance: Bot):
    await send_typing(bot_instance, chat_id)

    try:
        from datetime import datetime, timedelta

        today = datetime.now().date()
        week_end = today + timedelta(days=7)

        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/events",
            params={
                "user_id": user_id,
                "start_date": today.isoformat(),
                "end_date": week_end.isoformat()
            }
        )

        if response.status_code == 200:
            events = response.json()

            if events:
                rendered = render_events(events, title="📅 События на этой неделе")
                keyboard = keyboard_from_pairs([
                    [("➕ Новое событие", "new_event"), ("🏠 Меню", "main_menu")],
                    [("🗓 Расписание", "calendar_view_week"), ("🔗 Мой календарь", "calendar_link")],
                ])
                await bot_instance.send_message(
                    chat_id=chat_id,
                    text=rendered,
                    attachments=_attachments(keyboard),
                    parse_mode=ParseMode.HTML
                )
            else:
                keyboard = keyboard_from_pairs([
                    [("➕ Создать событие", "new_event")],
                    [("🗓 Расписание", "calendar_view_week"), ("🔗 Мой календарь", "calendar_link")],
                    [("🏠 Меню", "main_menu")],
                ])
                await bot_instance.send_message(
                    chat_id=chat_id,
                    text=(
                        "📅 <b>События на этой неделе</b>\n\n"
                        "<i>Событий не найдено.</i>"
                    ),
                    attachments=_attachments(keyboard),
                    parse_mode=ParseMode.HTML
                )
        else:
            raise RuntimeError(f"Core Service returned {response.status_code}")

    except Exception as e:
        logger.exception(f"Error loading events: {e}")
        keyboard = single_menu_button("🏠 Главное меню", "main_menu")
        await bot_instance.send_message(
            chat_id=chat_id,
            text=(
                "😔 Не удалось загрузить события.\n\n"
                "Попробуй ещё раз или вернись в меню."
            ),
            attachments=_attachments(keyboard),
        )


# --- Handlers ---

@dp.message_created(CommandStart())
async def cmd_start(event: MessageCreated):
    user = event.message.sender
    user_id = str(user.user_id)

    track_event(user_id, "Bot Started", {
        "username": user.username,
        "first_name": user.first_name,
        "language_code": event.user_locale or "ru"
    })
    set_user_profile(user_id, {
        "$name": user.full_name,
        "username": user.username,
        "language": event.user_locale or "ru"
    })

    stats = await get_dashboard_stats(user_id)
    keyboard = main_menu_keyboard()

    await event.message.answer(
        "👋 <b>Привет! Я твой персональный коуч.</b>\n\n"
        f"{stats}\n\n"
        "Используй кнопки ниже или просто напиши мне:",
        attachments=_attachments(keyboard),
        parse_mode=ParseMode.HTML
    )


@dp.message_created(Command("goals"))
async def cmd_goals(event: MessageCreated):
    await show_goals_for_user(event.message.recipient.chat_id, str(event.message.sender.user_id), event.message.bot)


@dp.message_created(Command("events"))
async def cmd_events(event: MessageCreated):
    await show_events_for_user(event.message.recipient.chat_id, str(event.message.sender.user_id), event.message.bot)


@dp.message_created(Command("stats"))
async def cmd_stats(event: MessageCreated):
    await show_personal_stats(event.message.recipient.chat_id, str(event.message.sender.user_id), event.message.bot)


@dp.message_created(Command("leaderboard"))
async def cmd_leaderboard(event: MessageCreated):
    await show_leaderboard(event.message.recipient.chat_id, str(event.message.sender.user_id), event.message.bot)


@dp.message_created(Command("calendar"))
async def cmd_calendar(event: MessageCreated):
    await show_calendar_overview(event.message.recipient.chat_id, str(event.message.sender.user_id), event.message.bot, "week")


@dp.message_created(Command("webapp"))
async def cmd_webapp(event: MessageCreated):
    """Send link to open WebApp in browser with user_id"""
    user_id = str(event.message.sender.user_id)
    webapp_url = f"https://mini-app-alpha-fawn.vercel.app?user_id={user_id}"

    message_text = (
        "🚀 <b>MaxOn Web App (ТЕСТ)</b>\n\n"
        "Открой приложение в браузере для удобного управления целями и событиями!\n\n"
        f"👉 <a href=\"{webapp_url}\">Открыть приложение</a>\n\n"
        f"<code>User ID: {user_id}</code>"
    )

    await event.message.answer(message_text, parse_mode=ParseMode.HTML)


@dp.message_callback(F.callback.payload == "show_goals")
async def callback_show_goals(callback: MessageCallback):
    user_id = str(callback.callback.user.user_id)
    await show_goals_for_user(callback.message.recipient.chat_id, user_id, callback.message.bot)


@dp.message_callback(F.callback.payload == "show_events")
async def callback_show_events(callback: MessageCallback):
    user_id = str(callback.callback.user.user_id)
    await show_events_for_user(callback.message.recipient.chat_id, user_id, callback.message.bot)


@dp.message_callback(F.callback.payload == "show_stats")
async def callback_show_stats(callback: MessageCallback):
    user_id = str(callback.callback.user.user_id)
    await show_personal_stats(callback.message.recipient.chat_id, user_id, callback.message.bot)


@dp.message_callback(F.callback.payload == "leaderboard")
async def callback_show_leaderboard(callback: MessageCallback):
    user_id = str(callback.callback.user.user_id)
    await show_leaderboard(callback.message.recipient.chat_id, user_id, callback.message.bot)


@dp.message_callback(F.callback.payload == "calendar_link")
async def callback_calendar_link(callback: MessageCallback):
    user_id = str(callback.callback.user.user_id)
    chat_id = callback.message.recipient.chat_id
    await send_typing(callback.message.bot, chat_id)

    link = await fetch_calendar_link(user_id)
    if link:
        text = (
            "🔗 <b>Твоя подписка на календарь</b>\n\n"
            f"{link}\n\n"
            "Добавь эту ссылку в Google Calendar (Other calendars → By URL) "
            "или Apple Calendar (Файл → Новая подписка на календарь)."
        )
    else:
        text = (
            "😔 Не удалось получить ссылку на календарь. "
            "Попробуй позже или убедись, что сервис календаря запущен."
        )

    keyboard = keyboard_from_pairs([
        [("📅 События", "show_events"), ("🏠 Меню", "main_menu")],
    ])
    await callback.message.bot.send_message(
        chat_id=chat_id,
        text=text,
        attachments=_attachments(keyboard),
        parse_mode=ParseMode.HTML,
    )


@dp.message_callback(F.callback.payload.in_({"calendar_view_today", "calendar_view_week", "calendar_view_month"}))
async def callback_calendar_view(callback: MessageCallback):
    user_id = str(callback.callback.user.user_id)
    period = callback.callback.payload.split("_")[-1]
    text = await build_calendar_overview(user_id, period)
    keyboard = calendar_view_keyboard(period)
    await callback.message.edit(
        text=text,
        attachments=_attachments(keyboard),
        parse_mode=ParseMode.HTML,
    )


@dp.message_callback(F.callback.payload == "new_goal")
async def callback_new_goal(callback: MessageCallback):
    await callback.message.answer(
        "💡 Отлично! Расскажи мне о своей цели.\n\n"
        "Например:\n"
        "• Выучить английский до уровня B2\n"
        "• Научиться программировать на Python\n"
        "• Похудеть на 10 кг за 3 месяца\n\n"
        "Я автоматически создам пошаговый план для её достижения!"
    )


@dp.message_callback(F.callback.payload == "new_event")
async def callback_new_event(callback: MessageCallback):
    await callback.message.answer(
        "📅 Создам событие! Скажи мне:\n\n"
        "Например:\n"
        "• Созвон с командой завтра в 15:00\n"
        "• Встреча с клиентом 5 октября\n"
        "• Тренировка каждый понедельник в 18:00"
    )


@dp.message_callback(F.callback.payload == "main_menu")
async def callback_main_menu(callback: MessageCallback):
    user_id = str(callback.callback.user.user_id)

    try:
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "idle",
                "context": {},
                "expiry_hours": 1
            }
        )
    except Exception as e:
        logger.error(f"Error resetting session state: {e}")

    stats = await get_dashboard_stats(user_id)
    keyboard = main_menu_keyboard()

    await callback.message.edit(
        text=(
            "🏠 <b>Главное меню</b>\n\n"
            f"{stats}\n\n"
            "Выбери действие или просто напиши мне что-нибудь:"
        ),
        attachments=_attachments(keyboard),
        parse_mode=ParseMode.HTML
    )


@dp.message_callback(F.callback.payload.startswith("view_goal_"))
async def callback_view_goal(callback: MessageCallback):
    goal_id = callback.callback.payload.split("_")[-1]
    user_id = str(callback.callback.user.user_id)

    await send_typing(callback.message.bot, callback.message.recipient.chat_id)

    try:
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
            params={"user_id": user_id}
        )

        if response.status_code == 200:
            goal = response.json()
            rendered = render_goal_detail(goal)

            steps = goal.get("steps", [])
            step_buttons: List[List[CallbackButton]] = []
            for step in steps:
                step_id = step.get("id")
                step_status = step.get("status", "pending")
                step_title = step.get("title", "")

                if step_status == "completed":
                    emoji = "✅"
                elif step_status == "in_progress":
                    emoji = "🔄"
                else:
                    emoji = "⭕"

                text = step_title[:40] + "..." if len(step_title) > 40 else step_title
                step_buttons.append([
                    CallbackButton(text=f"{emoji} {text}", payload=f"toggle_step_{step_id}_{goal_id}")
                ])

            step_buttons.append([
                CallbackButton(text="✏️ Поправить шаги", payload=f"edit_goal_steps_{goal_id}")
            ])
            step_buttons.append([
                CallbackButton(text="◀️ К списку целей", payload="show_goals"),
                CallbackButton(text="🏠 Меню", payload="main_menu"),
            ])

            keyboard = build_inline_keyboard(step_buttons)
            await callback.message.edit(
                text=rendered,
                attachments=_attachments(keyboard),
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.message.edit(
                text="😔 Не удалось загрузить цель.\n\nПопробуй ещё раз.",
                parse_mode=ParseMode.HTML
            )

    except Exception as e:
        logger.exception(f"Error loading goal {goal_id}: {e}")
        await callback.message.edit(
            text="😔 Произошла ошибка при загрузке цели.",
            parse_mode=ParseMode.HTML
        )


@dp.message_callback(F.callback.payload.startswith("edit_goal_steps_"))
async def callback_edit_goal_steps(callback: MessageCallback):
    goal_id = callback.callback.payload.split("_")[-1]
    user_id = str(callback.callback.user.user_id)

    try:
        goal_response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
            params={"user_id": user_id}
        )

        if goal_response.status_code == 200:
            goal = goal_response.json()
            goal_title = goal.get("title", "цели")

            await http_client.put(
                f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
                json={
                    "current_state": "editing_goal_steps",
                    "context": {
                        "editing_goal_id": int(goal_id),
                        "goal_title": goal_title
                    },
                    "expiry_hours": 2
                }
            )

            keyboard = build_inline_keyboard([
                [CallbackButton(text="❌ Отменить редактирование", payload=f"cancel_edit_{goal_id}")],
                [CallbackButton(text="🏠 Главное меню", payload="main_menu")]
            ])

            await callback.message.edit(
                text=(
                    "✏️ <b>Режим редактирования шагов</b>\n\n"
                    f"Цель: <i>{goal_title}</i>\n\n"
                    "Теперь ты можешь попросить меня:\n"
                    "• Добавить новый шаг\n"
                    "• Изменить формулировку шага\n"
                    "• Удалить шаг\n"
                    "• Изменить порядок шагов\n\n"
                    "Просто напиши мне что нужно изменить, например:\n"
                    "<i>\"Добавь шаг: изучить основы Python\"</i>\n"
                    "<i>\"Удали третий шаг\"</i>\n"
                    "<i>\"Переформулируй первый шаг на более простой язык\"</i>\n\n"
                    "💡 Я работаю только с этой целью, пока ты не выйдешь из режима редактирования."
                ),
                attachments=_attachments(keyboard),
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.message.bot.send_message(
                chat_id=callback.message.recipient.chat_id,
                text="Не удалось загрузить цель"
            )

    except Exception as e:
        logger.exception(f"Error entering edit mode for goal {goal_id}: {e}")
        await callback.message.bot.send_message(
            chat_id=callback.message.recipient.chat_id,
            text="Произошла ошибка"
        )


@dp.message_callback(F.callback.payload.startswith("cancel_edit_"))
async def callback_cancel_edit(callback: MessageCallback):
    goal_id = callback.callback.payload.split("_")[-1]
    user_id = str(callback.callback.user.user_id)

    try:
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "idle",
                "context": {},
                "expiry_hours": 1
            }
        )

        keyboard = build_inline_keyboard([
            [CallbackButton(text="◀️ Вернуться к шагам", payload=f"view_goal_{goal_id}")],
            [CallbackButton(text="🏠 Главное меню", payload="main_menu")]
        ])

        await callback.message.edit(
            text="✅ Вы вышли из режима редактирования.",
            attachments=_attachments(keyboard),
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        logger.exception(f"Error cancelling edit mode: {e}")
        await callback.message.bot.send_message(
            chat_id=callback.message.recipient.chat_id,
            text="Произошла ошибка"
        )


@dp.message_callback(F.callback.payload.startswith("toggle_step_"))
async def callback_toggle_step(callback: MessageCallback):
    parts = callback.callback.payload.split("_")
    step_id = parts[2]
    goal_id = parts[3]
    user_id = str(callback.callback.user.user_id)

    try:
        goal_response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
            params={"user_id": user_id}
        )

        if goal_response.status_code == 200:
            goal = goal_response.json()
            steps = goal.get("steps", [])

            current_step = next((step for step in steps if str(step.get("id")) == step_id), None)
            if not current_step:
                await callback.message.bot.send_message(
                    chat_id=callback.message.recipient.chat_id,
                    text="Шаг не найден"
                )
                return

            current_status = current_step.get("status", "pending")
            new_status = "completed" if current_status != "completed" else "pending"

            update_response = await http_client.put(
                f"{CORE_SERVICE_URL}/api/steps/{step_id}/status",
                json={"status": new_status, "user_id": user_id}
            )

            if update_response.status_code == 200:
                updated_goal_response = await http_client.get(
                    f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
                    params={"user_id": user_id}
                )

                if updated_goal_response.status_code == 200:
                    updated_goal = updated_goal_response.json()
                    rendered = render_goal_detail(updated_goal)

                    updated_buttons: List[List[CallbackButton]] = []
                    for step in updated_goal.get("steps", []):
                        s_id = step.get("id")
                        s_status = step.get("status", "pending")
                        s_title = step.get("title", "")

                        if s_status == "completed":
                            emoji = "✅"
                        elif s_status == "in_progress":
                            emoji = "🔄"
                        else:
                            emoji = "⭕"

                        text = s_title[:40] + "..." if len(s_title) > 40 else s_title
                        updated_buttons.append([
                            CallbackButton(text=f"{emoji} {text}", payload=f"toggle_step_{s_id}_{goal_id}")
                        ])

                    updated_buttons.append([
                        CallbackButton(text="◀️ К списку целей", payload="show_goals"),
                        CallbackButton(text="🏠 Меню", payload="main_menu"),
                    ])

                    keyboard = build_inline_keyboard(updated_buttons)
                    await callback.message.edit(
                        text=rendered,
                        attachments=_attachments(keyboard),
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await callback.message.bot.send_message(
                        chat_id=callback.message.recipient.chat_id,
                        text="Не удалось обновить цель"
                    )
            else:
                await callback.message.bot.send_message(
                    chat_id=callback.message.recipient.chat_id,
                    text="Не удалось обновить шаг"
                )
        else:
            await callback.message.bot.send_message(
                chat_id=callback.message.recipient.chat_id,
                text="Не удалось загрузить цель"
            )

    except Exception as e:
        logger.exception(f"Error toggling step {step_id}: {e}")
        await callback.message.bot.send_message(
            chat_id=callback.message.recipient.chat_id,
            text="Произошла ошибка"
        )


@dp.message_callback(F.callback.payload.startswith(("schedule_", "time_pref", "day_pref")))
async def callback_scheduling(callback: MessageCallback):
    user_id = str(callback.callback.user.user_id)
    payload = callback.callback.payload

    try:
        response = await http_client.post(
            f"{ORCHESTRATOR_URL}/api/callback",
            json={
                "user_id": user_id,
                "callback_data": payload
            },
            timeout=30.0
        )

        if response.status_code != 200:
            logger.error(f"Orchestrator callback error: {response.status_code}")
            await callback.message.bot.send_message(
                chat_id=callback.message.recipient.chat_id,
                text="Произошла ошибка"
            )
            return

        result = response.json()
        response_type = result.get("response_type", "text")
        text = result.get("text", "")
        buttons_data = result.get("buttons", [])

        keyboard = None
        if buttons_data:
            is_days = "day_pref" in payload
            row_size = 3 if is_days and len(buttons_data) > 4 else 2

            rows: List[List[CallbackButton]] = []
            current_row: List[CallbackButton] = []
            for btn in buttons_data:
                current_row.append(
                    CallbackButton(text=btn["text"], payload=btn["callback"])
                )
                if len(current_row) >= row_size:
                    rows.append(current_row)
                    current_row = []

            if current_row:
                rows.append(current_row)

            keyboard = build_inline_keyboard(rows)

        if response_type == "inline_buttons" and keyboard:
            await callback.message.edit(
                text=text,
                attachments=_attachments(keyboard),
                parse_mode=ParseMode.HTML
            )
        elif text:
            await callback.message.edit(
                text=text,
                parse_mode=ParseMode.HTML
            )

    except Exception as e:
        logger.exception(f"[{user_id}] Error handling scheduling callback: {e}")
        await callback.message.bot.send_message(
            chat_id=callback.message.recipient.chat_id,
            text="Произошла ошибка"
        )


async def _download_attachment(attachment) -> Optional[bytes]:
    payload = getattr(attachment, "payload", None)
    if not payload:
        return None

    url = getattr(payload, "url", None)
    token = getattr(payload, "token", None)
    if not url:
        return None

    headers = {"Authorization": f"Bearer {token}"} if token else None
    response = await http_client.get(url, headers=headers)
    if response.status_code != 200:
        return None
    return response.content


async def process_voice_message(event: MessageCreated, audio_attachment):
    user_id = str(event.message.sender.user_id)
    logger.info(f"[{user_id}] Received voice message")

    await send_typing(event.message.bot, event.message.recipient.chat_id)

    try:
        audio_bytes = await _download_attachment(audio_attachment)
        if not audio_bytes:
            await event.message.answer("😔 Не удалось загрузить голосовое сообщение. Попробуй ещё раз.")
            return

        track_event(user_id, "Message Received", {
            "message_type": "voice",
        })
        increment_user_counter(user_id, "total_messages", 1)

        transcribe_response = await http_client.post(
            f"{LLM_SERVICE_URL}/api/transcribe",
            content=audio_bytes,
            headers={"Content-Type": "application/octet-stream"},
            params={"user_id": user_id}
        )

        if transcribe_response.status_code != 200:
            logger.error(f"Transcription error: {transcribe_response.status_code} {transcribe_response.text}")
            await event.message.answer("😔 Не удалось распознать голосовое сообщение. Попробуй ещё раз.")
            return

        transcription = transcribe_response.json()
        text = transcription.get("text")
        if not text:
            await event.message.answer("😔 Не удалось распознать голосовое сообщение. Попробуй ещё раз.")
            return

        await handle_user_message(event, text_override=text)

    except httpx.TimeoutException:
        logger.error(f"[{user_id}] Transcription timeout")
        await event.message.answer(
            "⏱️ Запрос занял слишком много времени.\n\n"
            "Пожалуйста, попробуй ещё раз."
        )
    except Exception:
        logger.exception(f"[{user_id}] Error processing voice message")
        await event.message.answer(
            "😔 Упс, произошла ошибка при обработке голосового сообщения.\n\n"
            "Попробуй ещё раз."
        )


async def handle_user_message(event: MessageCreated, text_override: Optional[str] = None):
    user_id = str(event.message.sender.user_id)
    user_msg = text_override or (event.message.body.text or "").strip()

    if not user_msg:
        return

    # Skip commands - they should be handled by specific command handlers
    if user_msg.startswith('/'):
        return

    logger.info(f"[{user_id}] Received: {user_msg[:50]}...")

    track_event(user_id, "Message Received", {
        "message_type": "text",
        "message_length": len(user_msg)
    })
    increment_user_counter(user_id, "total_messages", 1)

    await send_typing(event.message.bot, event.message.recipient.chat_id)

    try:
        response = await http_client.post(
            f"{ORCHESTRATOR_URL}/api/process",
            json={"user_id": user_id, "message": user_msg},
            timeout=30.0
        )

        if response.status_code != 200:
            logger.error(f"Orchestrator error: {response.status_code} {response.text}")
            keyboard = keyboard_from_pairs([[ ("🏠 Вернуться в меню", "main_menu") ]])
            await event.message.answer(
                "😔 Упс, что-то пошло не так.\n\n"
                "Попробуй ещё раз или вернись в главное меню.",
                attachments=_attachments(keyboard)
            )
            return

        result = response.json()
        logger.info(f"[{user_id}] Orchestrator response: {result}")

        if not result.get("success"):
            error = result.get("error", "Неизвестная ошибка")
            keyboard = keyboard_from_pairs([[ ("🏠 Главное меню", "main_menu") ]])
            await event.message.answer(
                f"😔 Произошла ошибка: {error}\n\n"
                "Попробуй переформулировать запрос или вернись в меню.",
                attachments=_attachments(keyboard)
            )
            return

        response_type = result.get("response_type", "text")
        text = result.get("text")

        if response_type == "inline_buttons":
            buttons_data = result.get("buttons", [])
            if buttons_data:
                rows = [
                    [CallbackButton(text=btn["text"], payload=btn["callback"])]
                    for btn in buttons_data
                ]
                keyboard = build_inline_keyboard(rows)
                await event.message.answer(
                    text,
                    attachments=_attachments(keyboard),
                    parse_mode=ParseMode.HTML
                )
            else:
                await event.message.answer(text, parse_mode=ParseMode.HTML)

        elif response_type == "table":
            items = result.get("items", [])
            if items:
                first_item = items[0]
                if first_item.get("date"):
                    rendered = render_events(items, title=text or "События")
                    keyboard = keyboard_from_pairs([[ ("➕ Новое событие", "new_event"), ("🏠 Меню", "main_menu") ]])
                    await event.message.answer(
                        rendered,
                        attachments=_attachments(keyboard),
                        parse_mode=ParseMode.HTML
                    )
                elif first_item.get("steps"):
                    rendered = render_goals(items, title=text or "Цели")
                    keyboard = keyboard_from_pairs([[ ("➕ Новая цель", "new_goal"), ("🏠 Меню", "main_menu") ]])
                    await event.message.answer(
                        rendered,
                        attachments=_attachments(keyboard),
                        parse_mode=ParseMode.HTML
                    )
                elif first_item.get("price"):
                    rendered = render_products(items, title=text or "Товары")
                    await event.message.answer(rendered, parse_mode=ParseMode.HTML)
                elif first_item.get("product"):
                    rendered = render_cart(items, title=text or "Корзина")
                    await event.message.answer(rendered, parse_mode=ParseMode.HTML)
                else:
                    await event.message.answer("Результаты найдены, но формат не поддерживается.")
        elif text:
            await event.message.answer(text)

    except httpx.TimeoutException:
        logger.error(f"[{user_id}] Request timeout")
        keyboard = keyboard_from_pairs([[ ("🔄 Попробовать снова", "main_menu") ]])
        await event.message.answer(
            "⏱️ Запрос занял слишком много времени.\n\n"
            "Пожалуйста, попробуй ещё раз.",
            attachments=_attachments(keyboard)
        )
    except httpx.RequestError as e:
        logger.error(f"[{user_id}] HTTP error: {e}")
        keyboard = keyboard_from_pairs([[ ("🏠 Главное меню", "main_menu") ]])
        await event.message.answer(
            "🔌 Не могу связаться с сервером.\n\n"
            "Проверь подключение к интернету или попробуй позже.",
            attachments=_attachments(keyboard)
        )
    except Exception:
        logger.exception(f"[{user_id}] Unexpected error")
        keyboard = keyboard_from_pairs([[ ("🏠 Главное меню", "main_menu") ]])
        await event.message.answer(
            "😔 Упс, произошла непредвиденная ошибка.\n\n"
            "Попробуй ещё раз или свяжись с поддержкой.",
            attachments=_attachments(keyboard)
        )


@dp.message_created(F.message.body.text & ~F.message.body.text.startswith('/'))
async def handle_message(event: MessageCreated):
    attachments = event.message.body.attachments or []
    audio_attachment = next((att for att in attachments if getattr(att, "type", None) == AttachmentType.AUDIO), None)

    if audio_attachment and not (event.message.body.text and event.message.body.text.strip()):
        await process_voice_message(event, audio_attachment)
    else:
        await handle_user_message(event)


# --- Lifecycle ---

@dp.on_started()
async def on_started():
    await on_startup()


async def on_startup():
    logger.info("🚀 Starting MAX Bot...")
    logger.info(f"Orchestrator URL: {ORCHESTRATOR_URL}")

    try:
        response = await http_client.get(f"{ORCHESTRATOR_URL}/health", timeout=5.0)
        if response.status_code == 200:
            logger.info("✅ Orchestrator is reachable")
        else:
            logger.warning(f"⚠️ Orchestrator returned {response.status_code}")
    except Exception as e:
        logger.warning(f"⚠️ Cannot reach Orchestrator: {e}")

    commands = [
        BotCommand(name="/start", description="🏠 Главное меню"),
        BotCommand(name="/goals", description="🎯 Мои цели"),
        BotCommand(name="/events", description="📅 Календарь событий"),
        BotCommand(name="/calendar", description="🗓 Мой календарь"),
        BotCommand(name="/stats", description="📊 Личная статистика"),
        BotCommand(name="/leaderboard", description="🏆 Лидерборд"),
        BotCommand(name="/webapp", description="🚀 Открыть Web App"),
    ]
    await bot.set_my_commands(*commands)
    logger.info("✅ Bot commands menu set")


async def on_shutdown():
    logger.info("Shutting down MAX Bot...")
    await http_client.aclose()
    await bot.close_session()


async def main():
    try:
        await bot.delete_webhook()
    except Exception as e:
        logger.warning(f"Could not delete webhook: {e}")

    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())

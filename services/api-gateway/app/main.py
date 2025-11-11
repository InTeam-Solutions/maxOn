import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
import httpx

from app.renderer import render_events, render_goals, render_products, render_cart, render_goals_list, render_goal_detail
from shared.utils.analytics import track_event, increment_user_counter, set_user_profile

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# --- Configuration ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8001")
CORE_SERVICE_URL = os.getenv("CORE_SERVICE_URL", "http://core:8004")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://llm:8003")
CONTEXT_SERVICE_URL = os.getenv("CONTEXT_SERVICE_URL", "http://context:8002")

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

# --- Bot initialization ---
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# HTTP client for Orchestrator
http_client = httpx.AsyncClient(timeout=30.0)


# --- Handlers ---

async def get_dashboard_stats(user_id: str) -> str:
    """Get user dashboard with upcoming events and goals progress"""
    try:
        from datetime import datetime, timedelta
        import random

        stats_lines = []

        # Get upcoming events (next 3 days)
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
                for event in events[:3]:  # First 3
                    title = event.get("title", "Событие")
                    date = event.get("date", "")
                    time = event.get("time", "")

                    # Format date
                    try:
                        date_obj = datetime.fromisoformat(date)
                        weekday = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date_obj.weekday()]
                        date_str = f"{weekday}, {date_obj.strftime('%d.%m')}"
                    except:
                        date_str = date

                    time_str = f" в {time}" if time else ""
                    stats_lines.append(f"  • {title} — {date_str}{time_str}")
                stats_lines.append("")

        # Get active goals
        goals_response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals",
            params={"user_id": user_id, "status": "active"}
        )

        if goals_response.status_code == 200:
            goals = goals_response.json()
            if goals:
                stats_lines.append("🎯 <b>Твои цели:</b>")
                total_progress = sum(g.get("progress_percent", 0) for g in goals) / len(goals) if goals else 0
                stats_lines.append(f"  Общий прогресс: <b>{total_progress:.0f}%</b>")

                completed_goals = len([g for g in goals if g.get("status") == "completed"])
                stats_lines.append(f"  Активных целей: <b>{len(goals)}</b>")

                # Random goal motivation
                if goals:
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


@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command"""
    user_id = str(message.from_user.id)

    # Reset session state to idle (clear any previous dialog state)
    try:
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "idle",
                "context": {},
                "expiry_hours": 1
            }
        )
        logger.info(f"Reset session state for user {user_id} to idle on /start")
    except Exception as e:
        logger.error(f"Error resetting session state: {e}")

    # Track user start
    track_event(user_id, "Bot Started", {
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "language_code": message.from_user.language_code
    })
    set_user_profile(user_id, {
        "$name": message.from_user.full_name,
        "username": message.from_user.username,
        "language": message.from_user.language_code or "ru"
    })

    # Get dashboard stats
    stats = await get_dashboard_stats(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎯 Мои цели", callback_data="show_goals"),
            InlineKeyboardButton(text="📅 Календарь", callback_data="show_events")
        ],
        [
            InlineKeyboardButton(text="➕ Новая цель", callback_data="new_goal"),
            InlineKeyboardButton(text="➕ Событие", callback_data="new_event")
        ]
    ])

    await message.answer(
        f"👋 <b>Привет! Я твой персональный коуч.</b>\n\n"
        f"{stats}\n\n"
        f"Используй кнопки ниже или просто напиши мне:",
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def show_goals_for_user(chat_id: int, user_id: str, bot_instance):
    """Show goals for a specific user - reusable function"""
    # Show typing indicator
    await bot_instance.send_chat_action(chat_id=chat_id, action="typing")

    try:
        # Direct call to Core Service (no LLM involved)
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals",
            params={"user_id": user_id, "status": "active"}
        )

        if response.status_code == 200:
            goals = response.json()

            if goals:
                rendered = render_goals_list(goals, title="🎯 Твои цели")

                # Create buttons for each goal
                goal_buttons = []
                for idx, goal in enumerate(goals, 1):
                    goal_id = goal.get("id")
                    goal_title = goal.get("title", "Без названия")
                    # Truncate title for button if too long
                    button_text = goal_title[:35] + "..." if len(goal_title) > 35 else goal_title
                    goal_buttons.append([
                        InlineKeyboardButton(text=f"{idx}. {button_text}", callback_data=f"view_goal_{goal_id}")
                    ])

                # Add action buttons at the bottom
                goal_buttons.append([
                    InlineKeyboardButton(text="➕ Новая цель", callback_data="new_goal"),
                    InlineKeyboardButton(text="✏️ Редактировать", callback_data="settings_goals")
                ])
                goal_buttons.append([
                    InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
                ])

                keyboard = InlineKeyboardMarkup(inline_keyboard=goal_buttons)

                await bot_instance.send_message(chat_id, rendered, parse_mode="HTML", reply_markup=keyboard)
            else:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Создать первую цель", callback_data="new_goal")]
                ])
                await bot_instance.send_message(
                    chat_id,
                    "🎯 <b>Твои цели</b>\n\n"
                    "<i>Целей пока нет. Создай свою первую цель!</i>",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
        else:
            raise Exception(f"Core Service returned {response.status_code}")

    except Exception as e:
        logger.exception(f"Error loading goals: {e}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        await bot_instance.send_message(
            chat_id,
            "😔 Не удалось загрузить цели.\n\n"
            "Попробуй ещё раз или вернись в меню.",
            reply_markup=keyboard
        )


@dp.message(Command("goals"))
async def cmd_goals(message: Message):
    """Handle /goals command - direct system call"""
    user_id = str(message.from_user.id)
    await show_goals_for_user(message.chat.id, user_id, message.bot)


async def show_events_for_user(chat_id: int, user_id: str, bot_instance):
    """Show events for a specific user - reusable function"""
    # Show typing indicator
    await bot_instance.send_chat_action(chat_id=chat_id, action="typing")

    try:
        # Direct call to Core Service (no LLM involved)
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

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="➕ Новое событие", callback_data="new_event"),
                        InlineKeyboardButton(text="✏️ Редактировать", callback_data="settings_events")
                    ],
                    [
                        InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
                    ]
                ])

                await bot_instance.send_message(chat_id, rendered, parse_mode="HTML", reply_markup=keyboard)
            else:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Создать событие", callback_data="new_event")]
                ])
                await bot_instance.send_message(
                    chat_id,
                    "📅 <b>События на этой неделе</b>\n\n"
                    "<i>Событий не найдено.</i>",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
        else:
            raise Exception(f"Core Service returned {response.status_code}")

    except Exception as e:
        logger.exception(f"Error loading events: {e}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        await bot_instance.send_message(
            chat_id,
            "😔 Не удалось загрузить события.\n\n"
            "Попробуй ещё раз или вернись в меню.",
            reply_markup=keyboard
        )


@dp.message(Command("events"))
async def cmd_events(message: Message):
    """Handle /events command - direct system call"""
    user_id = str(message.from_user.id)
    await show_events_for_user(message.chat.id, user_id, message.bot)


@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    """Handle /settings command - show notification settings"""
    user_id = str(message.from_user.id)
    chat_id = message.chat.id
    await show_settings(chat_id, user_id, message.bot)


@dp.callback_query(F.data == "show_goals")
async def callback_show_goals(callback: CallbackQuery):
    """Handle show_goals button"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    await show_goals_for_user(callback.message.chat.id, user_id, callback.bot)


@dp.callback_query(F.data == "show_events")
async def callback_show_events(callback: CallbackQuery):
    """Handle show_events button"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    await show_events_for_user(callback.message.chat.id, user_id, callback.bot)


@dp.callback_query(F.data == "new_goal")
async def callback_new_goal(callback: CallbackQuery):
    """Handle new_goal button"""
    await callback.answer()

    user_id = str(callback.from_user.id)

    # Set state to goal_clarification to indicate user wants to create a new goal
    try:
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "goal_clarification",
                "context": {},
                "expiry_hours": 4
            }
        )
        logger.info(f"Set session state for user {user_id} to goal_clarification")
    except Exception as e:
        logger.error(f"Error setting session state: {e}")

    await callback.message.answer(
        "💡 Отлично! Расскажи мне о своей цели.\n\n"
        "Например:\n"
        "• Выучить английский до уровня B2\n"
        "• Научиться программировать на Python\n"
        "• Похудеть на 10 кг за 3 месяца\n\n"
        "Я автоматически создам пошаговый план для её достижения!"
    )


@dp.callback_query(F.data == "new_event")
async def callback_new_event(callback: CallbackQuery):
    """Handle new_event button"""
    await callback.answer()

    user_id = str(callback.from_user.id)

    # Show calendar for date selection
    from app.renderer import create_calendar_keyboard

    calendar_keyboard = create_calendar_keyboard()

    await callback.message.answer(
        "📅 <b>Создание события</b>\n\nВыбери дату события:",
        reply_markup=calendar_keyboard,
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """Handle main_menu button - return to start"""
    await callback.answer()
    user_id = str(callback.from_user.id)

    # Reset session state (exit any editing mode)
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

    # Get dashboard stats
    stats = await get_dashboard_stats(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎯 Мои цели", callback_data="show_goals"),
            InlineKeyboardButton(text="📅 Календарь", callback_data="show_events")
        ],
        [
            InlineKeyboardButton(text="➕ Новая цель", callback_data="new_goal"),
            InlineKeyboardButton(text="➕ Событие", callback_data="new_event")
        ]
    ])

    await callback.message.edit_text(
        f"🏠 <b>Главное меню</b>\n\n"
        f"{stats}\n\n"
        f"Выбери действие или просто напиши мне что-нибудь:",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("view_goal_"))
async def callback_view_goal(callback: CallbackQuery):
    """Handle view_goal_{goal_id} button - show goal details"""
    await callback.answer()

    goal_id = callback.data.split("_")[-1]
    user_id = str(callback.from_user.id)

    await callback.bot.send_chat_action(chat_id=callback.message.chat.id, action="typing")

    try:
        # Fetch goal details from Core Service
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
            params={"user_id": user_id}
        )

        if response.status_code == 200:
            goal = response.json()
            rendered = render_goal_detail(goal)

            # Create buttons for each step
            step_buttons = []
            steps = goal.get("steps", [])

            for step in steps:
                step_id = step.get("id")
                step_status = step.get("status", "pending")
                step_title = step.get("title", "")

                # Button text with emoji
                if step_status == "completed":
                    emoji = "✅"
                elif step_status == "in_progress":
                    emoji = "🔄"
                else:
                    emoji = "⭕"

                # Truncate step title for button
                button_text = step_title[:40] + "..." if len(step_title) > 40 else step_title

                step_buttons.append([
                    InlineKeyboardButton(
                        text=f"{emoji} {button_text}",
                        callback_data=f"toggle_step_{step_id}_{goal_id}"
                    )
                ])

            # Add edit button
            step_buttons.append([
                InlineKeyboardButton(text="✏️ Поправить шаги", callback_data=f"edit_goal_steps_{goal_id}")
            ])

            # Add navigation buttons
            step_buttons.append([
                InlineKeyboardButton(text="◀️ К списку целей", callback_data="show_goals"),
                InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
            ])

            keyboard = InlineKeyboardMarkup(inline_keyboard=step_buttons)

            await callback.message.edit_text(rendered, parse_mode="HTML", reply_markup=keyboard)
        else:
            await callback.message.edit_text(
                "😔 Не удалось загрузить цель.\n\nПопробуй ещё раз.",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.exception(f"Error loading goal {goal_id}: {e}")
        await callback.message.edit_text(
            "😔 Произошла ошибка при загрузке цели.",
            parse_mode="HTML"
        )


@dp.callback_query(F.data.startswith("edit_goal_steps_"))
async def callback_edit_goal_steps(callback: CallbackQuery):
    """Handle edit_goal_steps_{goal_id} button - enter edit mode"""
    await callback.answer()

    goal_id = callback.data.split("_")[-1]
    user_id = str(callback.from_user.id)

    try:
        # Get goal details
        goal_response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
            params={"user_id": user_id}
        )

        if goal_response.status_code == 200:
            goal = goal_response.json()
            goal_title = goal.get("title", "цели")

            # Update session state to editing mode
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

            # Show instruction message
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить редактирование", callback_data=f"cancel_edit_{goal_id}")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])

            await callback.message.edit_text(
                f"✏️ <b>Режим редактирования шагов</b>\n\n"
                f"Цель: <i>{goal_title}</i>\n\n"
                f"Теперь ты можешь попросить меня:\n"
                f"• Добавить новый шаг\n"
                f"• Изменить формулировку шага\n"
                f"• Удалить шаг\n"
                f"• Изменить порядок шагов\n\n"
                f"Просто напиши мне что нужно изменить, например:\n"
                f"<i>\"Добавь шаг: изучить основы Python\"</i>\n"
                f"<i>\"Удали третий шаг\"</i>\n"
                f"<i>\"Переформулируй первый шаг на более простой язык\"</i>\n\n"
                f"💡 Я работаю только с этой целью, пока ты не выйдешь из режима редактирования.",
                parse_mode="HTML",
                reply_markup=keyboard
            )

        else:
            await callback.answer("Не удалось загрузить цель", show_alert=True)

    except Exception as e:
        logger.exception(f"Error entering edit mode for goal {goal_id}: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@dp.callback_query(F.data.startswith("cancel_edit_"))
async def callback_cancel_edit(callback: CallbackQuery):
    """Cancel editing mode and return to goal view"""
    await callback.answer()

    goal_id = callback.data.split("_")[-1]
    user_id = str(callback.from_user.id)

    try:
        # Reset session state
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "idle",
                "context": {},
                "expiry_hours": 1
            }
        )

        # Return to goal view - trigger view_goal callback
        await callback.message.edit_text("Возвращаюсь к просмотру цели...")

        # Simulate view_goal callback
        callback.data = f"view_goal_{goal_id}"
        await callback_view_goal(callback)

    except Exception as e:
        logger.exception(f"Error cancelling edit mode: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@dp.callback_query(F.data.startswith("toggle_step_"))
async def callback_toggle_step(callback: CallbackQuery):
    """Handle toggle_step_{step_id}_{goal_id} button - mark step as completed/pending"""
    parts = callback.data.split("_")
    step_id = parts[2]
    goal_id = parts[3]
    user_id = str(callback.from_user.id)

    try:
        # Get current step status
        goal_response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
            params={"user_id": user_id}
        )

        if goal_response.status_code == 200:
            goal = goal_response.json()
            steps = goal.get("steps", [])

            # Find the step
            current_step = None
            for step in steps:
                if str(step.get("id")) == step_id:
                    current_step = step
                    break

            if not current_step:
                await callback.answer("Шаг не найден", show_alert=True)
                return

            current_status = current_step.get("status", "pending")

            # Toggle status: pending/in_progress → completed, completed → pending
            new_status = "completed" if current_status != "completed" else "pending"

            # Update step status via Core Service
            update_response = await http_client.put(
                f"{CORE_SERVICE_URL}/api/steps/{step_id}/status",
                json={"status": new_status, "user_id": user_id}
            )

            if update_response.status_code == 200:
                # Fetch updated goal
                updated_goal_response = await http_client.get(
                    f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
                    params={"user_id": user_id}
                )

                if updated_goal_response.status_code == 200:
                    updated_goal = updated_goal_response.json()
                    rendered = render_goal_detail(updated_goal)

                    # Recreate buttons with updated status
                    step_buttons = []
                    updated_steps = updated_goal.get("steps", [])

                    for step in updated_steps:
                        s_id = step.get("id")
                        s_status = step.get("status", "pending")
                        s_title = step.get("title", "")

                        # Button text with emoji
                        if s_status == "completed":
                            emoji = "✅"
                        elif s_status == "in_progress":
                            emoji = "🔄"
                        else:
                            emoji = "⭕"

                        # Truncate step title for button
                        button_text = s_title[:40] + "..." if len(s_title) > 40 else s_title

                        step_buttons.append([
                            InlineKeyboardButton(
                                text=f"{emoji} {button_text}",
                                callback_data=f"toggle_step_{s_id}_{goal_id}"
                            )
                        ])

                    # Add navigation buttons
                    step_buttons.append([
                        InlineKeyboardButton(text="◀️ К списку целей", callback_data="show_goals"),
                        InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
                    ])

                    keyboard = InlineKeyboardMarkup(inline_keyboard=step_buttons)

                    await callback.message.edit_text(rendered, parse_mode="HTML", reply_markup=keyboard)

                    # Show toast notification
                    if new_status == "completed":
                        await callback.answer("✅ Шаг отмечен как выполненный!", show_alert=False)
                    else:
                        await callback.answer("⭕ Шаг отмечен как невыполненный", show_alert=False)
                else:
                    await callback.answer("Не удалось обновить цель", show_alert=True)
            else:
                await callback.answer("Не удалось обновить шаг", show_alert=True)
        else:
            await callback.answer("Не удалось загрузить цель", show_alert=True)

    except Exception as e:
        logger.exception(f"Error toggling step {step_id}: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


# ==================== SCHEDULING CALLBACK HANDLERS ====================

@dp.callback_query(F.data.startswith(("schedule_", "time_pref", "day_pref")))
async def callback_scheduling(callback: CallbackQuery):
    """Handle all scheduling-related callbacks"""
    user_id = str(callback.from_user.id)
    callback_data = callback.data

    try:
        logger.info(f"[{user_id}] Scheduling callback: {callback_data}")

        # Send callback to Orchestrator
        response = await http_client.post(
            f"{ORCHESTRATOR_URL}/api/callback",
            json={
                "user_id": user_id,
                "callback_data": callback_data
            },
            timeout=30.0
        )

        if response.status_code != 200:
            logger.error(f"Orchestrator callback error: {response.status_code}")
            await callback.answer("Произошла ошибка", show_alert=True)
            return

        result = response.json()
        response_type = result.get("response_type", "text")
        text = result.get("text", "")
        buttons_data = result.get("buttons", [])

        # Build inline keyboard if buttons provided
        keyboard = None
        if buttons_data:
            # Split buttons into rows (2 per row for most, except days which are 3 per row)
            is_days = "day_pref" in callback_data
            row_size = 3 if is_days and len(buttons_data) > 4 else 2

            button_rows = []
            current_row = []

            for btn in buttons_data:
                current_row.append(
                    InlineKeyboardButton(
                        text=btn["text"],
                        callback_data=btn["callback"]
                    )
                )

                if len(current_row) >= row_size:
                    button_rows.append(current_row)
                    current_row = []

            if current_row:
                button_rows.append(current_row)

            keyboard = InlineKeyboardMarkup(inline_keyboard=button_rows)

        # Update message or send new one
        if response_type == "inline_buttons" and keyboard:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            await callback.answer()
        elif text:
            # For non-button responses, edit message and show notification
            await callback.message.edit_text(text, parse_mode="HTML")
            await callback.answer()
        else:
            await callback.answer("OK")

    except Exception as e:
        logger.exception(f"[{user_id}] Error handling scheduling callback")
        await callback.answer("Произошла ошибка", show_alert=True)


@dp.message(F.voice)
async def handle_voice(message: types.Message):
    """Handle voice messages - transcribe and process"""
    user_id = str(message.from_user.id)
    logger.info(f"[{user_id}] Received voice message")

    # Send "typing" action
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # Download voice file
        voice = message.voice
        file = await message.bot.get_file(voice.file_id)
        voice_bytes = await message.bot.download_file(file.file_path)

        # Transcribe via LLM service
        logger.info(f"[{user_id}] Transcribing voice message...")

        # Track voice message received
        track_event(user_id, "Message Received", {
            "message_type": "voice",
            "audio_duration": voice.duration
        })
        increment_user_counter(user_id, "total_messages", 1)

        transcribe_response = await http_client.post(
            f"{LLM_SERVICE_URL}/api/transcribe",
            content=voice_bytes.read(),
            headers={"Content-Type": "application/octet-stream"},
            params={"user_id": user_id}
        )

        if transcribe_response.status_code != 200:
            logger.error(f"Transcription error: {transcribe_response.status_code} {transcribe_response.text}")
            await message.answer("😔 Не удалось распознать голосовое сообщение. Попробуй ещё раз.")
            return

        transcription = transcribe_response.json()
        user_msg = transcription.get("text", "")

        if not user_msg:
            await message.answer("😔 Не удалось распознать речь. Попробуй ещё раз.")
            return

        logger.info(f"[{user_id}] Transcribed: {user_msg[:50]}...")

        # Show transcribed text to user
        await message.answer(f"🎤 <i>Распознано: {user_msg}</i>", parse_mode="HTML")

        # Process as regular text message
        response = await http_client.post(
            f"{ORCHESTRATOR_URL}/api/process",
            json={
                "user_id": user_id,
                "message": user_msg
            },
            timeout=30.0
        )

        if response.status_code != 200:
            logger.error(f"Orchestrator error: {response.status_code} {response.text}")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Вернуться в меню", callback_data="main_menu")]
            ])
            await message.answer(
                "😔 Упс, что-то пошло не так.\n\n"
                "Попробуй ещё раз или вернись в главное меню.",
                reply_markup=keyboard
            )
            return

        result = response.json()
        logger.info(f"[{user_id}] Orchestrator response: {result}")

        if not result.get("success"):
            error = result.get("error", "Неизвестная ошибка")
            logger.error(f"[{user_id}] Processing failed: {error}")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
            await message.answer(
                f"😔 Произошла ошибка: {error}\n\n"
                "Попробуй переформулировать запрос или вернись в меню.",
                reply_markup=keyboard
            )
            return

        # Handle response (same logic as text messages)
        response_type = result.get("response_type", "text")
        text = result.get("text")

        if response_type == "table":
            items = result.get("items", [])
            if items:
                if items[0].get("date"):  # Events
                    rendered = render_events(items, title=text or "События")
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="➕ Новое событие", callback_data="new_event"),
                            InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
                        ]
                    ])
                    await message.answer(rendered, parse_mode="HTML", reply_markup=keyboard)
                elif items[0].get("steps"):  # Goals
                    rendered = render_goals(items, title=text or "Цели")
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="➕ Новая цель", callback_data="new_goal"),
                            InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
                        ]
                    ])
                    await message.answer(rendered, parse_mode="HTML", reply_markup=keyboard)
                elif items[0].get("price"):  # Products
                    rendered = render_products(items, title=text or "Товары")
                    await message.answer(rendered, parse_mode="HTML")
        elif text:
            if "цель" in text.lower() and ("создал" in text.lower() or "отлично" in text.lower()):
                await message.react([types.ReactionTypeEmoji(emoji="🎉")])
            elif "удалил" in text.lower():
                await message.react([types.ReactionTypeEmoji(emoji="👍")])
            await message.answer(text)

    except httpx.TimeoutException:
        logger.error(f"[{user_id}] Request timeout")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="main_menu")]
        ])
        await message.answer(
            "⏱️ Запрос занял слишком много времени.\n\n"
            "Пожалуйста, попробуй ещё раз.",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"[{user_id}] Error processing voice message")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        await message.answer(
            "😔 Упс, произошла ошибка при обработке голосового сообщения.\n\n"
            "Попробуй ещё раз.",
            reply_markup=keyboard
        )


@dp.message()
async def handle_message(message: types.Message):
    """Handle all text messages"""
    user_id = str(message.from_user.id)
    user_msg = message.text

    if not user_msg:
        return

    logger.info(f"[{user_id}] Received: {user_msg[:50]}...")

    # Track message received
    track_event(user_id, "Message Received", {
        "message_type": "text",
        "message_length": len(user_msg)
    })
    increment_user_counter(user_id, "total_messages", 1)

    # Send "typing" action for better UX
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # Check if user is in an editing state
        session_response = await http_client.get(f"{CONTEXT_SERVICE_URL}/api/session/{user_id}")

        if session_response.status_code == 200:
            session = session_response.json()
            current_state = session.get("current_state", "idle")
            context = session.get("context", {})

            # Handle event field editing
            if current_state.startswith("event_edit_"):
                field = current_state.replace("event_edit_", "")
                event_id = context.get("event_id")

                if event_id:
                    try:
                        # Prepare update data based on field
                        update_data = {}

                        if field == "title":
                            update_data["title"] = user_msg
                        elif field == "date":
                            update_data["date"] = user_msg
                        elif field == "time_start":
                            update_data["time_start"] = user_msg
                        elif field == "time_end":
                            update_data["time_end"] = user_msg if user_msg.strip() else None
                        elif field == "duration":
                            try:
                                update_data["duration_minutes"] = int(user_msg)
                            except ValueError:
                                await message.answer(
                                    "❌ Пожалуйста, введи число (длительность в минутах)",
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"manage_event_{event_id}")]
                                    ])
                                )
                                return
                        elif field == "repeat":
                            update_data["repeat_pattern"] = user_msg if user_msg.strip() else None
                        elif field == "notes":
                            update_data["notes"] = user_msg

                        # Update event via Core Service
                        update_response = await http_client.patch(
                            f"{CORE_SERVICE_URL}/api/events/{event_id}",
                            params={"user_id": user_id},
                            json=update_data
                        )

                        if update_response.status_code == 200:
                            # Reset session state
                            await http_client.put(
                                f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
                                json={
                                    "current_state": "idle",
                                    "context": {},
                                    "expiry_hours": 1
                                }
                            )

                            # Show success and redirect to event detail
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="◀️ К событию", callback_data=f"manage_event_{event_id}")],
                                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
                            ])

                            field_names = {
                                "title": "название",
                                "date": "дата",
                                "time_start": "время начала",
                                "time_end": "время окончания",
                                "duration": "длительность",
                                "repeat": "повторение",
                                "notes": "заметки"
                            }

                            await message.answer(
                                f"✅ Успешно обновлено поле: <b>{field_names.get(field, field)}</b>",
                                parse_mode="HTML",
                                reply_markup=keyboard
                            )
                            return
                        else:
                            raise Exception("Failed to update event")

                    except Exception as e:
                        logger.exception(f"Error updating event field: {e}")
                        await message.answer(
                            "❌ Произошла ошибка при обновлении события.",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="◀️ Назад", callback_data=f"manage_event_{event_id}")]
                            ])
                        )
                        return

            # Handle goal field editing
            elif current_state.startswith("goal_edit_"):
                field = current_state.replace("goal_edit_", "")
                goal_id = context.get("goal_id")

                if goal_id:
                    try:
                        # Prepare update data based on field
                        update_data = {}

                        if field == "title":
                            update_data["title"] = user_msg
                        elif field == "description":
                            update_data["description"] = user_msg
                        elif field == "deadline":
                            update_data["target_date"] = user_msg

                        # Update goal via Core Service
                        update_response = await http_client.patch(
                            f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
                            params={"user_id": user_id},
                            json=update_data
                        )

                        if update_response.status_code == 200:
                            # Reset session state
                            await http_client.put(
                                f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
                                json={
                                    "current_state": "idle",
                                    "context": {},
                                    "expiry_hours": 1
                                }
                            )

                            # Show success and redirect to goal detail
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="◀️ К цели", callback_data=f"manage_goal_{goal_id}")],
                                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
                            ])

                            field_names = {
                                "title": "название",
                                "description": "описание",
                                "deadline": "дедлайн"
                            }

                            await message.answer(
                                f"✅ Успешно обновлено поле: <b>{field_names.get(field, field)}</b>",
                                parse_mode="HTML",
                                reply_markup=keyboard
                            )
                            return
                        else:
                            raise Exception("Failed to update goal")

                    except Exception as e:
                        logger.exception(f"Error updating goal field: {e}")
                        await message.answer(
                            "❌ Произошла ошибка при обновлении цели.",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="◀️ Назад", callback_data=f"manage_goal_{goal_id}")]
                            ])
                        )
                        return

            # Handle step field editing
            elif current_state.startswith("step_edit_"):
                field = current_state.replace("step_edit_", "")
                step_id = context.get("step_id")

                if step_id:
                    try:
                        # Prepare update data based on field
                        update_data = {}

                        if field == "title":
                            update_data["title"] = user_msg
                        elif field == "description":
                            update_data["description"] = user_msg

                        # Update step via Core Service
                        update_response = await http_client.patch(
                            f"{CORE_SERVICE_URL}/api/steps/{step_id}",
                            params={"user_id": user_id},
                            json=update_data
                        )

                        if update_response.status_code == 200:
                            # Reset session state
                            await http_client.put(
                                f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
                                json={
                                    "current_state": "idle",
                                    "context": {},
                                    "expiry_hours": 1
                                }
                            )

                            # Show success and redirect to step detail
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="◀️ К шагу", callback_data=f"edit_step_{step_id}")],
                                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
                            ])

                            field_names = {
                                "title": "название",
                                "description": "описание"
                            }

                            await message.answer(
                                f"✅ Успешно обновлено поле: <b>{field_names.get(field, field)}</b>",
                                parse_mode="HTML",
                                reply_markup=keyboard
                            )
                            return
                        else:
                            raise Exception("Failed to update step")

                    except Exception as e:
                        logger.exception(f"Error updating step field: {e}")
                        await message.answer(
                            "❌ Произошла ошибка при обновлении шага.",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="◀️ Назад", callback_data=f"edit_step_{step_id}")]
                            ])
                        )
                        return

            # Handle adding a new step
            elif current_state == "step_add_title":
                goal_id = context.get("goal_id")

                if goal_id:
                    try:
                        # Get current steps count for order_index
                        steps_response = await http_client.get(
                            f"{CORE_SERVICE_URL}/api/goals/{goal_id}/steps",
                            params={"user_id": user_id}
                        )

                        order_index = 0
                        if steps_response.status_code == 200:
                            steps = steps_response.json()
                            order_index = len(steps)

                        # Create new step via Core Service
                        create_response = await http_client.post(
                            f"{CORE_SERVICE_URL}/api/steps",
                            params={"user_id": user_id},
                            json={
                                "goal_id": goal_id,
                                "title": user_msg,
                                "status": "pending",
                                "order_index": order_index
                            }
                        )

                        if create_response.status_code == 200:
                            # Reset session state
                            await http_client.put(
                                f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
                                json={
                                    "current_state": "idle",
                                    "context": {},
                                    "expiry_hours": 1
                                }
                            )

                            # Show success and redirect to steps list
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="◀️ К списку шагов", callback_data=f"manage_steps_{goal_id}")],
                                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
                            ])

                            await message.answer(
                                f"✅ Новый шаг добавлен: <b>{user_msg}</b>",
                                parse_mode="HTML",
                                reply_markup=keyboard
                            )
                            return
                        else:
                            raise Exception("Failed to create step")

                    except Exception as e:
                        logger.exception(f"Error creating step: {e}")
                        await message.answer(
                            "❌ Произошла ошибка при создании шага.",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="◀️ Назад", callback_data=f"manage_steps_{goal_id}")]
                            ])
                        )
                        return

        # Send to Orchestrator
        response = await http_client.post(
            f"{ORCHESTRATOR_URL}/api/process",
            json={
                "user_id": user_id,
                "message": user_msg
            },
            timeout=30.0
        )

        if response.status_code != 200:
            logger.error(f"Orchestrator error: {response.status_code} {response.text}")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Вернуться в меню", callback_data="main_menu")]
            ])
            await message.answer(
                "😔 Упс, что-то пошло не так.\n\n"
                "Попробуй ещё раз или вернись в главное меню.",
                reply_markup=keyboard
            )
            return

        result = response.json()
        logger.info(f"[{user_id}] Orchestrator response: {result}")

        if not result.get("success"):
            error = result.get("error", "Неизвестная ошибка")
            logger.error(f"[{user_id}] Processing failed: {error}")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
            await message.answer(
                f"😔 Произошла ошибка: {error}\n\n"
                "Попробуй переформулировать запрос или вернись в меню.",
                reply_markup=keyboard
            )
            return

        # Handle response based on type
        response_type = result.get("response_type", "text")
        text = result.get("text")

        if response_type == "inline_buttons":
            # Handle inline buttons response from Orchestrator
            buttons_data = result.get("buttons", [])
            if buttons_data:
                # Build inline keyboard
                button_rows = []
                for btn in buttons_data:
                    button_rows.append([
                        InlineKeyboardButton(
                            text=btn["text"],
                            callback_data=btn["callback"]
                        )
                    ])

                keyboard = InlineKeyboardMarkup(inline_keyboard=button_rows)
                await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
            else:
                # No buttons, just send text
                await message.answer(text, parse_mode="HTML")

        elif response_type == "table":
            items = result.get("items", [])
            if items:
                # Determine item type and render accordingly
                if items[0].get("date"):  # Events
                    rendered = render_events(items, title=text or "События")
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="➕ Новое событие", callback_data="new_event"),
                            InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
                        ]
                    ])
                    await message.answer(rendered, parse_mode="HTML", reply_markup=keyboard)

                elif items[0].get("steps"):  # Goals
                    rendered = render_goals(items, title=text or "Цели")
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="➕ Новая цель", callback_data="new_goal"),
                            InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
                        ]
                    ])
                    await message.answer(rendered, parse_mode="HTML", reply_markup=keyboard)

                elif items[0].get("price"):  # Products
                    rendered = render_products(items, title=text or "Товары")
                    await message.answer(rendered, parse_mode="HTML")

                elif items[0].get("product"):  # Cart items
                    rendered = render_cart(items, title=text or "Корзина")
                    await message.answer(rendered, parse_mode="HTML")
                else:
                    rendered = "Результаты найдены, но формат не поддерживается."
                    await message.answer(rendered, parse_mode="HTML")

        elif text:
            # Only send text if not table (table uses text as title)
            # Add reaction emoji based on intent
            if "цель" in text.lower() and ("создал" in text.lower() or "отлично" in text.lower()):
                await message.react([types.ReactionTypeEmoji(emoji="🎉")])
            elif "удалил" in text.lower():
                await message.react([types.ReactionTypeEmoji(emoji="👍")])

            # Check if buttons provided
            buttons_data = result.get("buttons")
            if buttons_data:
                # Build inline keyboard from buttons array
                keyboard_rows = []
                for row in buttons_data:
                    button_row = []
                    for btn in row:
                        button_row.append(
                            InlineKeyboardButton(
                                text=btn["text"],
                                callback_data=btn["callback_data"]
                            )
                        )
                    keyboard_rows.append(button_row)

                keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
                await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
            else:
                await message.answer(text, parse_mode="HTML")

    except httpx.TimeoutException:
        logger.error(f"[{user_id}] Request timeout")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="main_menu")]
        ])
        await message.answer(
            "⏱️ Запрос занял слишком много времени.\n\n"
            "Пожалуйста, попробуй ещё раз.",
            reply_markup=keyboard
        )
    except httpx.RequestError as e:
        logger.error(f"[{user_id}] HTTP error: {e}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        await message.answer(
            "🔌 Не могу связаться с сервером.\n\n"
            "Проверь подключение к интернету или попробуй позже.",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"[{user_id}] Unexpected error")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        await message.answer(
            "😔 Упс, произошла непредвиденная ошибка.\n\n"
            "Попробуй ещё раз или свяжись с поддержкой.",
            reply_markup=keyboard
        )


async def on_startup():
    """Run on bot startup"""
    logger.info("🚀 Starting Telegram Bot...")
    logger.info(f"Orchestrator URL: {ORCHESTRATOR_URL}")

    # Check Orchestrator availability
    try:
        response = await http_client.get(f"{ORCHESTRATOR_URL}/health", timeout=5.0)
        if response.status_code == 200:
            logger.info("✅ Orchestrator is reachable")
        else:
            logger.warning(f"⚠️ Orchestrator returned {response.status_code}")
    except Exception as e:
        logger.warning(f"⚠️ Cannot reach Orchestrator: {e}")

    # Set bot commands menu
    from aiogram.types import BotCommand
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="goals", description="🎯 Мои цели"),
        BotCommand(command="events", description="📅 Календарь событий"),
    ]
    await bot.set_my_commands(commands)
    logger.info("✅ Bot commands menu set")

    logger.info("✅ Telegram Bot started successfully")


# ==================== SETTINGS MENU HANDLERS ====================

@dp.callback_query(F.data == "settings_menu")
async def callback_settings_menu(callback: CallbackQuery):
    """Handle settings menu button"""
    await callback.answer()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Управление событиями", callback_data="settings_events")],
        [InlineKeyboardButton(text="🎯 Управление целями", callback_data="settings_goals")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "Выбери, чем хочешь управлять:",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "settings_events")
async def callback_settings_events(callback: CallbackQuery):
    """Handle event management menu"""
    await callback.answer()
    user_id = str(callback.from_user.id)

    try:
        # Fetch all events from Core Service
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/events",
            params={
                "user_id": user_id,
                "limit": 50
            }
        )

        if response.status_code == 200:
            events = response.json()

            if not events:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Добавить событие", callback_data="new_event")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_menu")]
                ])
                await callback.message.edit_text(
                    "📅 <b>Управление событиями</b>\n\n"
                    "У тебя пока нет событий.",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                return

            # Create buttons for each event
            event_buttons = []
            for event in events[:10]:  # Show first 10
                date = event.get("date", "")
                title = event.get("title", "Без названия")
                event_buttons.append([
                    InlineKeyboardButton(
                        text=f"📅 {date} - {title[:30]}",
                        callback_data=f"manage_event_{event['id']}"
                    )
                ])

            # Add action buttons
            event_buttons.append([
                InlineKeyboardButton(text="➕ Добавить событие", callback_data="new_event"),
                InlineKeyboardButton(text="🗑️📦 Удалить несколько", callback_data="bulk_delete_events")
            ])
            event_buttons.append([
                InlineKeyboardButton(text="◀️ Назад", callback_data="settings_menu")
            ])

            keyboard = InlineKeyboardMarkup(inline_keyboard=event_buttons)
            await callback.message.edit_text(
                f"📅 <b>Управление событиями</b>\n\n"
                f"Всего событий: {len(events)}\n"
                f"Выбери событие для редактирования:",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            raise Exception("Failed to fetch events")

    except Exception as e:
        logger.exception(f"Error in settings_events: {e}")
        await callback.message.edit_text("Произошла ошибка при загрузке событий.")


@dp.callback_query(F.data == "settings_goals")
async def callback_settings_goals(callback: CallbackQuery):
    """Handle goal management menu"""
    await callback.answer()
    user_id = str(callback.from_user.id)

    try:
        # Fetch all goals from Core Service
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals",
            params={"user_id": user_id}
        )

        if response.status_code == 200:
            goals = response.json()

            if not goals:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Добавить цель", callback_data="new_goal")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_menu")]
                ])
                await callback.message.edit_text(
                    "🎯 <b>Управление целями</b>\n\n"
                    "У тебя пока нет целей.",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                return

            # Create buttons for each goal
            goal_buttons = []
            for goal in goals:
                status_emoji = "✅" if goal.get("status") == "completed" else "📦" if goal.get("status") == "archived" else "🎯"
                title = goal.get("title", "Без названия")
                progress = goal.get("progress_percent", 0)

                goal_buttons.append([
                    InlineKeyboardButton(
                        text=f"{status_emoji} {title[:30]} ({progress:.0f}%)",
                        callback_data=f"manage_goal_{goal['id']}"
                    )
                ])

            # Add action buttons
            goal_buttons.append([
                InlineKeyboardButton(text="➕ Добавить цель", callback_data="new_goal"),
                InlineKeyboardButton(text="🗑️📦 Удалить несколько", callback_data="bulk_delete_goals")
            ])
            goal_buttons.append([
                InlineKeyboardButton(text="◀️ Назад", callback_data="settings_menu")
            ])

            keyboard = InlineKeyboardMarkup(inline_keyboard=goal_buttons)
            await callback.message.edit_text(
                f"🎯 <b>Управление целями</b>\n\n"
                f"Всего целей: {len(goals)}\n"
                f"Выбери цель для редактирования:",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            raise Exception("Failed to fetch goals")

    except Exception as e:
        logger.exception(f"Error in settings_goals: {e}")
        await callback.message.edit_text("Произошла ошибка при загрузке целей.")


@dp.callback_query(F.data.startswith("manage_event_"))
async def callback_manage_event(callback: CallbackQuery):
    """Handle individual event management"""
    await callback.answer()
    user_id = str(callback.from_user.id)

    try:
        # Extract event_id from callback_data (format: manage_event_{event_id})
        event_id = callback.data.split("_")[2]

        # Fetch event details from Core Service
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/events/{event_id}",
            params={"user_id": user_id}
        )

        if response.status_code == 200:
            event = response.json()

            # Format event details
            title = event.get("title", "Без названия")
            date = event.get("date", "Не указана")
            time_start = event.get("time_start", "Не указано")
            time_end = event.get("time_end", "")
            duration = event.get("duration_minutes")
            repeat_pattern = event.get("repeat_pattern")
            notes = event.get("notes", "")

            # Build display text
            text = f"📅 <b>{title}</b>\n\n"
            text += f"📆 <b>Дата:</b> {date}\n"
            text += f"⏰ <b>Время начала:</b> {time_start}\n"

            if time_end:
                text += f"⏱ <b>Время окончания:</b> {time_end}\n"
            if duration:
                text += f"⏱ <b>Длительность:</b> {duration} мин\n"

            if repeat_pattern:
                text += f"🔁 <b>Повторение:</b> {repeat_pattern}\n"

            if notes:
                text += f"\n💬 <b>Заметки:</b>\n<i>{notes}</i>\n"

            # Create edit buttons
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✏️ Название", callback_data=f"edit_event_title_{event_id}"),
                    InlineKeyboardButton(text="📅 Дата", callback_data=f"edit_event_date_{event_id}")
                ],
                [
                    InlineKeyboardButton(text="⏰ Время начала", callback_data=f"edit_event_time_start_{event_id}"),
                    InlineKeyboardButton(text="⏱ Время окончания", callback_data=f"edit_event_time_end_{event_id}")
                ],
                [
                    InlineKeyboardButton(text="⏱ Длительность", callback_data=f"edit_event_duration_{event_id}"),
                    InlineKeyboardButton(text="🔁 Повторение", callback_data=f"edit_event_repeat_{event_id}")
                ],
                [
                    InlineKeyboardButton(text="📝 Заметки", callback_data=f"edit_event_notes_{event_id}")
                ],
                [
                    InlineKeyboardButton(text="🗑️ Удалить событие", callback_data=f"delete_event_{event_id}")
                ],
                [
                    InlineKeyboardButton(text="◀️ Назад к списку", callback_data="settings_events")
                ]
            ])

            await callback.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            raise Exception("Failed to fetch event")

    except Exception as e:
        logger.exception(f"Error in manage_event: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при загрузке события.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_events")]
            ])
        )


@dp.callback_query(F.data.startswith("manage_goal_"))
async def callback_manage_goal(callback: CallbackQuery):
    """Handle individual goal management"""
    await callback.answer()
    user_id = str(callback.from_user.id)

    try:
        # Extract goal_id from callback_data (format: manage_goal_{goal_id})
        goal_id = callback.data.split("_")[2]

        # Fetch goal details from Core Service
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
            params={"user_id": user_id}
        )

        if response.status_code == 200:
            goal = response.json()

            # Format goal details
            title = goal.get("title", "Без названия")
            description = goal.get("description", "")
            status = goal.get("status", "active")
            target_date = goal.get("target_date")
            progress = goal.get("progress_percent", 0)

            status_emoji = "✅" if status == "completed" else "📦" if status == "archived" else "🎯"
            status_text = "Завершена" if status == "completed" else "Архивирована" if status == "archived" else "Активна"

            # Format deadline nicely
            if target_date:
                try:
                    from datetime import datetime
                    date_obj = datetime.fromisoformat(target_date)
                    deadline_str = date_obj.strftime("%d.%m.%Y")
                except:
                    deadline_str = target_date
            else:
                deadline_str = "Не указан"

            # Build display text
            text = f"{status_emoji} <b>{title}</b>\n\n"
            text += f"📊 <b>Статус:</b> {status_text}\n"
            text += f"📈 <b>Прогресс:</b> {progress:.0f}%\n"
            text += f"📅 <b>Дедлайн:</b> {deadline_str}\n"

            if description:
                text += f"\n💡 <b>Описание:</b>\n<i>{description}</i>\n"

            # Fetch steps for this goal
            steps_response = await http_client.get(
                f"{CORE_SERVICE_URL}/api/goals/{goal_id}/steps",
                params={"user_id": user_id}
            )

            if steps_response.status_code == 200:
                steps = steps_response.json()
                if steps:
                    text += f"\n📋 <b>Шагов:</b> {len(steps)}\n"

            # Create edit buttons
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✏️ Название", callback_data=f"edit_goal_title_{goal_id}"),
                    InlineKeyboardButton(text="📝 Описание", callback_data=f"edit_goal_description_{goal_id}")
                ],
                [
                    InlineKeyboardButton(text="📅 Дедлайн", callback_data=f"edit_goal_deadline_{goal_id}"),
                    InlineKeyboardButton(text="📊 Статус", callback_data=f"edit_goal_status_{goal_id}")
                ],
                [
                    InlineKeyboardButton(text="📋 Управление шагами", callback_data=f"manage_steps_{goal_id}")
                ],
                [
                    InlineKeyboardButton(text="🗑️ Удалить цель", callback_data=f"delete_goal_{goal_id}")
                ],
                [
                    InlineKeyboardButton(text="◀️ Назад к списку", callback_data="settings_goals")
                ]
            ])

            await callback.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            raise Exception("Failed to fetch goal")

    except Exception as e:
        logger.exception(f"Error in manage_goal: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при загрузке цели.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_goals")]
            ])
        )


# ==================== EVENT FIELD EDITING HANDLERS ====================

@dp.callback_query(F.data.startswith("edit_event_title_"))
async def callback_edit_event_title(callback: CallbackQuery):
    """Handle event title editing"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    event_id = callback.data.split("_")[3]

    try:
        # Set session state
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "event_edit_title",
                "context": {"event_id": event_id},
                "expiry_hours": 2
            }
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_event_{event_id}")]
        ])

        await callback.message.edit_text(
            "✏️ <b>Редактирование названия события</b>\n\n"
            "Введи новое название:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"Error in edit_event_title: {e}")


@dp.callback_query(F.data.startswith("edit_event_date_"))
async def callback_edit_event_date(callback: CallbackQuery):
    """Handle event date editing"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    event_id = callback.data.split("_")[3]

    try:
        # Set session state
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "event_edit_date",
                "context": {"event_id": event_id},
                "expiry_hours": 2
            }
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_event_{event_id}")]
        ])

        await callback.message.edit_text(
            "📅 <b>Редактирование даты события</b>\n\n"
            "Введи новую дату в формате YYYY-MM-DD\n"
            "(например: 2025-12-31):",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"Error in edit_event_date: {e}")


@dp.callback_query(F.data.startswith("edit_event_time_start_"))
async def callback_edit_event_time_start(callback: CallbackQuery):
    """Handle event start time editing"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    event_id = callback.data.split("_")[4]

    try:
        # Set session state
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "event_edit_time_start",
                "context": {"event_id": event_id},
                "expiry_hours": 2
            }
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_event_{event_id}")]
        ])

        await callback.message.edit_text(
            "⏰ <b>Редактирование времени начала</b>\n\n"
            "Введи новое время в формате HH:MM\n"
            "(например: 14:30):",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"Error in edit_event_time_start: {e}")


@dp.callback_query(F.data.startswith("edit_event_time_end_"))
async def callback_edit_event_time_end(callback: CallbackQuery):
    """Handle event end time editing"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    event_id = callback.data.split("_")[4]

    try:
        # Set session state
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "event_edit_time_end",
                "context": {"event_id": event_id},
                "expiry_hours": 2
            }
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_event_{event_id}")]
        ])

        await callback.message.edit_text(
            "⏱ <b>Редактирование времени окончания</b>\n\n"
            "Введи новое время в формате HH:MM\n"
            "(например: 16:00):",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"Error in edit_event_time_end: {e}")


@dp.callback_query(F.data.startswith("edit_event_duration_"))
async def callback_edit_event_duration(callback: CallbackQuery):
    """Handle event duration editing"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    event_id = callback.data.split("_")[3]

    try:
        # Set session state
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "event_edit_duration",
                "context": {"event_id": event_id},
                "expiry_hours": 2
            }
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_event_{event_id}")]
        ])

        await callback.message.edit_text(
            "⏱ <b>Редактирование длительности</b>\n\n"
            "Введи длительность в минутах\n"
            "(например: 60):",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"Error in edit_event_duration: {e}")


@dp.callback_query(F.data.startswith("edit_event_repeat_"))
async def callback_edit_event_repeat(callback: CallbackQuery):
    """Handle event repeat pattern editing"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    event_id = callback.data.split("_")[3]

    try:
        # Set session state
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "event_edit_repeat",
                "context": {"event_id": event_id},
                "expiry_hours": 2
            }
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_event_{event_id}")]
        ])

        await callback.message.edit_text(
            "🔁 <b>Редактирование повторения</b>\n\n"
            "Введи паттерн повторения:\n"
            "• daily - каждый день\n"
            "• weekly - каждую неделю\n"
            "• monthly - каждый месяц\n"
            "• или оставь пустым для отмены повторения",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"Error in edit_event_repeat: {e}")


@dp.callback_query(F.data.startswith("edit_event_notes_"))
async def callback_edit_event_notes(callback: CallbackQuery):
    """Handle event notes editing"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    event_id = callback.data.split("_")[3]

    try:
        # Set session state
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "event_edit_notes",
                "context": {"event_id": event_id},
                "expiry_hours": 2
            }
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_event_{event_id}")]
        ])

        await callback.message.edit_text(
            "📝 <b>Редактирование заметок</b>\n\n"
            "Введи новые заметки для события:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"Error in edit_event_notes: {e}")


@dp.callback_query(F.data.startswith("delete_event_"))
async def callback_delete_event(callback: CallbackQuery):
    """Handle event deletion confirmation"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    event_id = callback.data.split("_")[2]

    try:
        # Get event details for confirmation
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/events/{event_id}",
            params={"user_id": user_id}
        )

        if response.status_code == 200:
            event = response.json()
            title = event.get("title", "Без названия")

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_event_{event_id}"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_event_{event_id}")
                ]
            ])

            await callback.message.edit_text(
                f"🗑️ <b>Удаление события</b>\n\n"
                f"Ты уверен, что хочешь удалить событие:\n"
                f"<b>{title}</b>?\n\n"
                f"Это действие нельзя отменить.",
                parse_mode="HTML",
                reply_markup=keyboard
            )
    except Exception as e:
        logger.exception(f"Error in delete_event: {e}")


@dp.callback_query(F.data.startswith("confirm_delete_event_"))
async def callback_confirm_delete_event(callback: CallbackQuery):
    """Confirm and execute event deletion"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    event_id = callback.data.split("_")[3]

    try:
        # Delete event via Core Service
        response = await http_client.delete(
            f"{CORE_SERVICE_URL}/api/events/{event_id}",
            params={"user_id": user_id}
        )

        if response.status_code == 200:
            await callback.message.edit_text(
                "✅ Событие успешно удалено!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ К списку событий", callback_data="settings_events")]
                ])
            )
        else:
            raise Exception("Failed to delete event")

    except Exception as e:
        logger.exception(f"Error confirming delete event: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при удалении события.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_events")]
            ])
        )


# ==================== GOAL FIELD EDITING HANDLERS ====================

@dp.callback_query(F.data.startswith("edit_goal_title_"))
async def callback_edit_goal_title(callback: CallbackQuery):
    """Handle goal title editing"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    goal_id = callback.data.split("_")[3]

    try:
        # Set session state
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "goal_edit_title",
                "context": {"goal_id": goal_id},
                "expiry_hours": 2
            }
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_goal_{goal_id}")]
        ])

        await callback.message.edit_text(
            "✏️ <b>Редактирование названия цели</b>\n\n"
            "Введи новое название:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"Error in edit_goal_title: {e}")


@dp.callback_query(F.data.startswith("edit_goal_description_"))
async def callback_edit_goal_description(callback: CallbackQuery):
    """Handle goal description editing"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    goal_id = callback.data.split("_")[3]

    try:
        # Set session state
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "goal_edit_description",
                "context": {"goal_id": goal_id},
                "expiry_hours": 2
            }
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_goal_{goal_id}")]
        ])

        await callback.message.edit_text(
            "📝 <b>Редактирование описания цели</b>\n\n"
            "Введи новое описание:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"Error in edit_goal_description: {e}")


@dp.callback_query(F.data.startswith("edit_goal_deadline_"))
async def callback_edit_goal_deadline(callback: CallbackQuery):
    """Handle goal deadline editing"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    goal_id = callback.data.split("_")[3]

    try:
        # Set session state
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "goal_edit_deadline",
                "context": {"goal_id": goal_id},
                "expiry_hours": 2
            }
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_goal_{goal_id}")]
        ])

        await callback.message.edit_text(
            "📅 <b>Редактирование дедлайна</b>\n\n"
            "Введи новый дедлайн в формате YYYY-MM-DD\n"
            "(например: 2025-12-31):",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"Error in edit_goal_deadline: {e}")


@dp.callback_query(F.data.startswith("edit_goal_status_"))
async def callback_edit_goal_status(callback: CallbackQuery):
    """Handle goal status editing with buttons"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    goal_id = callback.data.split("_")[3]

    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎯 Активна", callback_data=f"set_goal_status_{goal_id}_active"),
                InlineKeyboardButton(text="✅ Завершена", callback_data=f"set_goal_status_{goal_id}_completed")
            ],
            [
                InlineKeyboardButton(text="📦 Архивирована", callback_data=f"set_goal_status_{goal_id}_archived")
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_goal_{goal_id}")
            ]
        ])

        await callback.message.edit_text(
            "📊 <b>Изменение статуса цели</b>\n\n"
            "Выбери новый статус:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"Error in edit_goal_status: {e}")


@dp.callback_query(F.data.startswith("set_goal_status_"))
async def callback_set_goal_status(callback: CallbackQuery):
    """Set goal status"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    parts = callback.data.split("_")
    goal_id = parts[3]
    new_status = parts[4]

    try:
        # Update goal status via Core Service
        response = await http_client.patch(
            f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
            params={"user_id": user_id},
            json={"status": new_status}
        )

        if response.status_code == 200:
            status_names = {
                "active": "Активна",
                "completed": "Завершена",
                "archived": "Архивирована"
            }

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ К цели", callback_data=f"manage_goal_{goal_id}")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])

            await callback.message.edit_text(
                f"✅ Статус цели изменен на: <b>{status_names.get(new_status, new_status)}</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            raise Exception("Failed to update goal status")

    except Exception as e:
        logger.exception(f"Error setting goal status: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при изменении статуса.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data=f"manage_goal_{goal_id}")]
            ])
        )


@dp.callback_query(F.data.startswith("delete_goal_"))
async def callback_delete_goal(callback: CallbackQuery):
    """Handle goal deletion confirmation"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    goal_id = callback.data.split("_")[2]

    try:
        # Get goal details for confirmation
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
            params={"user_id": user_id}
        )

        if response.status_code == 200:
            goal = response.json()
            title = goal.get("title", "Без названия")

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_goal_{goal_id}"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_goal_{goal_id}")
                ]
            ])

            await callback.message.edit_text(
                f"🗑️ <b>Удаление цели</b>\n\n"
                f"Ты уверен, что хочешь удалить цель:\n"
                f"<b>{title}</b>?\n\n"
                f"Все связанные шаги также будут удалены.\n"
                f"Это действие нельзя отменить.",
                parse_mode="HTML",
                reply_markup=keyboard
            )
    except Exception as e:
        logger.exception(f"Error in delete_goal: {e}")


@dp.callback_query(F.data.startswith("confirm_delete_goal_"))
async def callback_confirm_delete_goal(callback: CallbackQuery):
    """Confirm and execute goal deletion"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    goal_id = callback.data.split("_")[3]

    try:
        # Delete goal via Core Service
        response = await http_client.delete(
            f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
            params={"user_id": user_id}
        )

        if response.status_code == 200:
            await callback.message.edit_text(
                "✅ Цель и все связанные шаги успешно удалены!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ К списку целей", callback_data="settings_goals")]
                ])
            )
        else:
            raise Exception("Failed to delete goal")

    except Exception as e:
        logger.exception(f"Error confirming delete goal: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при удалении цели.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_goals")]
            ])
        )


# ==================== STEP MANAGEMENT HANDLERS ====================

@dp.callback_query(F.data.startswith("manage_steps_"))
async def callback_manage_steps(callback: CallbackQuery):
    """Handle step management for a goal"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    goal_id = callback.data.split("_")[2]

    try:
        # Fetch goal details
        goal_response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
            params={"user_id": user_id}
        )

        if goal_response.status_code != 200:
            raise Exception("Failed to fetch goal")

        goal = goal_response.json()
        goal_title = goal.get("title", "Без названия")

        # Fetch steps for this goal
        steps_response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals/{goal_id}/steps",
            params={"user_id": user_id}
        )

        if steps_response.status_code == 200:
            steps = steps_response.json()

            if not steps:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Добавить шаг", callback_data=f"add_step_{goal_id}")],
                    [InlineKeyboardButton(text="◀️ Назад к цели", callback_data=f"manage_goal_{goal_id}")]
                ])
                await callback.message.edit_text(
                    f"📋 <b>Управление шагами</b>\n\n"
                    f"Цель: <b>{goal_title}</b>\n\n"
                    f"У этой цели пока нет шагов.",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                return

            # Build step list text with status emojis
            text = f"📋 <b>Управление шагами</b>\n\n"
            text += f"Цель: <b>{goal_title}</b>\n\n"

            for i, step in enumerate(steps, 1):
                status = step.get("status", "pending")
                status_emoji = "✅" if status == "completed" else "🔄" if status == "in_progress" else "⭕"
                title = step.get("title", "Без названия")
                text += f"{i}. {status_emoji} {title[:40]}\n"

            # Create buttons for each step
            step_buttons = []
            for step in steps:
                status = step.get("status", "pending")
                status_emoji = "✅" if status == "completed" else "🔄" if status == "in_progress" else "⭕"
                title = step.get("title", "Без названия")

                step_buttons.append([
                    InlineKeyboardButton(
                        text=f"{status_emoji} {title[:25]}",
                        callback_data=f"edit_step_{step['id']}"
                    )
                ])

            # Add action buttons
            step_buttons.append([
                InlineKeyboardButton(text="➕ Добавить шаг", callback_data=f"add_step_{goal_id}")
            ])
            step_buttons.append([
                InlineKeyboardButton(text="◀️ Назад к цели", callback_data=f"manage_goal_{goal_id}")
            ])

            keyboard = InlineKeyboardMarkup(inline_keyboard=step_buttons)
            await callback.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            raise Exception("Failed to fetch steps")

    except Exception as e:
        logger.exception(f"Error in manage_steps: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при загрузке шагов.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data=f"manage_goal_{goal_id}")]
            ])
        )


@dp.callback_query(F.data.startswith("edit_step_"))
async def callback_edit_step(callback: CallbackQuery):
    """Handle individual step editing"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    step_id = callback.data.split("_")[2]

    try:
        # Fetch step details
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/steps/{step_id}",
            params={"user_id": user_id}
        )

        if response.status_code == 200:
            step = response.json()
            goal_id = step.get("goal_id")

            title = step.get("title", "Без названия")
            description = step.get("description", "")
            status = step.get("status", "pending")
            order_index = step.get("order_index", 0)

            status_emoji = "✅" if status == "completed" else "🔄" if status == "in_progress" else "⭕"
            status_text = "Выполнено" if status == "completed" else "В процессе" if status == "in_progress" else "Ожидает"

            # Build display text
            text = f"📝 <b>{title}</b>\n\n"
            text += f"📊 <b>Статус:</b> {status_emoji} {status_text}\n"
            text += f"🔢 <b>Порядок:</b> {order_index + 1}\n"

            if description:
                text += f"\n💭 <b>Описание:</b>\n<i>{description}</i>\n"

            # Create edit buttons
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✏️ Название", callback_data=f"edit_step_title_{step_id}"),
                    InlineKeyboardButton(text="📝 Описание", callback_data=f"edit_step_description_{step_id}")
                ],
                [
                    InlineKeyboardButton(text="📊 Статус", callback_data=f"edit_step_status_{step_id}")
                ],
                [
                    InlineKeyboardButton(text="⬆️ Вверх", callback_data=f"move_step_up_{step_id}"),
                    InlineKeyboardButton(text="⬇️ Вниз", callback_data=f"move_step_down_{step_id}")
                ],
                [
                    InlineKeyboardButton(text="🗑️ Удалить шаг", callback_data=f"delete_step_{step_id}")
                ],
                [
                    InlineKeyboardButton(text="◀️ К списку шагов", callback_data=f"manage_steps_{goal_id}")
                ]
            ])

            await callback.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            raise Exception("Failed to fetch step")

    except Exception as e:
        logger.exception(f"Error in edit_step: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при загрузке шага.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_goals")]
            ])
        )


# ==================== STEP FIELD EDITING HANDLERS ====================

@dp.callback_query(F.data.startswith("edit_step_title_"))
async def callback_edit_step_title(callback: CallbackQuery):
    """Handle step title editing"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    step_id = callback.data.split("_")[3]

    try:
        # Set session state
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "step_edit_title",
                "context": {"step_id": step_id},
                "expiry_hours": 2
            }
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_step_{step_id}")]
        ])

        await callback.message.edit_text(
            "✏️ <b>Редактирование названия шага</b>\n\n"
            "Введи новое название:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"Error in edit_step_title: {e}")


@dp.callback_query(F.data.startswith("edit_step_description_"))
async def callback_edit_step_description(callback: CallbackQuery):
    """Handle step description editing"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    step_id = callback.data.split("_")[3]

    try:
        # Set session state
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "step_edit_description",
                "context": {"step_id": step_id},
                "expiry_hours": 2
            }
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_step_{step_id}")]
        ])

        await callback.message.edit_text(
            "📝 <b>Редактирование описания шага</b>\n\n"
            "Введи новое описание:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"Error in edit_step_description: {e}")


@dp.callback_query(F.data.startswith("edit_step_status_"))
async def callback_edit_step_status(callback: CallbackQuery):
    """Handle step status editing with buttons"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    step_id = callback.data.split("_")[3]

    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="⭕ Ожидает", callback_data=f"set_step_status_{step_id}_pending"),
                InlineKeyboardButton(text="🔄 В процессе", callback_data=f"set_step_status_{step_id}_in_progress")
            ],
            [
                InlineKeyboardButton(text="✅ Выполнено", callback_data=f"set_step_status_{step_id}_completed")
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_step_{step_id}")
            ]
        ])

        await callback.message.edit_text(
            "📊 <b>Изменение статуса шага</b>\n\n"
            "Выбери новый статус:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"Error in edit_step_status: {e}")


@dp.callback_query(F.data.startswith("set_step_status_"))
async def callback_set_step_status(callback: CallbackQuery):
    """Set step status"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    parts = callback.data.split("_")
    step_id = parts[3]
    new_status = parts[4]

    try:
        # Update step status via Core Service
        response = await http_client.patch(
            f"{CORE_SERVICE_URL}/api/steps/{step_id}",
            params={"user_id": user_id},
            json={"status": new_status}
        )

        if response.status_code == 200:
            status_names = {
                "pending": "⭕ Ожидает",
                "in_progress": "🔄 В процессе",
                "completed": "✅ Выполнено"
            }

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ К шагу", callback_data=f"edit_step_{step_id}")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])

            await callback.message.edit_text(
                f"✅ Статус шага изменен на: <b>{status_names.get(new_status, new_status)}</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            raise Exception("Failed to update step status")

    except Exception as e:
        logger.exception(f"Error setting step status: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при изменении статуса.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data=f"edit_step_{step_id}")]
            ])
        )


@dp.callback_query(F.data.startswith("move_step_up_"))
async def callback_move_step_up(callback: CallbackQuery):
    """Move step up in order"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    step_id = callback.data.split("_")[3]

    try:
        # Get step details to find goal_id
        step_response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/steps/{step_id}",
            params={"user_id": user_id}
        )

        if step_response.status_code != 200:
            raise Exception("Failed to fetch step")

        step = step_response.json()
        goal_id = step.get("goal_id")
        current_order = step.get("order_index", 0)

        if current_order == 0:
            await callback.answer("Это уже первый шаг", show_alert=True)
            return

        # Get all steps for this goal
        steps_response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals/{goal_id}/steps",
            params={"user_id": user_id}
        )

        if steps_response.status_code == 200:
            steps = steps_response.json()

            # Find the step above
            prev_step = None
            for s in steps:
                if s.get("order_index") == current_order - 1:
                    prev_step = s
                    break

            if prev_step:
                # Swap order indices
                await http_client.patch(
                    f"{CORE_SERVICE_URL}/api/steps/{step_id}",
                    params={"user_id": user_id},
                    json={"order_index": current_order - 1}
                )

                await http_client.patch(
                    f"{CORE_SERVICE_URL}/api/steps/{prev_step['id']}",
                    params={"user_id": user_id},
                    json={"order_index": current_order}
                )

                await callback.answer("Шаг перемещен вверх ✅")
                # Refresh the step detail view
                await callback_edit_step(callback)
            else:
                await callback.answer("Не удалось найти предыдущий шаг", show_alert=True)

    except Exception as e:
        logger.exception(f"Error moving step up: {e}")
        await callback.answer("Ошибка при перемещении шага", show_alert=True)


@dp.callback_query(F.data.startswith("move_step_down_"))
async def callback_move_step_down(callback: CallbackQuery):
    """Move step down in order"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    step_id = callback.data.split("_")[3]

    try:
        # Get step details to find goal_id
        step_response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/steps/{step_id}",
            params={"user_id": user_id}
        )

        if step_response.status_code != 200:
            raise Exception("Failed to fetch step")

        step = step_response.json()
        goal_id = step.get("goal_id")
        current_order = step.get("order_index", 0)

        # Get all steps for this goal
        steps_response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals/{goal_id}/steps",
            params={"user_id": user_id}
        )

        if steps_response.status_code == 200:
            steps = steps_response.json()

            if current_order >= len(steps) - 1:
                await callback.answer("Это уже последний шаг", show_alert=True)
                return

            # Find the step below
            next_step = None
            for s in steps:
                if s.get("order_index") == current_order + 1:
                    next_step = s
                    break

            if next_step:
                # Swap order indices
                await http_client.patch(
                    f"{CORE_SERVICE_URL}/api/steps/{step_id}",
                    params={"user_id": user_id},
                    json={"order_index": current_order + 1}
                )

                await http_client.patch(
                    f"{CORE_SERVICE_URL}/api/steps/{next_step['id']}",
                    params={"user_id": user_id},
                    json={"order_index": current_order}
                )

                await callback.answer("Шаг перемещен вниз ✅")
                # Refresh the step detail view
                await callback_edit_step(callback)
            else:
                await callback.answer("Не удалось найти следующий шаг", show_alert=True)

    except Exception as e:
        logger.exception(f"Error moving step down: {e}")
        await callback.answer("Ошибка при перемещении шага", show_alert=True)


@dp.callback_query(F.data.startswith("delete_step_"))
async def callback_delete_step(callback: CallbackQuery):
    """Handle step deletion confirmation"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    step_id = callback.data.split("_")[2]

    try:
        # Get step details for confirmation
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/steps/{step_id}",
            params={"user_id": user_id}
        )

        if response.status_code == 200:
            step = response.json()
            title = step.get("title", "Без названия")
            goal_id = step.get("goal_id")

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_step_{step_id}"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_step_{step_id}")
                ]
            ])

            await callback.message.edit_text(
                f"🗑️ <b>Удаление шага</b>\n\n"
                f"Ты уверен, что хочешь удалить шаг:\n"
                f"<b>{title}</b>?\n\n"
                f"Это действие нельзя отменить.",
                parse_mode="HTML",
                reply_markup=keyboard
            )
    except Exception as e:
        logger.exception(f"Error in delete_step: {e}")


@dp.callback_query(F.data.startswith("confirm_delete_step_"))
async def callback_confirm_delete_step(callback: CallbackQuery):
    """Confirm and execute step deletion"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    step_id = callback.data.split("_")[3]

    try:
        # Get goal_id before deleting
        step_response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/steps/{step_id}",
            params={"user_id": user_id}
        )

        if step_response.status_code != 200:
            raise Exception("Failed to fetch step")

        goal_id = step_response.json().get("goal_id")

        # Delete step via Core Service
        response = await http_client.delete(
            f"{CORE_SERVICE_URL}/api/steps/{step_id}",
            params={"user_id": user_id}
        )

        if response.status_code == 200:
            await callback.message.edit_text(
                "✅ Шаг успешно удален!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ К списку шагов", callback_data=f"manage_steps_{goal_id}")]
                ])
            )
        else:
            raise Exception("Failed to delete step")

    except Exception as e:
        logger.exception(f"Error confirming delete step: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при удалении шага.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_goals")]
            ])
        )


@dp.callback_query(F.data.startswith("add_step_"))
async def callback_add_step(callback: CallbackQuery):
    """Handle adding a new step"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    goal_id = callback.data.split("_")[2]

    try:
        # Set session state
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "step_add_title",
                "context": {"goal_id": goal_id},
                "expiry_hours": 2
            }
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"manage_steps_{goal_id}")]
        ])

        await callback.message.edit_text(
            "➕ <b>Добавление нового шага</b>\n\n"
            "Введи название шага:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.exception(f"Error in add_step: {e}")


# ==================== BULK DELETE HANDLERS ====================

@dp.callback_query(F.data == "bulk_delete_events")
async def callback_bulk_delete_events(callback: CallbackQuery):
    """Handle bulk delete events - show selection interface"""
    await callback.answer()
    user_id = str(callback.from_user.id)

    try:
        # Fetch all events
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/events",
            params={"user_id": user_id, "limit": 50}
        )

        if response.status_code == 200:
            events = response.json()

            if not events:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_events")]
                ])
                await callback.message.edit_text(
                    "📅 У тебя нет событий для удаления.",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                return

            # Initialize selection state
            await http_client.put(
                f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
                json={
                    "current_state": "bulk_delete_events",
                    "context": {"selected_events": []},
                    "expiry_hours": 1
                }
            )

            # Create buttons for each event
            event_buttons = []
            for event in events[:20]:  # Limit to 20 for UI
                date = event.get("date", "")
                title = event.get("title", "Без названия")
                event_buttons.append([
                    InlineKeyboardButton(
                        text=f"⬜ {date} - {title[:25]}",
                        callback_data=f"toggle_event_{event['id']}"
                    )
                ])

            # Add action buttons
            event_buttons.append([
                InlineKeyboardButton(text="🗑️ Удалить выбранные", callback_data="confirm_bulk_delete_events")
            ])
            event_buttons.append([
                InlineKeyboardButton(text="❌ Отмена", callback_data="settings_events")
            ])

            keyboard = InlineKeyboardMarkup(inline_keyboard=event_buttons)
            await callback.message.edit_text(
                "📅 <b>Массовое удаление событий</b>\n\n"
                "Выбери события для удаления (нажми на них):",
                parse_mode="HTML",
                reply_markup=keyboard
            )

    except Exception as e:
        logger.exception(f"Error in bulk_delete_events: {e}")


@dp.callback_query(F.data.startswith("toggle_event_"))
async def callback_toggle_event(callback: CallbackQuery):
    """Toggle event selection"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    event_id = callback.data.split("_")[2]

    try:
        # Get current selection
        session_response = await http_client.get(f"{CONTEXT_SERVICE_URL}/api/session/{user_id}")

        if session_response.status_code == 200:
            session = session_response.json()
            selected_events = session.get("context", {}).get("selected_events", [])

            # Toggle selection
            if event_id in selected_events:
                selected_events.remove(event_id)
            else:
                selected_events.append(event_id)

            # Update session
            await http_client.put(
                f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
                json={
                    "current_state": "bulk_delete_events",
                    "context": {"selected_events": selected_events},
                    "expiry_hours": 1
                }
            )

            # Fetch all events again to rebuild UI
            response = await http_client.get(
                f"{CORE_SERVICE_URL}/api/events",
                params={"user_id": user_id, "limit": 50}
            )

            if response.status_code == 200:
                events = response.json()

                # Rebuild buttons with updated selection
                event_buttons = []
                for event in events[:20]:
                    date = event.get("date", "")
                    title = event.get("title", "Без названия")
                    is_selected = str(event['id']) in selected_events
                    checkbox = "☑️" if is_selected else "⬜"

                    event_buttons.append([
                        InlineKeyboardButton(
                            text=f"{checkbox} {date} - {title[:25]}",
                            callback_data=f"toggle_event_{event['id']}"
                        )
                    ])

                # Add action buttons
                event_buttons.append([
                    InlineKeyboardButton(text=f"🗑️ Удалить выбранные ({len(selected_events)})", callback_data="confirm_bulk_delete_events")
                ])
                event_buttons.append([
                    InlineKeyboardButton(text="❌ Отмена", callback_data="settings_events")
                ])

                keyboard = InlineKeyboardMarkup(inline_keyboard=event_buttons)
                await callback.message.edit_text(
                    f"📅 <b>Массовое удаление событий</b>\n\n"
                    f"Выбрано: {len(selected_events)}\n"
                    f"Нажми на события для выбора:",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )

    except Exception as e:
        logger.exception(f"Error in toggle_event: {e}")


@dp.callback_query(F.data == "confirm_bulk_delete_events")
async def callback_confirm_bulk_delete_events(callback: CallbackQuery):
    """Confirm and execute bulk delete"""
    await callback.answer()
    user_id = str(callback.from_user.id)

    try:
        # Get selected events
        session_response = await http_client.get(f"{CONTEXT_SERVICE_URL}/api/session/{user_id}")

        if session_response.status_code == 200:
            session = session_response.json()
            selected_events = session.get("context", {}).get("selected_events", [])

            if not selected_events:
                await callback.answer("Не выбрано ни одного события", show_alert=True)
                return

            # Delete each event
            deleted_count = 0
            for event_id in selected_events:
                try:
                    delete_response = await http_client.delete(
                        f"{CORE_SERVICE_URL}/api/events/{event_id}",
                        params={"user_id": user_id}
                    )
                    if delete_response.status_code == 200:
                        deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete event {event_id}: {e}")

            # Reset session
            await http_client.put(
                f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
                json={
                    "current_state": "idle",
                    "context": {},
                    "expiry_hours": 1
                }
            )

            await callback.message.edit_text(
                f"✅ Удалено событий: {deleted_count} из {len(selected_events)}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ К списку событий", callback_data="settings_events")]
                ])
            )

    except Exception as e:
        logger.exception(f"Error in confirm_bulk_delete_events: {e}")


@dp.callback_query(F.data == "bulk_delete_goals")
async def callback_bulk_delete_goals(callback: CallbackQuery):
    """Handle bulk delete goals - show selection interface"""
    await callback.answer()
    user_id = str(callback.from_user.id)

    try:
        # Fetch all goals
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals",
            params={"user_id": user_id}
        )

        if response.status_code == 200:
            goals = response.json()

            if not goals:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_goals")]
                ])
                await callback.message.edit_text(
                    "🎯 У тебя нет целей для удаления.",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                return

            # Initialize selection state
            await http_client.put(
                f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
                json={
                    "current_state": "bulk_delete_goals",
                    "context": {"selected_goals": []},
                    "expiry_hours": 1
                }
            )

            # Create buttons for each goal
            goal_buttons = []
            for goal in goals:
                status_emoji = "✅" if goal.get("status") == "completed" else "📦" if goal.get("status") == "archived" else "🎯"
                title = goal.get("title", "Без названия")
                goal_buttons.append([
                    InlineKeyboardButton(
                        text=f"⬜ {status_emoji} {title[:30]}",
                        callback_data=f"toggle_goal_{goal['id']}"
                    )
                ])

            # Add action buttons
            goal_buttons.append([
                InlineKeyboardButton(text="🗑️ Удалить выбранные", callback_data="confirm_bulk_delete_goals")
            ])
            goal_buttons.append([
                InlineKeyboardButton(text="❌ Отмена", callback_data="settings_goals")
            ])

            keyboard = InlineKeyboardMarkup(inline_keyboard=goal_buttons)
            await callback.message.edit_text(
                "🎯 <b>Массовое удаление целей</b>\n\n"
                "Выбери цели для удаления (нажми на них):\n"
                "⚠️ Все шаги также будут удалены!",
                parse_mode="HTML",
                reply_markup=keyboard
            )

    except Exception as e:
        logger.exception(f"Error in bulk_delete_goals: {e}")


@dp.callback_query(F.data.startswith("toggle_goal_"))
async def callback_toggle_goal(callback: CallbackQuery):
    """Toggle goal selection"""
    await callback.answer()
    user_id = str(callback.from_user.id)
    goal_id = callback.data.split("_")[2]

    try:
        # Get current selection
        session_response = await http_client.get(f"{CONTEXT_SERVICE_URL}/api/session/{user_id}")

        if session_response.status_code == 200:
            session = session_response.json()
            selected_goals = session.get("context", {}).get("selected_goals", [])

            # Toggle selection
            if goal_id in selected_goals:
                selected_goals.remove(goal_id)
            else:
                selected_goals.append(goal_id)

            # Update session
            await http_client.put(
                f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
                json={
                    "current_state": "bulk_delete_goals",
                    "context": {"selected_goals": selected_goals},
                    "expiry_hours": 1
                }
            )

            # Fetch all goals again to rebuild UI
            response = await http_client.get(
                f"{CORE_SERVICE_URL}/api/goals",
                params={"user_id": user_id}
            )

            if response.status_code == 200:
                goals = response.json()

                # Rebuild buttons with updated selection
                goal_buttons = []
                for goal in goals:
                    status_emoji = "✅" if goal.get("status") == "completed" else "📦" if goal.get("status") == "archived" else "🎯"
                    title = goal.get("title", "Без названия")
                    is_selected = str(goal['id']) in selected_goals
                    checkbox = "☑️" if is_selected else "⬜"

                    goal_buttons.append([
                        InlineKeyboardButton(
                            text=f"{checkbox} {status_emoji} {title[:30]}",
                            callback_data=f"toggle_goal_{goal['id']}"
                        )
                    ])

                # Add action buttons
                goal_buttons.append([
                    InlineKeyboardButton(text=f"🗑️ Удалить выбранные ({len(selected_goals)})", callback_data="confirm_bulk_delete_goals")
                ])
                goal_buttons.append([
                    InlineKeyboardButton(text="❌ Отмена", callback_data="settings_goals")
                ])

                keyboard = InlineKeyboardMarkup(inline_keyboard=goal_buttons)
                await callback.message.edit_text(
                    f"🎯 <b>Массовое удаление целей</b>\n\n"
                    f"Выбрано: {len(selected_goals)}\n"
                    f"Нажми на цели для выбора:\n"
                    f"⚠️ Все шаги также будут удалены!",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )

    except Exception as e:
        logger.exception(f"Error in toggle_goal: {e}")


@dp.callback_query(F.data == "confirm_bulk_delete_goals")
async def callback_confirm_bulk_delete_goals(callback: CallbackQuery):
    """Confirm and execute bulk delete goals"""
    await callback.answer()
    user_id = str(callback.from_user.id)

    try:
        # Get selected goals
        session_response = await http_client.get(f"{CONTEXT_SERVICE_URL}/api/session/{user_id}")

        if session_response.status_code == 200:
            session = session_response.json()
            selected_goals = session.get("context", {}).get("selected_goals", [])

            if not selected_goals:
                await callback.answer("Не выбрано ни одной цели", show_alert=True)
                return

            # Delete each goal
            deleted_count = 0
            for goal_id in selected_goals:
                try:
                    delete_response = await http_client.delete(
                        f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
                        params={"user_id": user_id}
                    )
                    if delete_response.status_code == 200:
                        deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete goal {goal_id}: {e}")

            # Reset session
            await http_client.put(
                f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
                json={
                    "current_state": "idle",
                    "context": {},
                    "expiry_hours": 1
                }
            )

            await callback.message.edit_text(
                f"✅ Удалено целей: {deleted_count} из {len(selected_goals)}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ К списку целей", callback_data="settings_goals")]
                ])
            )

    except Exception as e:
        logger.exception(f"Error in confirm_bulk_delete_goals: {e}")


# ==================== SMART GOAL EDITING HANDLERS ====================

@dp.callback_query(F.data.startswith("edit_goal_"))
async def callback_edit_goal(callback: CallbackQuery):
    """Handle edit goal button from SMART analysis"""
    user_id = str(callback.from_user.id)
    await callback.answer()

    try:
        # Extract goal_id from callback_data (format: edit_goal_{goal_id})
        goal_id = callback.data.split("_")[2]

        logger.info(f"[{user_id}] Editing goal {goal_id}")

        # Set session state to goal editing
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "goal_editing",
                "context": {"goal_id": goal_id},
                "expiry_hours": 4
            }
        )

        # Get current goal details
        response = await http_client.get(
            f"{CORE_SERVICE_URL}/api/goals/{goal_id}?user_id={user_id}"
        )

        if response.status_code == 200:
            goal = response.json()
            text = (
                f"✏️ <b>Редактирование цели</b>\n\n"
                f"Текущая цель: <b>{goal['title']}</b>\n\n"
                f"Напиши новую формулировку цели с учетом рекомендаций SMART:\n"
                f"• Сделай цель более конкретной\n"
                f"• Добавь измеримые критерии\n"
                f"• Убедись что она достижима\n"
                f"• Проверь релевантность\n"
                f"• Укажи временные рамки"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_goal_edit")]
            ])

            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        else:
            await callback.message.edit_text("Не удалось загрузить цель. Попробуй еще раз.")

    except Exception as e:
        logger.exception(f"Error editing goal: {e}")
        await callback.message.edit_text("Произошла ошибка при редактировании цели.")


@dp.callback_query(F.data == "continue_goal")
async def callback_continue_goal(callback: CallbackQuery):
    """Handle continue button - skip SMART improvements"""
    user_id = str(callback.from_user.id)
    await callback.answer("Отлично! Продолжаем с текущей целью.")

    try:
        # Just remove buttons and keep the text as is
        text = callback.message.text or callback.message.caption
        await callback.message.edit_text(text, parse_mode="HTML")

    except Exception as e:
        logger.exception(f"Error continuing goal: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@dp.callback_query(F.data == "cancel_goal_edit")
async def callback_cancel_goal_edit(callback: CallbackQuery):
    """Cancel goal editing"""
    user_id = str(callback.from_user.id)
    await callback.answer("Редактирование отменено")

    try:
        # Reset session state to idle
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "idle",
                "context": {},
                "expiry_hours": 1
            }
        )

        # Return to main menu
        await cmd_start(callback.message)

    except Exception as e:
        logger.exception(f"Error canceling goal edit: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@dp.callback_query(F.data == "continue_to_deadline")
async def callback_continue_to_deadline(callback: CallbackQuery):
    """Continue with current goal despite SMART score"""
    user_id = str(callback.from_user.id)
    await callback.answer("Продолжаем!")

    try:
        # Get session context to retrieve goal info
        session_response = await http_client.get(f"{CONTEXT_SERVICE_URL}/api/session/{user_id}")
        if session_response.status_code == 200:
            session = session_response.json()
            context = session.get("context", {})
            goal_id = context.get("goal_id")

            # Transition to deadline request state
            await http_client.put(
                f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
                json={
                    "current_state": "goal_deadline_request",
                    "context": context,
                    "expiry_hours": 4
                }
            )

            text = (
                f"📅 <b>Когда ты хочешь достичь этой цели?</b>\n\n"
                f"Укажи дедлайн, например:\n"
                f"• 'через 2 недели'\n"
                f"• '15 декабря'\n"
                f"• '2025-12-15'"
            )

            await callback.message.edit_text(text, parse_mode="HTML")
        else:
            await callback.message.edit_text("Произошла ошибка. Попробуй еще раз.")

    except Exception as e:
        logger.exception(f"Error continuing to deadline: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


# ==================== CALENDAR HANDLERS ====================

@dp.callback_query(F.data.startswith("cal_prev_"))
async def callback_calendar_prev(callback: CallbackQuery):
    """Handle calendar previous month"""
    await callback.answer()

    from app.renderer import create_calendar_keyboard

    # Parse year and month
    parts = callback.data.split("_")
    year = int(parts[2])
    month = int(parts[3])

    # Go to previous month
    if month == 1:
        month = 12
        year -= 1
    else:
        month -= 1

    calendar_keyboard = create_calendar_keyboard(year, month)

    await callback.message.edit_text(
        "📅 <b>Создание события</b>\n\nВыбери дату события:",
        reply_markup=calendar_keyboard,
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("cal_next_"))
async def callback_calendar_next(callback: CallbackQuery):
    """Handle calendar next month"""
    await callback.answer()

    from app.renderer import create_calendar_keyboard

    # Parse year and month
    parts = callback.data.split("_")
    year = int(parts[2])
    month = int(parts[3])

    # Go to next month
    if month == 12:
        month = 1
        year += 1
    else:
        month += 1

    calendar_keyboard = create_calendar_keyboard(year, month)

    await callback.message.edit_text(
        "📅 <b>Создание события</b>\n\nВыбери дату события:",
        reply_markup=calendar_keyboard,
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("cal_select_"))
async def callback_calendar_select(callback: CallbackQuery):
    """Handle calendar date selection"""
    await callback.answer()

    # Parse selected date
    parts = callback.data.split("_")
    year = parts[2]
    month = parts[3]
    day = parts[4]
    selected_date = f"{year}-{month}-{day}"

    user_id = str(callback.from_user.id)

    # Store selected date in session context
    try:
        await http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": "event_clarification",
                "context": {"selected_date": selected_date},
                "expiry_hours": 2
            }
        )
    except Exception as e:
        logger.error(f"Error storing selected date: {e}")

    # Format date nicely
    from datetime import datetime
    date_obj = datetime.fromisoformat(selected_date)
    weekday = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date_obj.weekday()]
    date_formatted = f"{weekday}, {date_obj.strftime('%d.%m.%Y')}"

    await callback.message.edit_text(
        f"📅 <b>Создание события</b>\n\n"
        f"Дата: {date_formatted}\n\n"
        f"Теперь введи детали события:\n"
        f"• Название\n"
        f"• Время (например: 15:00)\n"
        f"• Длительность (например: 1 час)\n\n"
        f"Например: <i>Встреча с клиентом в 15:00, 2 часа</i>",
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "cal_cancel")
async def callback_calendar_cancel(callback: CallbackQuery):
    """Handle calendar cancel"""
    await callback.answer("Отменено")

    await callback.message.edit_text(
        "❌ Создание события отменено.\n\n"
        "Используй /start для возврата в главное меню."
    )


@dp.callback_query(F.data == "cal_ignore")
async def callback_calendar_ignore(callback: CallbackQuery):
    """Ignore non-clickable calendar cells"""
    await callback.answer()


# ==================== NOTIFICATION SETTINGS ====================

async def show_settings(chat_id: int, user_id: str, bot_instance):
    """Show notification settings to user"""
    try:
        # Get or create user settings
        response = await http_client.get(f"{CORE_SERVICE_URL}/api/users/{user_id}")

        if response.status_code == 404:
            # User doesn't exist yet, create with defaults
            await http_client.post(
                f"{CORE_SERVICE_URL}/api/users",
                json={
                    "user_id": user_id,
                    "chat_id": str(chat_id),
                    "timezone": "Europe/Moscow",
                    "notification_enabled": True,
                    "event_reminders_enabled": True,
                    "goal_deadline_warnings_enabled": True,
                    "step_reminders_enabled": True,
                    "motivational_messages_enabled": True
                }
            )
            # Fetch again
            response = await http_client.get(f"{CORE_SERVICE_URL}/api/users/{user_id}")

        user_settings = response.json()

        # Build settings message
        global_enabled = user_settings.get("notification_enabled", True)
        event_enabled = user_settings.get("event_reminders_enabled", True)
        goal_enabled = user_settings.get("goal_deadline_warnings_enabled", True)
        step_enabled = user_settings.get("step_reminders_enabled", True)
        motivational_enabled = user_settings.get("motivational_messages_enabled", True)

        # Emojis for enabled/disabled
        def status_emoji(enabled):
            return "✅" if enabled else "❌"

        message = f"""⚙️ <b>Настройки уведомлений</b>

{status_emoji(global_enabled)} Все уведомления: {"включены" if global_enabled else "отключены"}

<b>Типы уведомлений:</b>
{status_emoji(event_enabled)} Напоминания о событиях
{status_emoji(goal_enabled)} Предупреждения о дедлайнах
{status_emoji(step_enabled)} Напоминания о незавершенных шагах
{status_emoji(motivational_enabled)} Мотивационные сообщения"""

        # Build keyboard
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'🔕' if global_enabled else '🔔'} Все уведомления",
                    callback_data="settings_toggle_global"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{'✅' if event_enabled else '❌'} События",
                    callback_data="settings_toggle_event_reminders"
                ),
                InlineKeyboardButton(
                    text=f"{'✅' if goal_enabled else '❌'} Дедлайны",
                    callback_data="settings_toggle_goal_deadlines"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{'✅' if step_enabled else '❌'} Шаги",
                    callback_data="settings_toggle_step_reminders"
                ),
                InlineKeyboardButton(
                    text=f"{'✅' if motivational_enabled else '❌'} Мотивация",
                    callback_data="settings_toggle_motivational"
                )
            ],
            [
                InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
            ]
        ])

        await bot_instance.send_message(
            chat_id,
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error showing settings: {e}")
        await bot_instance.send_message(
            chat_id,
            "❌ Упс, произошла ошибка при загрузке настроек.",
            parse_mode="HTML"
        )


@dp.callback_query(F.data.startswith("settings_toggle_"))
async def callback_settings_toggle(callback: CallbackQuery):
    """Handle settings toggle buttons"""
    await callback.answer()

    user_id = str(callback.from_user.id)
    chat_id = callback.message.chat.id

    # Determine which setting to toggle
    setting_type = callback.data.replace("settings_toggle_", "")

    setting_map = {
        "global": "notification_enabled",
        "event_reminders": "event_reminders_enabled",
        "goal_deadlines": "goal_deadline_warnings_enabled",
        "step_reminders": "step_reminders_enabled",
        "motivational": "motivational_messages_enabled"
    }

    field_name = setting_map.get(setting_type)

    if not field_name:
        await callback.answer("❌ Неизвестная настройка")
        return

    try:
        # Get current settings
        response = await http_client.get(f"{CORE_SERVICE_URL}/api/users/{user_id}")
        user_settings = response.json()

        # Toggle the setting
        current_value = user_settings.get(field_name, True)
        new_value = not current_value

        # Update settings
        await http_client.patch(
            f"{CORE_SERVICE_URL}/api/users/{user_id}",
            json={field_name: new_value}
        )

        # Refresh settings display
        await callback.message.delete()
        await show_settings(chat_id, user_id, callback.bot)

    except Exception as e:
        logger.error(f"Error toggling setting: {e}")
        await callback.answer("❌ Ошибка при обновлении настроек")


async def on_shutdown():
    """Run on bot shutdown"""
    logger.info("Shutting down Telegram Bot...")
    await http_client.aclose()
    await bot.session.close()


async def main():
    """Main entry point"""
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

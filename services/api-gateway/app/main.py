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

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command"""
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
        "👋 Привет! Я твой персональный коуч.\n\n"
        "Я помогу тебе:\n"
        "• 🎯 Достигать целей с пошаговым планом\n"
        "• 📅 Управлять календарем и событиями\n"
        "• 💪 Оставаться мотивированным\n\n"
        "Используй кнопки ниже или просто напиши мне:",
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
    await callback.message.answer(
        "📅 Создам событие! Скажи мне:\n\n"
        "Например:\n"
        "• Созвон с командой завтра в 15:00\n"
        "• Встреча с клиентом 5 октября\n"
        "• Тренировка каждый понедельник в 18:00"
    )


@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """Handle main_menu button - return to start"""
    await callback.answer()

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
        "🏠 <b>Главное меню</b>\n\n"
        "Выбери действие или просто напиши мне что-нибудь:",
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


@dp.callback_query(F.data.startswith("toggle_step_"))
async def callback_toggle_step(callback: CallbackQuery):
    """Handle toggle_step_{step_id}_{goal_id} button - mark step as completed/pending"""
    await callback.answer()

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
                await callback.answer("Не удалось обновить шаг", show_alert=True)
        else:
            await callback.answer("Не удалось загрузить цель", show_alert=True)

    except Exception as e:
        logger.exception(f"Error toggling step {step_id}: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


@dp.message()
async def handle_message(message: types.Message):
    """Handle all text messages"""
    user_id = str(message.from_user.id)
    user_msg = message.text

    if not user_msg:
        return

    logger.info(f"[{user_id}] Received: {user_msg[:50]}...")

    # Send "typing" action for better UX
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
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

        if response_type == "table":
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

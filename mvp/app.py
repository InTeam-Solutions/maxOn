import os
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties

from mvp.llm.nlp import LLMBackend
from mvp.core.router import handle_intent
from mvp.core.db import init_db
from mvp.core import events
from mvp.renderer import render_events, get_items_from_set

# --- Логирование ---
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не найден в .env")

# --- Инициализация компонентов ---
init_db()
events.ensure_schema()
llm = LLMBackend()

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# --- Handlers ---

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Я твой ассистент. Напиши мне сообщение — и я помогу 😉")


@dp.message()
async def handle_message(message: types.Message):
    user_msg = message.text
    user_id = str(message.from_user.id)  # 🔑 используем Telegram user_id

    try:
        # Шаг 1: GPT → интент
        parsed = llm.parse_message(user_msg)
        logger.debug(f"[LLM.parse_message] input={user_msg!r}, output={parsed}")

        # small_talk обрабатывается сразу
        if parsed.get("intent") == "small_talk":
            text = parsed.get("text", "").strip()
            await message.answer(text)
            return

        # Шаг 2: Core → выполнение (с user_id)
        core_result = handle_intent(parsed, user_id=user_id)
        logger.debug(f"[Core.handle_intent] input={parsed}, output={core_result}")

        # Шаг 3: GPT → итоговая стратегия ответа (JSON)
        summary = llm.summarize_response(core_result)
        logger.debug(f"[LLM.summarize_response] input={core_result}, output={summary}")

        intent = summary.get("intent")
        text = summary.get("text", "").strip()

        if text:
            await message.answer(text)

        # Шаг 4: по запросу — рендер таблицы
        if intent == "render_table":
            set_id = summary.get("set_id")
            items = summary.get("items")
            if items is None and set_id:
                items = get_items_from_set(set_id, user_id=user_id)

            if not items:
                await message.answer("События не найдены.")
            else:
                lines = []
                for i, e in enumerate(items, 1):
                    date = e.get("date") or ""
                    time = e.get("time") or ""
                    tt = f"{date} {time}".strip()
                    lines.append(f"{i}. <b>{e.get('title','(без названия)')}</b> — {tt}")
                await message.answer("\n".join(lines), parse_mode="HTML")

    except Exception:
        logger.exception("Ошибка при обработке сообщения")
        await message.answer("Упс, произошла ошибка. Попробуй ещё раз.")


def main():
    import asyncio
    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    main()

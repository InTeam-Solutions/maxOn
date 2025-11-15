"""
Telegram Service
Handles sending messages via Telegram Bot API
"""
import logging
import os
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

logger = logging.getLogger(__name__)

# Initialize bot instance
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)


async def send_telegram_message(chat_id: str, text: str) -> bool:
    """
    Send a message via Telegram

    Args:
        chat_id: Telegram chat ID (for private chats, this is same as user_id)
        text: Message text (HTML formatted)

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML"
        )
        logger.debug(f"✅ Sent message to chat {chat_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send message to chat {chat_id}: {e}")
        return False

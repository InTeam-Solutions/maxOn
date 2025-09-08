import os
from datetime import datetime
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Привет! Я Initio бот.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BACKEND_URL}/chat", json={"message": text})
        resp.raise_for_status()
        reply = resp.json().get("reply", "")
    await update.message.reply_text(reply)

async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text(
            "Использование: /addevent <YYYY-MM-DDTHH:MM> <описание>"
        )
        return
    time_str = context.args[0]
    description = " ".join(context.args[1:])
    try:
        datetime.fromisoformat(time_str)
    except ValueError:
        await update.message.reply_text("Неверный формат времени")
        return
    payload = {"time": time_str, "description": description}
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BACKEND_URL}/events", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            await update.message.reply_text(
                f"Событие {data['id']} добавлено на {data['time']}"
            )
        else:
            await update.message.reply_text("Не удалось создать событие")

def main() -> None:
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN is not set")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addevent", add_event))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()

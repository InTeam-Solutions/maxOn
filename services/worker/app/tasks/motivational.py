"""
Motivational Messages Task
Sends daily motivational messages to users with active goals
"""
import logging
import random
from datetime import datetime

from shared.database import get_db
from core_models.goal import Goal
from core_models.user import User
from app.services.telegram_service import send_telegram_message

logger = logging.getLogger(__name__)


# Predefined motivational messages
MOTIVATIONAL_MESSAGES = [
    "Доброе утро! 🌅 Каждый новый день — это возможность стать на шаг ближе к своей цели. Удачи!",
    "Привет! ☀️ Помни: маленькие шаги каждый день приводят к большим результатам. Продолжай двигаться вперед!",
    "Доброе утро! 💪 Успех — это сумма небольших усилий, повторяемых изо дня в день. Ты на правильном пути!",
    "Привет! 🎯 Не забывай: самая длинная дорога начинается с первого шага. А ты уже сделал его!",
    "Доброе утро! 🌟 Вера в себя и последовательность — вот твои главные союзники на пути к цели!",
    "Привет! ⚡ Сегодня отличный день, чтобы сделать еще один шаг к своей мечте!",
    "Доброе утро! 🔥 Трудности — это всего лишь возможности в рабочей одежде. Продолжай работать!",
    "Привет! 🚀 Единственный способ достичь невозможного — это поверить, что оно возможно!",
]


async def send_daily_motivation():
    """
    Send daily motivational messages to users
    Runs daily at 8:00 AM
    """
    try:
        logger.info("💬 Sending daily motivational messages...")

        db = get_db()
        with db.session_ctx() as session:
            # Get all users with motivational messages enabled
            users = session.query(User).filter(
                User.notification_enabled == True,
                User.motivational_messages_enabled == True
            ).all()

            messages_sent = 0

            for user in users:
                # Check if user has any active goals
                active_goals_count = session.query(Goal).filter(
                    Goal.user_id == user.user_id,
                    Goal.status == "active"
                ).count()

                if active_goals_count == 0:
                    logger.debug(f"User {user.user_id} has no active goals, skipping")
                    continue

                # Get user's active goals for personalized message
                active_goals = session.query(Goal).filter(
                    Goal.user_id == user.user_id,
                    Goal.status == "active"
                ).limit(3).all()

                # Format motivational message
                message = format_motivational_message(active_goals)

                # Send message
                success = await send_telegram_message(
                    chat_id=user.chat_id,
                    text=message
                )

                if success:
                    messages_sent += 1
                    logger.info(f"✅ Sent motivational message to user {user.user_id}")
                else:
                    logger.error(f"❌ Failed to send motivational message to user {user.user_id}")

        logger.info(f"📊 Motivational messages complete. Sent: {messages_sent}")

    except Exception as e:
        logger.exception(f"❌ Error sending motivational messages: {e}")


def format_motivational_message(goals: list) -> str:
    """Format daily motivational message with user's goals"""
    # Random motivational greeting
    greeting = random.choice(MOTIVATIONAL_MESSAGES)

    message = greeting

    if goals:
        message += "\n\n<b>Твои цели на сегодня:</b>\n"

        for goal in goals:
            progress = goal.progress_percent or 0
            message += f"\n🎯 {goal.title} — {progress:.0f}%"

    message += "\n\n✨ <i>Вперед к новым достижениям!</i>"

    return message

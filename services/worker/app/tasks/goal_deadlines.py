"""
Goal Deadline Warnings Task
Checks for goals approaching their deadline and sends warnings
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import and_

from shared.database import get_db
from core_models.goal import Goal
from core_models.user import User
from app.services.telegram_service import send_telegram_message

logger = logging.getLogger(__name__)


async def check_and_send_warnings():
    """
    Check for goals with approaching deadlines and send warnings
    Runs daily at 9:00 AM
    """
    try:
        logger.info("⏰ Checking for goal deadline warnings...")

        db = get_db()
        with db.session_ctx() as session:
            # Get current date
            today = datetime.now().date()

            # Warning thresholds: 7 days, 3 days, 1 day, today
            warning_dates = [
                today + timedelta(days=7),
                today + timedelta(days=3),
                today + timedelta(days=1),
                today
            ]

            # Query active goals with deadlines approaching
            goals = session.query(Goal).filter(
                and_(
                    Goal.status == "active",
                    Goal.target_date.isnot(None),
                    Goal.target_date.in_(warning_dates)
                )
            ).all()

            warnings_sent = 0

            for goal in goals:
                # Get user settings
                user = session.query(User).filter(User.user_id == goal.user_id).first()

                if not user:
                    logger.warning(f"User {goal.user_id} not found for goal {goal.id}")
                    continue

                if not user.notification_enabled or not user.goal_deadline_warnings_enabled:
                    logger.debug(f"Goal deadline warnings disabled for user {goal.user_id}")
                    continue

                # Calculate days remaining
                days_remaining = (goal.target_date - today).days

                # Format warning message
                message = format_deadline_warning(goal, days_remaining)

                # Send warning
                success = await send_telegram_message(
                    chat_id=user.chat_id,
                    text=message
                )

                if success:
                    warnings_sent += 1
                    logger.info(f"✅ Sent deadline warning for goal {goal.id} to user {goal.user_id}")
                else:
                    logger.error(f"❌ Failed to send deadline warning for goal {goal.id}")

        logger.info(f"📊 Goal deadline check complete. Sent: {warnings_sent}")

    except Exception as e:
        logger.exception(f"❌ Error checking goal deadlines: {e}")


def format_deadline_warning(goal: Goal, days_remaining: int) -> str:
    """Format goal deadline warning message"""
    # Determine urgency emoji and message
    if days_remaining == 0:
        urgency_emoji = "🚨"
        time_text = "Дедлайн <b>сегодня</b>!"
    elif days_remaining == 1:
        urgency_emoji = "⚠️"
        time_text = "Дедлайн <b>завтра</b>!"
    elif days_remaining <= 3:
        urgency_emoji = "⏰"
        time_text = f"До дедлайна осталось <b>{days_remaining} дня</b>"
    else:
        urgency_emoji = "📅"
        time_text = f"До дедлайна осталось <b>{days_remaining} дней</b>"

    # Progress bar
    progress = goal.progress_percent or 0
    filled = int(progress / 10)
    progress_bar = "█" * filled + "░" * (10 - filled)

    # Build message
    message = f"""{urgency_emoji} <b>Напоминание о цели</b>

🎯 <b>{goal.title}</b>

{time_text}
📆 Дедлайн: {goal.target_date.strftime('%d.%m.%Y')}

{progress_bar} <b>{progress:.0f}%</b> завершено"""

    if goal.description:
        message += f"\n\n💡 {goal.description[:100]}"

    # Add motivation based on progress
    if progress < 30:
        message += "\n\n💪 Самое время начать активно работать над целью!"
    elif progress < 70:
        message += "\n\n👍 Хорошее начало! Продолжай в том же духе!"
    else:
        message += "\n\n🔥 Отличная работа! Ты почти у цели!"

    return message

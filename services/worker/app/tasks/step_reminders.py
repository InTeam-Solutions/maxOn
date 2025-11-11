"""
Unfinished Step Reminders Task
Checks for overdue or in-progress steps and sends reminders
"""
import logging
from datetime import datetime
from sqlalchemy import and_, or_

from shared.database import get_db
from core_models.goal import Step, Goal
from core_models.user import User
from app.services.telegram_service import send_telegram_message

logger = logging.getLogger(__name__)


async def check_and_send_reminders():
    """
    Check for unfinished steps and send reminders
    Runs daily at 8:00 PM
    """
    try:
        logger.info("📋 Checking for unfinished step reminders...")

        db = get_db()
        with db.session_ctx() as session:
            # Get current date
            today = datetime.now().date()

            # Query steps that are:
            # 1. In progress or pending
            # 2. Have a planned date in the past or today
            steps = session.query(Step).join(Goal).filter(
                and_(
                    Step.status.in_(["in_progress", "pending"]),
                    Step.planned_date.isnot(None),
                    Step.planned_date <= today,
                    Goal.status == "active"
                )
            ).all()

            # Group steps by user
            user_steps = {}
            for step in steps:
                # Get goal for this step
                goal = session.query(Goal).filter(Goal.id == step.goal_id).first()
                if not goal:
                    continue

                user_id = goal.user_id
                if user_id not in user_steps:
                    user_steps[user_id] = []

                user_steps[user_id].append((step, goal))

            reminders_sent = 0

            # Send reminders to each user
            for user_id, step_goal_pairs in user_steps.items():
                # Get user settings
                user = session.query(User).filter(User.user_id == user_id).first()

                if not user:
                    logger.warning(f"User {user_id} not found")
                    continue

                if not user.notification_enabled or not user.step_reminders_enabled:
                    logger.debug(f"Step reminders disabled for user {user_id}")
                    continue

                # Format reminder message
                message = format_step_reminder(step_goal_pairs, today)

                # Send reminder
                success = await send_telegram_message(
                    chat_id=user.chat_id,
                    text=message
                )

                if success:
                    reminders_sent += 1
                    logger.info(f"✅ Sent step reminder to user {user_id} ({len(step_goal_pairs)} steps)")
                else:
                    logger.error(f"❌ Failed to send step reminder to user {user_id}")

        logger.info(f"📊 Step reminders check complete. Sent: {reminders_sent}")

    except Exception as e:
        logger.exception(f"❌ Error checking step reminders: {e}")


def format_step_reminder(step_goal_pairs: list, today) -> str:
    """Format unfinished steps reminder message"""
    count = len(step_goal_pairs)

    if count == 1:
        message = "📋 <b>Напоминание о незавершенном шаге</b>\n\n"
    else:
        message = f"📋 <b>У тебя {count} незавершенных шагов</b>\n\n"

    for step, goal in step_goal_pairs[:5]:  # Show max 5 steps
        # Status emoji
        if step.status == "in_progress":
            status_emoji = "🔄"
        else:
            status_emoji = "⭕"

        # Calculate days overdue
        days_overdue = (today - step.planned_date).days

        if days_overdue == 0:
            time_text = "запланирован на сегодня"
        elif days_overdue == 1:
            time_text = "<b>просрочен на 1 день</b>"
        else:
            time_text = f"<b>просрочен на {days_overdue} дней</b>"

        message += f"{status_emoji} <i>{step.title}</i>\n"
        message += f"   🎯 Цель: {goal.title}\n"
        message += f"   📅 {time_text}\n\n"

    if count > 5:
        message += f"<i>...и еще {count - 5} шагов</i>\n\n"

    message += "💪 Давай завершим их сегодня!"

    return message

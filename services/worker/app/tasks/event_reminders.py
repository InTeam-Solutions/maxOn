"""
Event Reminders Task
Checks for upcoming events and sends reminders
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from shared.database import get_db
from core_models.event import Event
from core_models.user import User
from app.services.telegram_service import send_telegram_message

logger = logging.getLogger(__name__)


async def check_and_send_reminders():
    """
    Check for events that need reminders and send them
    Runs every minute
    """
    try:
        logger.info("🔔 Checking for event reminders...")

        db = get_db()
        with db.session_ctx() as session:
            # Get current time
            now = datetime.now()
            current_date = now.date()
            current_time = now.time()

            # Calculate time window (current minute ± 1 minute for tolerance)
            start_window = now - timedelta(minutes=1)
            end_window = now + timedelta(minutes=60)  # Check up to 60 minutes ahead

            # Query events that:
            # 1. Have reminders enabled
            # 2. Event datetime - reminder_minutes_before falls within our window
            events = session.query(Event).filter(
                Event.reminder_enabled == True,
                Event.date >= current_date,
                Event.time.isnot(None)
            ).all()

            reminders_sent = 0

            for event in events:
                # Calculate when reminder should be sent
                event_datetime = datetime.combine(event.date, event.time)
                reminder_datetime = event_datetime - timedelta(minutes=event.reminder_minutes_before)

                # Check if we should send reminder now
                if start_window <= reminder_datetime <= end_window:
                    # Get user settings
                    user = session.query(User).filter(User.user_id == event.user_id).first()

                    # Check if user has notifications enabled
                    if not user:
                        logger.warning(f"User {event.user_id} not found for event {event.id}")
                        continue

                    if not user.notification_enabled or not user.event_reminders_enabled:
                        logger.debug(f"Notifications disabled for user {event.user_id}")
                        continue

                    # Format reminder message
                    message = format_event_reminder(event)

                    # Send reminder
                    success = await send_telegram_message(
                        chat_id=user.chat_id,
                        text=message
                    )

                    if success:
                        reminders_sent += 1
                        logger.info(f"✅ Sent reminder for event {event.id} to user {event.user_id}")
                    else:
                        logger.error(f"❌ Failed to send reminder for event {event.id}")

        logger.info(f"📊 Event reminders check complete. Sent: {reminders_sent}")

    except Exception as e:
        logger.exception(f"❌ Error checking event reminders: {e}")


def format_event_reminder(event: Event) -> str:
    """Format event reminder message in Telegram HTML"""
    # Format time
    event_time = event.time.strftime("%H:%M") if event.time else "??:??"

    # Format duration
    duration_str = ""
    if event.duration_minutes:
        if event.duration_minutes < 60:
            duration_str = f" ({event.duration_minutes}мин)"
        else:
            hours = event.duration_minutes / 60
            duration_str = f" ({hours:.1f}ч)"

    # Build message
    minutes_before = event.reminder_minutes_before

    if minutes_before < 60:
        time_str = f"{minutes_before} минут"
    else:
        hours = minutes_before / 60
        if hours == int(hours):
            time_str = f"{int(hours)} час{'а' if hours < 5 else 'ов'}"
        else:
            time_str = f"{hours:.1f} часа"

    message = f"""🔔 <b>Напоминание о событии</b>

📅 <b>{event.title}</b>

⏰ Начало через {time_str}
🕐 Время: {event_time}{duration_str}
📆 Дата: {event.date.strftime('%d.%m.%Y')}"""

    if event.notes:
        message += f"\n\n💬 {event.notes}"

    return message

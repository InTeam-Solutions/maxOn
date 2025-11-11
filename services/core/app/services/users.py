from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.user import User


def create_or_update_user(
    session: Session,
    user_id: str,
    chat_id: str,
    timezone: Optional[str] = "Europe/Moscow",
    notification_enabled: Optional[bool] = True,
    event_reminders_enabled: Optional[bool] = True,
    goal_deadline_warnings_enabled: Optional[bool] = True,
    step_reminders_enabled: Optional[bool] = True,
    motivational_messages_enabled: Optional[bool] = True
) -> Dict[str, Any]:
    """Create a new user or update existing one"""
    user = session.query(User).filter(User.user_id == user_id).first()

    if user:
        # Update existing user
        user.chat_id = chat_id
        if timezone is not None:
            user.timezone = timezone
        if notification_enabled is not None:
            user.notification_enabled = notification_enabled
        if event_reminders_enabled is not None:
            user.event_reminders_enabled = event_reminders_enabled
        if goal_deadline_warnings_enabled is not None:
            user.goal_deadline_warnings_enabled = goal_deadline_warnings_enabled
        if step_reminders_enabled is not None:
            user.step_reminders_enabled = step_reminders_enabled
        if motivational_messages_enabled is not None:
            user.motivational_messages_enabled = motivational_messages_enabled
    else:
        # Create new user
        user = User(
            user_id=user_id,
            chat_id=chat_id,
            timezone=timezone,
            notification_enabled=notification_enabled,
            event_reminders_enabled=event_reminders_enabled,
            goal_deadline_warnings_enabled=goal_deadline_warnings_enabled,
            step_reminders_enabled=step_reminders_enabled,
            motivational_messages_enabled=motivational_messages_enabled
        )
        session.add(user)

    session.flush()
    return user.to_dict()


def get_user(session: Session, user_id: str) -> Optional[Dict[str, Any]]:
    """Get a user by ID"""
    user = session.query(User).filter(User.user_id == user_id).first()
    return user.to_dict() if user else None


def update_user_settings(
    session: Session,
    user_id: str,
    **settings
) -> Optional[Dict[str, Any]]:
    """Update user notification settings"""
    user = session.query(User).filter(User.user_id == user_id).first()

    if not user:
        return None

    # Update only provided settings
    for key, value in settings.items():
        if hasattr(user, key) and value is not None:
            setattr(user, key, value)

    session.flush()
    return user.to_dict()


def get_all_users_with_notifications_enabled(session: Session) -> list[Dict[str, Any]]:
    """Get all users who have notifications enabled (for worker service)"""
    users = session.query(User).filter(User.notification_enabled == True).all()
    return [user.to_dict() for user in users]

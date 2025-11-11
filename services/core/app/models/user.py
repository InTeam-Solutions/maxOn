from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from shared.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(String(64), primary_key=True, index=True)  # Telegram user ID
    chat_id = Column(String(64), nullable=False, index=True)  # Telegram chat ID for sending messages
    timezone = Column(String(64), default="Europe/Moscow", nullable=False)

    # Global notification switch
    notification_enabled = Column(Boolean, default=True, nullable=False)

    # Per-type notification settings
    event_reminders_enabled = Column(Boolean, default=True, nullable=False)
    goal_deadline_warnings_enabled = Column(Boolean, default=True, nullable=False)
    step_reminders_enabled = Column(Boolean, default=True, nullable=False)
    motivational_messages_enabled = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "timezone": self.timezone,
            "notification_enabled": self.notification_enabled,
            "event_reminders_enabled": self.event_reminders_enabled,
            "goal_deadline_warnings_enabled": self.goal_deadline_warnings_enabled,
            "step_reminders_enabled": self.step_reminders_enabled,
            "motivational_messages_enabled": self.motivational_messages_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

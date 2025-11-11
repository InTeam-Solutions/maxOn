from sqlalchemy import Column, Integer, String, Date, Time, Text, ForeignKey, Boolean
from shared.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(64), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    date = Column(Date, nullable=False, index=True)
    time = Column(Time, nullable=True)
    duration_minutes = Column(Integer, nullable=True)  # Duration in minutes
    repeat = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)

    # Links to goals/steps
    event_type = Column(String(32), default="user")  # "user" | "goal_step"
    linked_step_id = Column(Integer, ForeignKey("steps.id", ondelete="CASCADE"), nullable=True)
    linked_goal_id = Column(Integer, ForeignKey("goals.id", ondelete="CASCADE"), nullable=True)

    # Reminder settings
    reminder_minutes_before = Column(Integer, default=15, nullable=False)  # Minutes before event to send reminder
    reminder_enabled = Column(Boolean, default=True, nullable=False)  # Whether reminders are enabled for this event

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "date": self.date.isoformat(),
            "time": self.time.isoformat(timespec="minutes") if self.time else None,
            "duration_minutes": self.duration_minutes,
            "repeat": self.repeat,
            "notes": self.notes,
            "event_type": self.event_type,
            "linked_step_id": self.linked_step_id,
            "linked_goal_id": self.linked_goal_id,
            "reminder_minutes_before": self.reminder_minutes_before,
            "reminder_enabled": self.reminder_enabled,
        }
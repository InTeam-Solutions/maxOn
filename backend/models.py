from datetime import datetime, date
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Boolean,
    JSON,
)
from sqlalchemy.orm import relationship

from .database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    time = Column(DateTime, nullable=False)
    description = Column(String, nullable=False)
    cron = Column(String, nullable=True)

    skips = relationship("EventSkip", cascade="all, delete-orphan", back_populates="event")


class EventSkip(Base):
    __tablename__ = "event_skips"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"))
    date = Column(Date, nullable=False)

    event = relationship("Event", back_populates="skips")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    clarifications = Column(JSON, default=list)

    steps = relationship(
        "GoalStep", back_populates="goal", cascade="all, delete-orphan"
    )


class GoalStep(Base):
    __tablename__ = "goal_steps"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False)
    description = Column(String, nullable=False)
    is_done = Column(Boolean, default=False)

    goal = relationship("Goal", back_populates="steps")

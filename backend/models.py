from datetime import datetime, date
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
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

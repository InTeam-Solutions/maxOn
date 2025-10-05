from sqlalchemy import Column, Integer, String, Date, Time, Text
from shared.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(64), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    date = Column(Date, nullable=False, index=True)
    time = Column(Time, nullable=True)
    repeat = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "date": self.date.isoformat(),
            "time": self.time.isoformat(timespec="minutes") if self.time else None,
            "repeat": self.repeat,
            "notes": self.notes,
        }
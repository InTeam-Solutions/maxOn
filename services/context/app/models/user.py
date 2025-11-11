from sqlalchemy import Column, String, DateTime, JSON
from datetime import datetime
from shared.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(String(64), primary_key=True)
    timezone = Column(String(64), default="UTC", nullable=False)
    language = Column(String(16), default="ru", nullable=False)
    preferences = Column(JSON, default=dict, nullable=True)  # JSONB для PostgreSQL
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "timezone": self.timezone,
            "language": self.language,
            "preferences": self.preferences or {},
            "created_at": self.created_at.isoformat(),
        }
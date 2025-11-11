from sqlalchemy import Column, String, DateTime, JSON
from datetime import datetime, timedelta
from shared.database import Base


class SessionState(Base):
    __tablename__ = "session_states"

    user_id = Column(String(64), primary_key=True)
    current_state = Column(String(64), default="idle", nullable=False)
    context = Column(JSON, default=dict, nullable=True)  # State context data
    expires_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "current_state": self.current_state,
            "context": self.context or {},
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "updated_at": self.updated_at.isoformat(),
        }

    def is_expired(self):
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def set_expiry(self, hours: int = 1):
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime
from shared.database import Base


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), index=True, nullable=False)
    role = Column(String(16), nullable=False)  # 'user' | 'assistant' | 'system'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    meta = Column(JSON, default=dict, nullable=True)  # renamed from metadata

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.meta or {},  # return as metadata for API
        }
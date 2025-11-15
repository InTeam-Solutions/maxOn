from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ConversationMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class UserProfile(BaseModel):
    user_id: str
    timezone: str = "UTC"
    language: str = "ru"
    preferences: Optional[Dict[str, Any]] = None


class SessionState(BaseModel):
    user_id: str
    current_state: str = "idle"
    context: Dict[str, Any] = {}
    expires_at: Optional[datetime] = None


class UserContext(BaseModel):
    """Full user context for LLM"""
    profile: UserProfile
    conversation_history: List[ConversationMessage] = []
    session_state: SessionState
    active_goals: List[str] = []
    upcoming_events: List[Dict[str, Any]] = []
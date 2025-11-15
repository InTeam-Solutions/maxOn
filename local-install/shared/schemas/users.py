from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    chat_id: str
    timezone: str = "Europe/Moscow"
    notification_enabled: bool = True
    event_reminders_enabled: bool = True
    goal_deadline_warnings_enabled: bool = True
    step_reminders_enabled: bool = True
    motivational_messages_enabled: bool = True


class UserCreate(UserBase):
    user_id: str


class UserUpdate(BaseModel):
    chat_id: Optional[str] = None
    timezone: Optional[str] = None
    notification_enabled: Optional[bool] = None
    event_reminders_enabled: Optional[bool] = None
    goal_deadline_warnings_enabled: Optional[bool] = None
    step_reminders_enabled: Optional[bool] = None
    motivational_messages_enabled: Optional[bool] = None


class UserResponse(UserBase):
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

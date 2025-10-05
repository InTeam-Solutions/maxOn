from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, time as time_type


class EventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    date: date
    time: Optional[time_type] = None
    repeat: Optional[str] = None
    notes: Optional[str] = None


class EventCreate(EventBase):
    user_id: str


class EventUpdate(BaseModel):
    title: Optional[str] = None
    date: Optional[date] = None
    time: Optional[time_type] = None
    repeat: Optional[str] = None
    notes: Optional[str] = None


class EventResponse(EventBase):
    id: int
    user_id: str

    class Config:
        from_attributes = True
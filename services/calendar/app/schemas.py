from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CalendarCreate(BaseModel):
    user_id: int
    name: Optional[str] = Field(default=None, max_length=255)


class CalendarEnsureRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)


class CalendarResponse(BaseModel):
    id: UUID
    user_id: int
    name: Optional[str]
    public_ics_url: str

    model_config = ConfigDict(from_attributes=True)


class EventCreate(BaseModel):
    title: str = Field(max_length=255)
    brief_description: Optional[str] = Field(default=None)
    start_datetime: datetime
    duration_minutes: int = Field(gt=0, description="Duration in minutes")

    @field_validator("start_datetime")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("start_datetime must be timezone aware")
        return value.astimezone(timezone.utc)


class EventResponse(BaseModel):
    id: UUID
    calendar_id: UUID
    title: str
    brief_description: Optional[str]
    start_datetime: datetime
    end_datetime: datetime
    duration_minutes: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CalendarDetailResponse(CalendarResponse):
    events: List[EventResponse]

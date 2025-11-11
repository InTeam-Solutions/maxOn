from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, time as time_type


class StepBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    order: int
    estimated_hours: Optional[float] = None
    planned_date: Optional[date] = None
    planned_time: Optional[time_type] = None
    duration_minutes: Optional[int] = 120


class StepCreate(StepBase):
    goal_id: int


class StepResponse(StepBase):
    id: int
    goal_id: int
    status: str  # 'pending' | 'in_progress' | 'completed'
    completed_at: Optional[date] = None
    linked_event_id: Optional[int] = None

    class Config:
        from_attributes = True


class GoalBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    target_date: Optional[date] = None
    target_deadline: Optional[date] = None
    is_scheduled: Optional[bool] = False


class GoalCreate(GoalBase):
    user_id: str
    steps: Optional[List[StepBase]] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    target_date: Optional[date] = None
    target_deadline: Optional[date] = None
    is_scheduled: Optional[bool] = None


class GoalResponse(GoalBase):
    id: int
    user_id: str
    status: str  # 'active' | 'completed' | 'archived'
    progress_percent: float
    steps: List[StepResponse] = []

    class Config:
        from_attributes = True
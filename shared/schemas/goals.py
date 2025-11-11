from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


class StepBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    order: int
    estimated_hours: Optional[float] = None


class StepCreate(StepBase):
    goal_id: int


class StepResponse(StepBase):
    id: int
    goal_id: int
    status: str  # 'pending' | 'in_progress' | 'completed'
    completed_at: Optional[date] = None

    class Config:
        from_attributes = True


class GoalBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    target_date: Optional[date] = None


class GoalCreate(GoalBase):
    user_id: str
    steps: Optional[List[StepBase]] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    target_date: Optional[date] = None


class GoalResponse(GoalBase):
    id: int
    user_id: str
    status: str  # 'active' | 'completed' | 'archived'
    progress_percent: float
    steps: List[StepResponse] = []

    class Config:
        from_attributes = True
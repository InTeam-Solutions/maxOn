from sqlalchemy import Column, Integer, String, Text, Date, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from shared.database import Base


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(64), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="active")  # active | completed | archived
    progress_percent = Column(Float, default=0.0)
    target_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship
    steps = relationship("Step", back_populates="goal", cascade="all, delete-orphan")

    def to_dict(self, include_steps=True):
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "progress_percent": self.progress_percent,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "created_at": self.created_at.isoformat(),
        }
        if include_steps:
            data["steps"] = [step.to_dict() for step in self.steps]
        return data

    def update_progress(self):
        """Calculate progress based on completed steps"""
        if not self.steps:
            self.progress_percent = 0.0
            return

        completed = sum(1 for step in self.steps if step.status == "completed")
        self.progress_percent = (completed / len(self.steps)) * 100


class Step(Base):
    __tablename__ = "steps"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    goal_id = Column(Integer, ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    order = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="pending")  # pending | in_progress | completed
    estimated_hours = Column(Float, nullable=True)
    completed_at = Column(Date, nullable=True)

    # Relationship
    goal = relationship("Goal", back_populates="steps")

    def to_dict(self):
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "title": self.title,
            "order": self.order,
            "status": self.status,
            "estimated_hours": self.estimated_hours,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
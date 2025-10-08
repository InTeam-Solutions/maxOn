from typing import List, Dict, Any, Optional
from datetime import date as date_type
from dateutil import parser as dtparser
from sqlalchemy.orm import Session

from app.models.goal import Goal, Step


def parse_date(date_str: str) -> date_type:
    """Parse date string to date object"""
    return dtparser.parse(date_str).date()


def create_goal(
    session: Session,
    user_id: str,
    title: str,
    description: Optional[str] = None,
    target_date: Optional[str] = None,
    steps_data: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Create a new goal with optional steps"""
    goal = Goal(
        user_id=user_id,
        title=title.strip(),
        description=description,
        target_date=parse_date(target_date) if target_date else None,
        status="active"
    )
    session.add(goal)
    session.flush()

    # Add steps if provided
    if steps_data:
        for idx, step_data in enumerate(steps_data):
            step = Step(
                goal_id=goal.id,
                title=step_data.get("title", "").strip(),
                order=step_data.get("order", idx),
                estimated_hours=step_data.get("estimated_hours"),
                status="pending"
            )
            session.add(step)

        session.flush()
        goal.update_progress()
        session.flush()

    return goal.to_dict()


def get_goal(session: Session, goal_id: int, user_id: str) -> Optional[Dict[str, Any]]:
    """Get a goal by ID with its steps"""
    goal = session.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == user_id
    ).first()
    return goal.to_dict() if goal else None


def list_goals(
    session: Session,
    user_id: str,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """List user's goals"""
    q = session.query(Goal).filter(Goal.user_id == user_id)

    if status:
        q = q.filter(Goal.status == status)

    q = q.order_by(Goal.created_at.desc()).limit(limit)

    return [goal.to_dict() for goal in q.all()]


def update_goal(
    session: Session,
    goal_id: int,
    user_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    target_date: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Update a goal"""
    goal = session.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == user_id
    ).first()

    if not goal:
        return None

    if title is not None:
        goal.title = title.strip()
    if description is not None:
        goal.description = description
    if status is not None:
        goal.status = status
    if target_date is not None:
        goal.target_date = parse_date(target_date)

    session.flush()
    return goal.to_dict()


def delete_goal(session: Session, goal_id: int, user_id: str) -> bool:
    """Delete a goal (cascade deletes steps)"""
    goal = session.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == user_id
    ).first()

    if not goal:
        return False

    session.delete(goal)
    session.flush()
    return True


def add_step(
    session: Session,
    goal_id: int,
    user_id: str,
    title: str,
    order: Optional[int] = None,
    estimated_hours: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """Add a step to a goal"""
    # Verify goal ownership
    goal = session.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == user_id
    ).first()

    if not goal:
        return None

    # Determine order
    if order is None:
        max_order = session.query(Step).filter(Step.goal_id == goal_id).count()
        order = max_order

    step = Step(
        goal_id=goal_id,
        title=title.strip(),
        order=order,
        estimated_hours=estimated_hours,
        status="pending"
    )
    session.add(step)
    session.flush()

    # Update progress
    goal.update_progress()
    session.flush()

    return step.to_dict()


def update_step_status(
    session: Session,
    step_id: int,
    user_id: str,
    status: str
) -> Optional[Dict[str, Any]]:
    """Update step status and recalculate goal progress"""
    step = session.query(Step).join(Goal).filter(
        Step.id == step_id,
        Goal.user_id == user_id
    ).first()

    if not step:
        return None

    step.status = status

    if status == "completed":
        from datetime import date
        step.completed_at = date.today()

    session.flush()

    # Update goal progress
    step.goal.update_progress()
    session.flush()

    return step.to_dict()


def update_step(
    session: Session,
    step_id: int,
    user_id: str,
    title: Optional[str] = None,
    estimated_hours: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """Update step title and/or estimated hours"""
    step = session.query(Step).join(Goal).filter(
        Step.id == step_id,
        Goal.user_id == user_id
    ).first()

    if not step:
        return None

    if title is not None:
        step.title = title.strip()
    if estimated_hours is not None:
        step.estimated_hours = estimated_hours

    session.flush()
    return step.to_dict()


def delete_step(
    session: Session,
    step_id: int,
    user_id: str
) -> bool:
    """Delete a step and recalculate goal progress"""
    step = session.query(Step).join(Goal).filter(
        Step.id == step_id,
        Goal.user_id == user_id
    ).first()

    if not step:
        return False

    goal = step.goal
    session.delete(step)
    session.flush()

    # Update goal progress
    goal.update_progress()
    session.flush()

    return True
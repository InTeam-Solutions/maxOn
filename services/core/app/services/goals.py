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


# ==================== SCHEDULING FUNCTIONS ====================


def schedule_steps(
    session: Session,
    goal_id: int,
    user_id: str,
    schedule_plan: List[Dict[str, Any]],
    create_calendar_events: bool = True
) -> Dict[str, Any]:
    """
    Schedule steps in a goal with specific dates/times and optionally create calendar events

    Args:
        session: Database session
        goal_id: Goal ID
        user_id: User ID
        schedule_plan: List of dicts with format:
            [
                {"step_id": 1, "planned_date": "2025-11-15", "planned_time": "10:00"},
                {"step_id": 2, "planned_date": "2025-11-17", "planned_time": "14:00"},
                ...
            ]
        create_calendar_events: If True, creates Event entries for each step

    Returns:
        Goal dict with scheduled steps and created events
    """
    from app.models.event import Event
    from datetime import time as time_type

    # Verify goal ownership
    goal = session.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == user_id
    ).first()

    if not goal:
        return {"error": "Goal not found"}

    created_events = []

    for plan_item in schedule_plan:
        step_id = plan_item.get("step_id")
        planned_date_str = plan_item.get("planned_date")
        planned_time_str = plan_item.get("planned_time")

        # Get step
        step = session.query(Step).filter(
            Step.id == step_id,
            Step.goal_id == goal_id
        ).first()

        if not step:
            continue

        # Update step scheduling fields
        if planned_date_str:
            step.planned_date = parse_date(planned_date_str)

        if planned_time_str:
            # Parse time
            from dateutil import parser as dtparser
            t = dtparser.parse(planned_time_str).time()
            step.planned_time = t.replace(second=0, microsecond=0)

        # Calculate duration in minutes from estimated_hours
        if step.estimated_hours:
            step.duration_minutes = int(step.estimated_hours * 60)

        session.flush()

        # Create calendar event if requested
        if create_calendar_events and step.planned_date:
            event_title = f"{step.title}"
            event_notes = f"Шаг {step.order} для цели: {goal.title}"

            event = Event(
                user_id=user_id,
                title=event_title,
                date=step.planned_date,
                time=step.planned_time,
                notes=event_notes,
                event_type="goal_step",
                linked_step_id=step.id,
                linked_goal_id=goal.id
            )
            session.add(event)
            session.flush()

            # Link event to step
            step.linked_event_id = event.id
            session.flush()

            created_events.append(event.to_dict())

    # Mark goal as scheduled
    goal.is_scheduled = True
    session.flush()

    result = goal.to_dict()
    result["created_events"] = created_events

    return result


def get_free_time_slots(
    session: Session,
    user_id: str,
    start_date: str,
    end_date: str,
    time_preferences: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Find free time slots in user's calendar

    Args:
        session: Database session
        user_id: User ID
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        time_preferences: Dict with format:
            {
                "preferred_times": ["morning", "afternoon", "evening"],  # morning=9-12, afternoon=12-18, evening=18-22
                "preferred_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
                "duration_minutes": 120  # Desired duration per session
            }

    Returns:
        List of free slots: [{"date": "2025-11-15", "time": "10:00", "duration_minutes": 120}, ...]
    """
    from app.models.event import Event
    from datetime import datetime, timedelta

    # Parse dates
    start = parse_date(start_date)
    end = parse_date(end_date)

    # Get all existing events in the range
    existing_events = session.query(Event).filter(
        Event.user_id == user_id,
        Event.date >= start,
        Event.date <= end
    ).order_by(Event.date, Event.time).all()

    # Build a dict of occupied time slots
    occupied = {}
    for event in existing_events:
        date_key = event.date.isoformat()
        if date_key not in occupied:
            occupied[date_key] = []

        if event.time:
            occupied[date_key].append({
                "time": event.time,
                "duration": 60  # Default 1 hour if not specified
            })

    # Generate free slots
    free_slots = []
    current_date = start

    while current_date <= end:
        date_key = current_date.isoformat()
        weekday = current_date.weekday()  # 0=Monday, 6=Sunday

        # Check if this day is preferred
        if time_preferences and "preferred_days" in time_preferences:
            day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
            if day_names[weekday] not in time_preferences["preferred_days"]:
                current_date += timedelta(days=1)
                continue

        # Define time slots to check based on preferences
        time_slots = []
        if time_preferences and "preferred_times" in time_preferences:
            for pref in time_preferences["preferred_times"]:
                if pref == "morning":
                    time_slots.extend(["09:00", "10:00", "11:00"])
                elif pref == "afternoon":
                    time_slots.extend(["12:00", "13:00", "14:00", "15:00", "16:00", "17:00"])
                elif pref == "evening":
                    time_slots.extend(["18:00", "19:00", "20:00", "21:00"])
        else:
            # Default: business hours
            time_slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]

        # Check each time slot
        for time_str in time_slots:
            # Check if this slot is occupied
            is_free = True
            if date_key in occupied:
                from datetime import time as time_type
                from dateutil import parser as dtparser
                slot_time = dtparser.parse(time_str).time()

                for occ in occupied[date_key]:
                    if occ["time"] == slot_time:
                        is_free = False
                        break

            if is_free:
                duration = time_preferences.get("duration_minutes", 120) if time_preferences else 120
                free_slots.append({
                    "date": date_key,
                    "time": time_str,
                    "duration_minutes": duration
                })

        current_date += timedelta(days=1)

    return free_slots


def check_scheduling_feasibility(
    session: Session,
    user_id: str,
    goal_id: int,
    deadline: str,
    time_preferences: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Check if it's feasible to complete all goal steps by the deadline

    Args:
        session: Database session
        user_id: User ID
        goal_id: Goal ID
        deadline: Target deadline (YYYY-MM-DD)
        time_preferences: Time preferences dict

    Returns:
        {
            "feasible": True/False,
            "reason": "explanation",
            "required_hours": 42.0,
            "available_hours": 50.0,
            "suggested_deadline": "2025-12-15"  # If not feasible
        }
    """
    from datetime import datetime, timedelta

    # Get goal and steps
    goal = session.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == user_id
    ).first()

    if not goal:
        return {"feasible": False, "reason": "Goal not found"}

    # Calculate total required hours
    total_required_hours = sum(step.estimated_hours or 0 for step in goal.steps)

    if total_required_hours == 0:
        return {
            "feasible": True,
            "reason": "No time estimates for steps",
            "required_hours": 0,
            "available_hours": 0
        }

    # Get free slots between now and deadline
    today = datetime.now().date().isoformat()
    free_slots = get_free_time_slots(session, user_id, today, deadline, time_preferences)

    # Calculate available hours
    available_minutes = sum(slot["duration_minutes"] for slot in free_slots)
    available_hours = available_minutes / 60.0

    if available_hours >= total_required_hours:
        return {
            "feasible": True,
            "reason": f"Достаточно времени: доступно {available_hours:.1f}ч из {total_required_hours:.1f}ч",
            "required_hours": total_required_hours,
            "available_hours": available_hours
        }
    else:
        # Calculate suggested deadline
        deficit_hours = total_required_hours - available_hours
        # Assume avg 2 hours per day available
        additional_days = int(deficit_hours / 2) + 7  # Add buffer

        deadline_date = parse_date(deadline)
        suggested_deadline = deadline_date + timedelta(days=additional_days)

        return {
            "feasible": False,
            "reason": f"Не хватает времени: нужно {total_required_hours:.1f}ч, доступно {available_hours:.1f}ч",
            "required_hours": total_required_hours,
            "available_hours": available_hours,
            "suggested_deadline": suggested_deadline.isoformat()
        }
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime, time as time_type, timezone
import logging
import os

from dateutil import parser as dtparser
import httpx

from shared.database import init_db, get_db, Base
from shared.schemas.events import EventCreate, EventUpdate, EventResponse
from shared.schemas.goals import GoalCreate, GoalUpdate, GoalResponse, StepBase, StepResponse
from shared.schemas.products import ProductCreate, ProductResponse, CartItemCreate, CartItemResponse
from shared.schemas.users import UserCreate, UserUpdate, UserResponse
from shared.utils.logger import setup_logger

from app.services import events as events_service
from app.services import goals as goals_service
from app.services import products as products_service
from app.services import users as users_service

# Setup
app = FastAPI(
    title="MaxOn Core Service",
    description="Business logic for Events, Goals, Products, and Cart",
    version="0.1.0"
)

# CORS middleware for mini-app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = setup_logger("core_service", level=os.getenv("LOG_LEVEL", "INFO"))
CALENDAR_SERVICE_URL = os.getenv("CALENDAR_SERVICE_URL")
calendar_http_client: Optional[httpx.AsyncClient] = None
DEFAULT_EVENT_TIME = time_type(hour=9, minute=0)
DEFAULT_DURATION_MINUTES = 60


def _parse_calendar_user_id(raw_user_id: str) -> Optional[int]:
    try:
        return int(raw_user_id)
    except (TypeError, ValueError):
        logger.warning("Cannot convert user_id %s to int for calendar sync", raw_user_id)
        return None


def _build_iso_datetime(date_str: str, time_str: Optional[str]) -> str:
    date_obj = dtparser.parse(date_str).date()
    if time_str:
        time_obj = dtparser.parse(time_str).time().replace(second=0, microsecond=0)
    else:
        time_obj = DEFAULT_EVENT_TIME
    combined = datetime.combine(date_obj, time_obj, tzinfo=timezone.utc)
    return combined.isoformat().replace("+00:00", "Z")


async def _ensure_calendar_for_user(user_id: str, name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not (CALENDAR_SERVICE_URL and calendar_http_client):
        return None
    normalized_id = _parse_calendar_user_id(user_id)
    if normalized_id is None:
        return None

    payload: Dict[str, Any] = {}
    if name:
        payload["name"] = name

    try:
        response = await calendar_http_client.post(
            f"{CALENDAR_SERVICE_URL}/api/calendars/users/{normalized_id}/calendar",
            json=payload,
        )
        if response.status_code >= 400:
            logger.warning("Failed to ensure calendar for user %s: %s", user_id, response.text)
            return None
        return response.json()
    except Exception as exc:
        logger.warning("Calendar ensure failed for user %s: %s", user_id, exc)
        return None


async def _push_event_to_calendar(event: Dict[str, Any], calendar_name: Optional[str] = None) -> None:
    if not CALENDAR_SERVICE_URL or not calendar_http_client:
        return

    user_id = event.get("user_id")
    date_str = event.get("date")
    if not user_id or not date_str:
        return
    normalized_id = _parse_calendar_user_id(user_id)
    if normalized_id is None:
        return

    calendar = await _ensure_calendar_for_user(str(normalized_id), name=calendar_name)
    if not calendar:
        return

    try:
        payload = {
            "title": event.get("title") or "Событие",
            "brief_description": event.get("notes"),
            "start_datetime": _build_iso_datetime(date_str, event.get("time")),
            "duration_minutes": event.get("duration_minutes") or DEFAULT_DURATION_MINUTES,
        }
        response = await calendar_http_client.post(
            f"{CALENDAR_SERVICE_URL}/api/calendars/{calendar['id']}/events",
            json=payload,
        )
        if response.status_code >= 400:
            logger.warning("Failed to push event %s to calendar: %s", event.get("id"), response.text)
    except Exception as exc:
        logger.warning("Calendar sync failed for event %s: %s", event.get("id"), exc)


async def _push_events_batch(events: List[Dict[str, Any]], calendar_name: Optional[str] = None) -> None:
    for event in events:
        await _push_event_to_calendar(event, calendar_name=calendar_name)

# Database initialization
@app.on_event("startup")
async def startup():
    logger.info("Starting Core Service...")
    db = init_db()
    Base.metadata.create_all(bind=db.engine)
    global calendar_http_client
    if CALENDAR_SERVICE_URL:
        calendar_http_client = httpx.AsyncClient(timeout=10.0)
        logger.info("Calendar integration enabled at %s", CALENDAR_SERVICE_URL)
    else:
        logger.info("Calendar integration disabled (CALENDAR_SERVICE_URL not set)")
    logger.info("✅ Core Service started successfully")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down Core Service...")
    global calendar_http_client
    if calendar_http_client:
        await calendar_http_client.aclose()
        calendar_http_client = None


# Health checks
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "core"}


@app.get("/ready")
async def ready():
    try:
        db = get_db()
        with db.session_ctx() as session:
            session.execute("SELECT 1")
        return {"ready": True}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=500, detail="Database unavailable")


# ==================== EVENTS ====================

@app.post("/api/events", response_model=EventResponse, status_code=201)
async def create_event(event: EventCreate):
    """Create a new event"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            result = events_service.create_event(
                session=session,
                user_id=event.user_id,
                title=event.title,
                date=event.date.isoformat(),
                time=event.time.isoformat(timespec="minutes") if event.time else None,
                repeat=event.repeat,
                notes=event.notes,
                event_type=event.event_type,
                linked_step_id=event.linked_step_id,
                linked_goal_id=event.linked_goal_id
            )
        await _push_event_to_calendar(result)
        logger.info(f"Created event {result['id']} for user {event.user_id}")
        return result
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, user_id: str):
    """Get an event by ID"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            result = events_service.get_event(session, event_id, user_id)

        if not result:
            raise HTTPException(status_code=404, detail="Event not found")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/events", response_model=List[EventResponse])
async def search_events(
    user_id: str,
    title: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    time: Optional[str] = None,
    limit: int = 50
):
    """Search events with filters"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            results = events_service.search_events(
                session=session,
                user_id=user_id,
                title_query=title,
                start_date=start_date,
                end_date=end_date,
                time=time,
                limit=limit
            )
        return results
    except Exception as e:
        logger.error(f"Error searching events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/events/{event_id}", response_model=EventResponse)
async def update_event(event_id: int, user_id: str, update: EventUpdate):
    """Update an event"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            result = events_service.update_event(
                session=session,
                event_id=event_id,
                user_id=user_id,
                title=update.title,
                date=update.date.isoformat() if update.date else None,
                time=update.time.isoformat(timespec="minutes") if update.time else None,
                repeat=update.repeat,
                notes=update.notes
            )

        if not result:
            raise HTTPException(status_code=404, detail="Event not found")

        logger.info(f"Updated event {event_id} for user {user_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/events/{event_id}")
async def delete_event(event_id: int, user_id: str):
    """Delete an event"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            success = events_service.delete_event(session, event_id, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Event not found")

        logger.info(f"Deleted event {event_id} for user {user_id}")
        return {"status": "deleted", "id": event_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== GOALS ====================

@app.post("/api/goals", response_model=GoalResponse, status_code=201)
async def create_goal(goal: GoalCreate):
    """Create a new goal with optional steps"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            steps_data = [step.dict() for step in goal.steps] if goal.steps else None
            result = goals_service.create_goal(
                session=session,
                user_id=goal.user_id,
                title=goal.title,
                description=goal.description,
                target_date=goal.target_date.isoformat() if goal.target_date else None,
                steps_data=steps_data
            )
        logger.info(f"Created goal {result['id']} for user {goal.user_id}")
        return result
    except Exception as e:
        logger.error(f"Error creating goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/goals/free-slots")
async def get_free_slots(
    user_id: str,
    start_date: str,
    end_date: str,
    preferred_times: Optional[str] = None,
    preferred_days: Optional[str] = None,
    duration_minutes: Optional[int] = 120
):
    """Get free time slots in user's calendar"""
    try:
        db = get_db()

        # Build time preferences dict
        time_prefs = {
            "duration_minutes": duration_minutes
        }

        if preferred_times:
            time_prefs["preferred_times"] = preferred_times.split(",")

        if preferred_days:
            time_prefs["preferred_days"] = preferred_days.split(",")

        with db.session_ctx() as session:
            slots = goals_service.get_free_time_slots(
                session=session,
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                time_preferences=time_prefs if (preferred_times or preferred_days) else None
            )

        logger.info(f"Found {len(slots)} free slots for user {user_id}")
        return {"slots": slots, "count": len(slots)}
    except Exception as e:
        logger.error(f"Error getting free slots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/goals/{goal_id}", response_model=GoalResponse)
async def get_goal(goal_id: int, user_id: str):
    """Get a goal by ID with its steps"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            result = goals_service.get_goal(session, goal_id, user_id)

        if not result:
            raise HTTPException(status_code=404, detail="Goal not found")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/goals", response_model=List[GoalResponse])
async def list_goals(
    user_id: str,
    status: Optional[str] = None,
    limit: int = 50
):
    """List user's goals"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            results = goals_service.list_goals(
                session=session,
                user_id=user_id,
                status=status,
                limit=limit
            )
        return results
    except Exception as e:
        logger.error(f"Error listing goals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/goals/{goal_id}", response_model=GoalResponse)
async def update_goal(goal_id: int, user_id: str, update: GoalUpdate):
    """Update a goal"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            result = goals_service.update_goal(
                session=session,
                goal_id=goal_id,
                user_id=user_id,
                title=update.title,
                description=update.description,
                status=update.status,
                target_date=update.target_date.isoformat() if update.target_date else None
            )

        if not result:
            raise HTTPException(status_code=404, detail="Goal not found")

        logger.info(f"Updated goal {goal_id} for user {user_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/goals/{goal_id}")
async def delete_goal(goal_id: int, user_id: str):
    """Delete a goal"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            success = goals_service.delete_goal(session, goal_id, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Goal not found")

        logger.info(f"Deleted goal {goal_id} for user {user_id}")
        return {"status": "deleted", "id": goal_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/goals/{goal_id}/steps", response_model=StepResponse, status_code=201)
async def add_step(goal_id: int, user_id: str, step: StepBase):
    """Add a step to a goal"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            result = goals_service.add_step(
                session=session,
                goal_id=goal_id,
                user_id=user_id,
                title=step.title,
                order=step.order,
                estimated_hours=step.estimated_hours
            )

        if not result:
            raise HTTPException(status_code=404, detail="Goal not found")

        logger.info(f"Added step to goal {goal_id} for user {user_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding step: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class StepStatusUpdate(BaseModel):
    status: str
    user_id: str


class StepUpdate(BaseModel):
    title: Optional[str] = None
    estimated_hours: Optional[float] = None
    status: Optional[str] = None  # Add status field


@app.put("/api/steps/{step_id}/status", response_model=StepResponse)
async def update_step_status(step_id: int, update: StepStatusUpdate):
    """Update step status"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            result = goals_service.update_step_status(
                session=session,
                step_id=step_id,
                user_id=update.user_id,
                status=update.status
            )

        if not result:
            raise HTTPException(status_code=404, detail="Step not found")

        logger.info(f"Updated step {step_id} status to {update.status}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating step status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/steps/{step_id}", response_model=StepResponse)
async def update_step(step_id: int, user_id: str, update: StepUpdate):
    """Update step title, estimated hours, and/or status"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            # If status is being updated, use update_step_status
            if update.status is not None:
                result = goals_service.update_step_status(
                    session=session,
                    step_id=step_id,
                    user_id=user_id,
                    status=update.status
                )
            else:
                result = goals_service.update_step(
                    session=session,
                    step_id=step_id,
                    user_id=user_id,
                    title=update.title,
                    estimated_hours=update.estimated_hours
                )

        if not result:
            raise HTTPException(status_code=404, detail="Step not found")

        logger.info(f"Updated step {step_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating step: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/steps/{step_id}")
async def delete_step(step_id: int, user_id: str):
    """Delete a step"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            success = goals_service.delete_step(
                session=session,
                step_id=step_id,
                user_id=user_id
            )

        if not success:
            raise HTTPException(status_code=404, detail="Step not found")

        logger.info(f"Deleted step {step_id}")
        return {"status": "deleted", "id": step_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting step: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== GOAL SCHEDULING ====================


class SchedulePlanItem(BaseModel):
    step_id: int
    planned_date: str
    planned_time: Optional[str] = None


class ScheduleRequest(BaseModel):
    user_id: str
    schedule_plan: List[SchedulePlanItem]
    create_calendar_events: bool = True


@app.post("/api/goals/{goal_id}/schedule")
async def schedule_goal_steps(goal_id: int, request: ScheduleRequest):
    """Schedule steps in a goal with specific dates/times and create calendar events"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            # Convert Pydantic models to dicts
            schedule_plan = [item.dict() for item in request.schedule_plan]

            result = goals_service.schedule_steps(
                session=session,
                goal_id=goal_id,
                user_id=request.user_id,
                schedule_plan=schedule_plan,
                create_calendar_events=request.create_calendar_events
            )

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        await _push_events_batch(result.get("created_events", []), calendar_name=result.get("title"))
        logger.info(f"Scheduled {len(request.schedule_plan)} steps for goal {goal_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scheduling goal steps: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TimePreferences(BaseModel):
    preferred_times: Optional[List[str]] = None  # ["morning", "afternoon", "evening"]
    preferred_days: Optional[List[str]] = None   # ["mon", "tue", "wed", ...]
    duration_minutes: Optional[int] = 120


class FeasibilityRequest(BaseModel):
    user_id: str
    deadline: str
    time_preferences: Optional[TimePreferences] = None


@app.post("/api/goals/{goal_id}/check-feasibility")
async def check_feasibility(goal_id: int, request: FeasibilityRequest):
    """Check if it's feasible to complete goal by deadline"""
    try:
        db = get_db()

        # Convert TimePreferences to dict
        time_prefs = None
        if request.time_preferences:
            time_prefs = request.time_preferences.dict(exclude_none=True)

        with db.session_ctx() as session:
            result = goals_service.check_scheduling_feasibility(
                session=session,
                user_id=request.user_id,
                goal_id=goal_id,
                deadline=request.deadline,
                time_preferences=time_prefs
            )

        logger.info(f"Feasibility check for goal {goal_id}: {result['feasible']}")
        return result
    except Exception as e:
        logger.error(f"Error checking feasibility: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PRODUCTS & CART ====================

@app.post("/api/products", response_model=ProductResponse, status_code=201)
async def create_product(product: ProductCreate):
    """Create a new product"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            result = products_service.create_product(
                session=session,
                user_id=product.user_id,
                title=product.title,
                url=str(product.url),
                price=product.price,
                image_url=str(product.image_url) if product.image_url else None,
                source=product.source,
                description=product.description,
                rating=product.rating,
                linked_step_id=product.linked_step_id,
                created_from_prompt=product.created_from_prompt
            )
        logger.info(f"Created product {result['id']} for user {product.user_id}")
        return result
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products", response_model=List[ProductResponse])
async def list_products(
    user_id: str,
    linked_step_id: Optional[int] = None,
    limit: int = 50
):
    """List user's products"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            results = products_service.list_products(
                session=session,
                user_id=user_id,
                linked_step_id=linked_step_id,
                limit=limit
            )
        return results
    except Exception as e:
        logger.error(f"Error listing products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cart/items", response_model=CartItemResponse, status_code=201)
async def add_to_cart(item: CartItemCreate):
    """Add a product to cart"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            result = products_service.add_to_cart(
                session=session,
                user_id=item.user_id,
                product_id=item.product_id,
                quantity=item.quantity
            )

        if not result:
            raise HTTPException(status_code=404, detail="Product not found")

        logger.info(f"Added product {item.product_id} to cart for user {item.user_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cart/{user_id}", response_model=List[CartItemResponse])
async def get_cart(user_id: str):
    """Get user's cart"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            results = products_service.get_cart(session, user_id)
        return results
    except Exception as e:
        logger.error(f"Error getting cart: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/cart/items/{item_id}")
async def remove_from_cart(item_id: int, user_id: str):
    """Remove an item from cart"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            success = products_service.remove_from_cart(session, item_id, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Cart item not found")

        logger.info(f"Removed item {item_id} from cart for user {user_id}")
        return {"status": "removed", "id": item_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing from cart: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/cart/{user_id}/clear")
async def clear_cart(user_id: str):
    """Clear user's cart"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            count = products_service.clear_cart(session, user_id)

        logger.info(f"Cleared {count} items from cart for user {user_id}")
        return {"status": "cleared", "count": count}
    except Exception as e:
        logger.error(f"Error clearing cart: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== USERS ====================

@app.post("/api/users", response_model=UserResponse, status_code=201)
async def create_or_update_user(user: UserCreate):
    """Create a new user or update existing one"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            result = users_service.create_or_update_user(
                session=session,
                user_id=user.user_id,
                chat_id=user.chat_id,
                timezone=user.timezone,
                notification_enabled=user.notification_enabled,
                event_reminders_enabled=user.event_reminders_enabled,
                goal_deadline_warnings_enabled=user.goal_deadline_warnings_enabled,
                step_reminders_enabled=user.step_reminders_enabled,
                motivational_messages_enabled=user.motivational_messages_enabled
            )
        logger.info(f"Created/updated user {user.user_id}")
        return result
    except Exception as e:
        logger.error(f"Error creating/updating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user settings by ID"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            result = users_service.get_user(session, user_id)

        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/users/{user_id}", response_model=UserResponse)
async def update_user_settings(user_id: str, update: UserUpdate):
    """Update user notification settings"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            result = users_service.update_user_settings(
                session=session,
                user_id=user_id,
                **update.model_dump(exclude_unset=True)
            )

        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        logger.info(f"Updated settings for user {user_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users")
async def get_all_users_with_notifications():
    """Get all users with notifications enabled (for worker service)"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            results = users_service.get_all_users_with_notifications_enabled(session)
        return results
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Statistics & Leaderboard ====================


@app.get("/api/leaderboard")
async def get_leaderboard(limit: int = 20):
    """
    Get leaderboard of users ranked by streak days (consecutive days with completed tasks).
    Returns anonymous user IDs formatted as 'User #{rank}'.
    """
    try:
        db = get_db()
        with db.session_ctx() as session:
            # Import models
            from app.models.goal import Goal, Step
            from sqlalchemy import func, distinct
            from datetime import datetime, timedelta

            # Get all users with their completed steps
            # Calculate streak days: consecutive days with at least 1 completed step
            user_stats = []

            # Get all users who have goals
            users_with_goals = session.query(distinct(Goal.user_id)).all()

            for (user_id,) in users_with_goals:
                # Get all completed steps for this user, ordered by planned_date
                completed_steps = (
                    session.query(Step)
                    .join(Goal, Goal.id == Step.goal_id)
                    .filter(
                        Goal.user_id == user_id,
                        Step.status == 'completed',
                        Step.planned_date.isnot(None)
                    )
                    .order_by(Step.planned_date.desc())
                    .all()
                )

                if not completed_steps:
                    continue

                # Calculate streak: count consecutive days from today backwards
                streak_days = 0
                today = datetime.now().date()

                # Get unique dates of completed tasks
                completed_dates = sorted(
                    set(step.planned_date for step in completed_steps if step.planned_date),
                    reverse=True
                )

                # Calculate streak from most recent date
                if completed_dates:
                    current_date = completed_dates[0]

                    # Only count if streak includes today or yesterday
                    if (today - current_date).days <= 1:
                        streak_days = 1

                        for i in range(1, len(completed_dates)):
                            days_diff = (completed_dates[i-1] - completed_dates[i]).days
                            if days_diff == 1:
                                streak_days += 1
                            else:
                                break

                if streak_days > 0:
                    user_stats.append({
                        'user_id': user_id,
                        'streak_days': streak_days
                    })

            # Sort by streak_days descending
            user_stats.sort(key=lambda x: x['streak_days'], reverse=True)

            # Limit results and add rank with anonymous display names
            leaderboard = []
            for rank, user_stat in enumerate(user_stats[:limit], start=1):
                leaderboard.append({
                    'userId': user_stat['user_id'],
                    'displayName': f'User #{rank}',
                    'streakDays': user_stat['streak_days'],
                    'rank': rank
                })

            return leaderboard

    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

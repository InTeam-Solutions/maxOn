from typing import Dict, Any, List
from sqlalchemy.orm import Session
import os

from shared.utils.http_client import HTTPClient
from app.models.user import UserProfile
from app.models.conversation import ConversationMessage
from app.models.session import SessionState
from app.services.redis_cache import get_cache


async def build_llm_context(user_id: str, session_db: Session) -> Dict[str, Any]:
    """
    Build complete context for LLM from:
    - User profile
    - Recent conversation history (from Redis or DB)
    - Active goals (from Core Service)
    - Upcoming events (from Core Service)
    - Current session state
    """

    # 1. Get user profile
    profile = session_db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        # Create default profile
        profile = UserProfile(user_id=user_id)
        session_db.add(profile)
        session_db.flush()

    # 2. Get conversation history (try Redis first, fallback to DB)
    cache = get_cache()
    history_key = f"conversation:{user_id}"
    history = cache.lrange(history_key, 0, 9)  # Last 10 messages

    if not history:
        # Fallback to DB
        messages = session_db.query(ConversationMessage).filter(
            ConversationMessage.user_id == user_id
        ).order_by(ConversationMessage.timestamp.desc()).limit(10).all()

        history = [msg.to_dict() for msg in reversed(messages)]

    # 3. Get session state
    session_state = session_db.query(SessionState).filter(
        SessionState.user_id == user_id
    ).first()

    if not session_state:
        session_state = SessionState(user_id=user_id)
        session_db.add(session_state)
        session_db.flush()

    # Check if expired
    if session_state.is_expired():
        session_state.current_state = "idle"
        session_state.context = {}
        session_db.flush()

    # 4. Fetch active goals from Core Service (if available)
    active_goals = []
    try:
        core_url = os.getenv("CORE_SERVICE_URL", "http://core:8004")
        core_client = HTTPClient(core_url)
        goals_response = await core_client.get("/api/goals", params={"user_id": user_id, "status": "active", "limit": 3})

        # Extract goal titles
        active_goals = [goal.get("title", "") for goal in goals_response]
    except Exception as e:
        # Log but don't fail if Core Service unavailable
        pass

    # 5. Fetch upcoming events from Core Service (if available)
    upcoming_events = []
    try:
        from datetime import date, timedelta
        today = date.today().isoformat()
        next_week = (date.today() + timedelta(days=7)).isoformat()

        core_url = os.getenv("CORE_SERVICE_URL", "http://core:8004")
        core_client = HTTPClient(core_url)
        events_response = await core_client.get(
            "/api/events",
            params={"user_id": user_id, "start_date": today, "end_date": next_week, "limit": 3}
        )

        # Format events
        for event in events_response:
            event_str = f"{event.get('title')} - {event.get('date')}"
            if event.get('time'):
                event_str += f" {event.get('time')}"
            upcoming_events.append(event_str)
    except Exception as e:
        pass

    # Build full context
    return {
        "profile": profile.to_dict(),
        "conversation_history": history,
        "session_state": session_state.to_dict(),
        "active_goals": active_goals,
        "upcoming_events": upcoming_events,
    }
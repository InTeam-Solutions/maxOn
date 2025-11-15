from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import os

from shared.database import init_db, get_db, Base
from shared.utils.logger import setup_logger

from app.models.user import UserProfile
from app.models.conversation import ConversationMessage
from app.models.session import SessionState
from app.services.redis_cache import get_cache
from app.services.context_builder import build_llm_context

# Setup
app = FastAPI(
    title="Initio Context Service",
    description="User context, conversation memory, and session management",
    version="0.1.0"
)

logger = setup_logger("context_service", level=os.getenv("LOG_LEVEL", "INFO"))

# Database initialization
@app.on_event("startup")
async def startup():
    logger.info("Starting Context Service...")
    db = init_db()
    Base.metadata.create_all(bind=db.engine)
    logger.info("✅ Context Service started successfully")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down Context Service...")


# Health checks
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "context"}


@app.get("/ready")
async def ready():
    try:
        db = get_db()
        with db.session_ctx() as session:
            session.execute("SELECT 1")

        # Check Redis
        cache = get_cache()
        cache.client.ping()

        return {"ready": True}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unavailable")


# ==================== REQUEST/RESPONSE MODELS ====================

class MessageCreate(BaseModel):
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    metadata: Optional[Dict[str, Any]] = None


class SessionUpdate(BaseModel):
    current_state: str
    context: Dict[str, Any]
    expiry_hours: Optional[int] = 1


class ProfileUpdate(BaseModel):
    timezone: Optional[str] = None
    language: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


# ==================== USER PROFILE ====================

@app.get("/api/profile/{user_id}")
async def get_profile(user_id: str):
    """Get or create user profile"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            profile = session.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()

            if not profile:
                profile = UserProfile(user_id=user_id)
                session.add(profile)
                session.flush()

        return profile.to_dict()
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/profile/{user_id}")
async def update_profile(user_id: str, update: ProfileUpdate):
    """Update user profile"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            profile = session.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()

            if not profile:
                profile = UserProfile(user_id=user_id)
                session.add(profile)

            if update.timezone:
                profile.timezone = update.timezone
            if update.language:
                profile.language = update.language
            if update.preferences is not None:
                profile.preferences = update.preferences

            session.flush()
            result = profile.to_dict()

        logger.info(f"Updated profile for user {user_id}")
        return result
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CONVERSATION HISTORY ====================

@app.post("/api/conversation/{user_id}/messages")
async def add_message(user_id: str, message: MessageCreate):
    """Add a message to conversation history"""
    try:
        # Store in DB
        db = get_db()
        with db.session_ctx() as session:
            msg = ConversationMessage(
                user_id=user_id,
                role=message.role,
                content=message.content,
                meta=message.metadata or {}
            )
            session.add(msg)
            session.flush()
            result = msg.to_dict()

        # Store in Redis (hot storage)
        cache = get_cache()
        history_key = f"conversation:{user_id}"
        cache.lpush(history_key, result, max_length=20)
        cache.expire(history_key, 86400)  # 24h TTL

        logger.info(f"Added {message.role} message for user {user_id}")
        return result
    except Exception as e:
        logger.error(f"Error adding message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversation/{user_id}/messages")
async def get_messages(user_id: str, limit: int = 20):
    """Get recent conversation messages"""
    try:
        # Try Redis first
        cache = get_cache()
        history_key = f"conversation:{user_id}"
        messages = cache.lrange(history_key, 0, limit - 1)

        if messages:
            return messages

        # Fallback to DB
        db = get_db()
        with db.session_ctx() as session:
            msgs = session.query(ConversationMessage).filter(
                ConversationMessage.user_id == user_id
            ).order_by(ConversationMessage.timestamp.desc()).limit(limit).all()

            messages = [msg.to_dict() for msg in reversed(msgs)]

        return messages
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/conversation/{user_id}/messages")
async def clear_history(user_id: str):
    """Clear conversation history"""
    try:
        # Clear Redis
        cache = get_cache()
        history_key = f"conversation:{user_id}"
        cache.delete(history_key)

        # Clear DB (keep only last 50 for archive)
        db = get_db()
        with db.session_ctx() as session:
            # Get IDs to keep
            keep_msgs = session.query(ConversationMessage.id).filter(
                ConversationMessage.user_id == user_id
            ).order_by(ConversationMessage.timestamp.desc()).limit(50).all()

            keep_ids = [msg.id for msg in keep_msgs]

            # Delete others
            if keep_ids:
                session.query(ConversationMessage).filter(
                    ConversationMessage.user_id == user_id,
                    ~ConversationMessage.id.in_(keep_ids)
                ).delete(synchronize_session=False)
            else:
                session.query(ConversationMessage).filter(
                    ConversationMessage.user_id == user_id
                ).delete()

            session.flush()

        logger.info(f"Cleared conversation history for user {user_id}")
        return {"status": "cleared"}
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SESSION STATE ====================

@app.get("/api/session/{user_id}")
async def get_session(user_id: str):
    """Get current session state"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            state = session.query(SessionState).filter(
                SessionState.user_id == user_id
            ).first()

            if not state:
                state = SessionState(user_id=user_id)
                session.add(state)
                session.flush()

            # Check if expired
            if state.is_expired():
                state.current_state = "idle"
                state.context = {}
                session.flush()

            result = state.to_dict()

        return result
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/session/{user_id}")
async def update_session(user_id: str, update: SessionUpdate):
    """Update session state"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            state = session.query(SessionState).filter(
                SessionState.user_id == user_id
            ).first()

            if not state:
                state = SessionState(user_id=user_id)
                session.add(state)

            state.current_state = update.current_state
            state.context = update.context
            state.set_expiry(hours=update.expiry_hours)

            session.flush()
            result = state.to_dict()

        logger.info(f"Updated session for user {user_id}: state={update.current_state}")
        return result
    except Exception as e:
        logger.error(f"Error updating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/session/{user_id}")
async def reset_session(user_id: str):
    """Reset session to idle"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            state = session.query(SessionState).filter(
                SessionState.user_id == user_id
            ).first()

            if state:
                state.current_state = "idle"
                state.context = {}
                state.expires_at = None
                session.flush()

        logger.info(f"Reset session for user {user_id}")
        return {"status": "reset"}
    except Exception as e:
        logger.error(f"Error resetting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== FULL CONTEXT ====================

@app.get("/api/context/{user_id}")
async def get_full_context(user_id: str):
    """
    Get complete user context for LLM:
    - Profile
    - Recent conversation history
    - Session state
    - Active goals (from Core)
    - Upcoming events (from Core)
    """
    try:
        db = get_db()
        with db.session_ctx() as session:
            context = await build_llm_context(user_id, session)

        return context
    except Exception as e:
        logger.error(f"Error building full context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/context/{user_id}/summary")
async def get_context_summary(user_id: str):
    """Get a brief summary of user context (for logging/debugging)"""
    try:
        db = get_db()
        with db.session_ctx() as session:
            context = await build_llm_context(user_id, session)

        summary = {
            "user_id": user_id,
            "timezone": context["profile"]["timezone"],
            "language": context["profile"]["language"],
            "current_state": context["session_state"]["current_state"],
            "conversation_length": len(context["conversation_history"]),
            "active_goals_count": len(context["active_goals"]),
            "upcoming_events_count": len(context["upcoming_events"]),
        }

        return summary
    except Exception as e:
        logger.error(f"Error getting context summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
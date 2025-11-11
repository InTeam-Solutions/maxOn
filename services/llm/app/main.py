from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import hashlib
import logging
import os
import pytz

from openai import OpenAI
import redis

from shared.utils.logger import setup_logger
from shared.utils.analytics import track_event, increment_user_counter
from app.prompts.system import SYSTEM_PROMPT_TEMPLATE
from app.prompts.summarizer import SUMMARIZE_PROMPT_TEMPLATE
from app.prompts.goal_coach import GOAL_STEPS_PROMPT_TEMPLATE
from app.prompts.goal_scheduler import SCHEDULE_GOAL_PROMPT_TEMPLATE

# Setup
app = FastAPI(
    title="Initio LLM Service",
    description="OpenAI integration with context-aware prompts",
    version="0.1.0"
)

logger = setup_logger("llm_service", level=os.getenv("LOG_LEVEL", "INFO"))

# OpenAI client with proxy
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.proxyapi.ru/openai/v1")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")
OPENAI_WHISPER_MODEL = os.getenv("OPENAI_WHISPER_MODEL", "whisper-1")

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=OPENAI_BASE_URL
)

# Redis cache
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/2")
cache_client = redis.from_url(redis_url, decode_responses=True)


@app.on_event("startup")
async def startup():
    logger.info("Starting LLM Service...")
    logger.info(f"OpenAI Base URL: {OPENAI_BASE_URL}")
    # Test OpenAI connection
    try:
        openai_client.models.list()
        logger.info("✅ OpenAI connection successful")
    except Exception as e:
        logger.error(f"❌ OpenAI connection failed: {e}")

    # Test Redis
    try:
        cache_client.ping()
        logger.info("✅ Redis connection successful")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")

    logger.info("✅ LLM Service started successfully")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down LLM Service...")


# Health checks
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "llm"}


@app.get("/ready")
async def ready():
    try:
        openai_client.models.list()
        cache_client.ping()
        return {"ready": True}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unavailable")


# ==================== REQUEST/RESPONSE MODELS ====================

class ParseRequest(BaseModel):
    message: str
    context: Dict[str, Any]


class SummarizeRequest(BaseModel):
    core_result: Dict[str, Any]


class GenerateStepsRequest(BaseModel):
    goal_title: str
    current_level: Optional[str] = None
    time_commitment: Optional[str] = None
    additional_context: Optional[str] = None


class GenerateScheduleRequest(BaseModel):
    goal_title: str
    steps: List[Dict[str, Any]]
    start_date: str
    deadline: str
    preferred_times: Optional[List[str]] = None
    preferred_days: Optional[List[str]] = None
    duration_minutes: int = 120
    existing_events: Optional[List[Dict[str, Any]]] = None
    free_slots: Optional[List[Dict[str, Any]]] = None


class ChatRequest(BaseModel):
    message: str
    system_prompt: Optional[str] = None


# ==================== HELPER FUNCTIONS ====================

def get_cache_key(prefix: str, data: str) -> str:
    """Generate cache key from data hash"""
    hash_obj = hashlib.md5(data.encode())
    return f"{prefix}:{hash_obj.hexdigest()}"


def get_from_cache(key: str) -> Optional[Dict[str, Any]]:
    """Get from Redis cache"""
    try:
        value = cache_client.get(key)
        if value:
            return json.loads(value)
    except Exception as e:
        logger.error(f"Cache GET error: {e}")
    return None


def set_to_cache(key: str, value: Dict[str, Any], ttl: int = 3600):
    """Set to Redis cache with TTL"""
    try:
        cache_client.setex(key, ttl, json.dumps(value))
    except Exception as e:
        logger.error(f"Cache SET error: {e}")


def render_system_prompt(context: Dict[str, Any]) -> str:
    """Render system prompt with context"""

    # Get current time in user's timezone
    tz_name = context.get("profile", {}).get("timezone", "UTC")
    try:
        tz = pytz.timezone(tz_name)
    except:
        tz = pytz.UTC

    current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")

    # Prepare context for template
    template_context = {
        "user_name": context.get("profile", {}).get("user_id", "друг"),
        "current_time": current_time,
        "timezone": tz_name,
        "active_goals": context.get("active_goals", []),
        "upcoming_events": context.get("upcoming_events", []),
        "conversation_history": context.get("conversation_history", []),
        "current_state": context.get("session_state", {}).get("current_state", "idle"),
        "state_context": context.get("session_state", {}).get("context", {}),
    }

    return SYSTEM_PROMPT_TEMPLATE.render(**template_context)


# ==================== LLM ENDPOINTS ====================

@app.post("/api/parse")
async def parse_message(request: ParseRequest):
    """
    Parse user message into structured intent using LLM
    with context injection
    """
    try:
        user_id = request.context.get("profile", {}).get("user_id", "unknown")

        # Check cache
        cache_key = get_cache_key("parse", f"{request.message}:{json.dumps(request.context)}")
        cached = get_from_cache(cache_key)
        if cached:
            logger.info("Cache hit for parse")
            return cached

        # Render system prompt with context
        system_prompt = render_system_prompt(request.context)

        # Call OpenAI
        response = openai_client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message},
            ],
            temperature=0.2,
        )

        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)

        # Track to Mixpanel
        usage = response.usage
        track_event(user_id, "LLM Parse", {
            "model": OPENAI_CHAT_MODEL,
            "intent": result.get("intent"),
            "tokens_input": usage.prompt_tokens,
            "tokens_output": usage.completion_tokens,
            "tokens_total": usage.total_tokens,
            "message_length": len(request.message)
        })
        increment_user_counter(user_id, "total_parse_tokens", usage.total_tokens)

        # Cache result
        set_to_cache(cache_key, result, ttl=3600)  # 1 hour

        logger.info(f"Parsed message: {request.message[:50]}... -> {result.get('intent')}")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}, raw response: {raw}")
        raise HTTPException(status_code=500, detail="Failed to parse LLM response")
    except Exception as e:
        logger.error(f"Error parsing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/summarize")
async def summarize_response(request: SummarizeRequest):
    """
    Summarize core service result into user-facing response
    """
    try:
        # Render prompt
        prompt = SUMMARIZE_PROMPT_TEMPLATE.render(core_result=request.core_result)

        # Call OpenAI
        response = openai_client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(request.core_result, ensure_ascii=False)},
            ],
            temperature=0.2,
        )

        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)

        logger.info(f"Summarized result: {result.get('intent')}")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}, raw response: {raw}")
        raise HTTPException(status_code=500, detail="Failed to parse LLM response")
    except Exception as e:
        logger.error(f"Error summarizing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-steps")
async def generate_steps(request: GenerateStepsRequest):
    """
    Generate steps for a goal using LLM
    """
    try:
        # Extract user_id from additional_context if available
        user_id = "unknown"

        # Check cache
        cache_key = get_cache_key("steps", f"{request.goal_title}:{request.current_level}:{request.time_commitment}")
        cached = get_from_cache(cache_key)
        if cached:
            logger.info("Cache hit for generate-steps")
            return cached

        # Render prompt
        prompt = GOAL_STEPS_PROMPT_TEMPLATE.render(
            goal_title=request.goal_title,
            current_level=request.current_level,
            time_commitment=request.time_commitment,
            additional_context=request.additional_context
        )

        # Call OpenAI
        response = openai_client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": "Ты — коуч по достижению целей. Создавай конкретные, действенные микрошаги."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        raw = response.choices[0].message.content.strip()

        # Try to extract JSON if wrapped in markdown
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        result = json.loads(raw)

        # Track to Mixpanel
        usage = response.usage
        track_event(user_id, "LLM Generate Steps", {
            "model": OPENAI_CHAT_MODEL,
            "goal_title": request.goal_title,
            "steps_count": len(result),
            "tokens_input": usage.prompt_tokens,
            "tokens_output": usage.completion_tokens,
            "tokens_total": usage.total_tokens
        })
        increment_user_counter(user_id, "total_steps_tokens", usage.total_tokens)

        # Cache result
        set_to_cache(cache_key, result, ttl=86400)  # 24 hours

        logger.info(f"Generated {len(result)} steps for goal: {request.goal_title}")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}, raw response: {raw}")
        raise HTTPException(status_code=500, detail="Failed to parse LLM response")
    except Exception as e:
        logger.error(f"Error generating steps: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-schedule")
async def generate_schedule(request: GenerateScheduleRequest):
    """
    Generate optimal schedule for goal steps using LLM
    """
    try:
        user_id = "unknown"

        # Check cache
        cache_key = get_cache_key(
            "schedule",
            f"{request.goal_title}:{request.start_date}:{request.deadline}:{len(request.steps)}"
        )
        cached = get_from_cache(cache_key)
        if cached:
            logger.info("Cache hit for generate-schedule")
            return cached

        # Render prompt with all scheduling context
        prompt = SCHEDULE_GOAL_PROMPT_TEMPLATE.render(
            goal_title=request.goal_title,
            steps=request.steps,
            start_date=request.start_date,
            deadline=request.deadline,
            preferred_times=request.preferred_times or [],
            preferred_days=request.preferred_days or [],
            duration_minutes=request.duration_minutes,
            existing_events=request.existing_events or [],
            free_slots=request.free_slots or []
        )

        # Call OpenAI
        response = openai_client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": "Ты — планировщик задач. Создавай оптимальные расписания с учетом всех ограничений."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,  # Lower temperature for more deterministic scheduling
        )

        raw = response.choices[0].message.content.strip()

        # Try to extract JSON if wrapped in markdown
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        result = json.loads(raw)

        # Track to Mixpanel
        usage = response.usage
        track_event(user_id, "LLM Generate Schedule", {
            "model": OPENAI_CHAT_MODEL,
            "goal_title": request.goal_title,
            "steps_count": len(request.steps),
            "schedule_items": len(result) if isinstance(result, list) else 0,
            "tokens_input": usage.prompt_tokens,
            "tokens_output": usage.completion_tokens,
            "tokens_total": usage.total_tokens,
            "days_span": (datetime.fromisoformat(request.deadline) - datetime.fromisoformat(request.start_date)).days
        })
        increment_user_counter(user_id, "total_schedule_tokens", usage.total_tokens)

        # Cache result
        set_to_cache(cache_key, result, ttl=1800)  # 30 minutes cache

        logger.info(f"Generated schedule for goal: {request.goal_title}, {len(result) if isinstance(result, list) else 0} scheduled items")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}, raw response: {raw}")
        raise HTTPException(status_code=500, detail="Failed to parse LLM response")
    except Exception as e:
        logger.error(f"Error generating schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Free-form chat (for small_talk)
    """
    try:
        system = request.system_prompt or "Ты — дружелюбный ассистент. Отвечай кратко и по делу."

        response = openai_client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": request.message},
            ],
            temperature=0.7,
        )

        result = {
            "response": response.choices[0].message.content.strip()
        }

        return result

    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transcribe")
async def transcribe_audio(file: bytes = Body(...), user_id: str = "unknown"):
    """
    Transcribe audio file using Whisper API
    Accepts audio file bytes in request body and returns text transcription
    """
    try:
        from io import BytesIO

        # Create file-like object from bytes
        audio_file = BytesIO(file)
        audio_file.name = "audio.ogg"  # Telegram voice messages are OGG

        # Call Whisper API
        transcription = openai_client.audio.transcriptions.create(
            model=OPENAI_WHISPER_MODEL,
            file=audio_file,
            language="ru"  # Russian language
        )

        result = {
            "text": transcription.text
        }

        # Estimate audio duration (OGG Opus ~20 kbps average)
        audio_size_bytes = len(file)
        estimated_duration_seconds = (audio_size_bytes * 8) / (20 * 1024)  # bytes to seconds at 20kbps

        # Track to Mixpanel
        track_event(user_id, "Voice Transcription", {
            "model": OPENAI_WHISPER_MODEL,
            "audio_size_bytes": audio_size_bytes,
            "audio_seconds": round(estimated_duration_seconds, 2),
            "transcription_length": len(transcription.text)
        })
        increment_user_counter(user_id, "total_voice_messages", 1)

        logger.info(f"Transcribed audio: {transcription.text[:50]}...")
        return result

    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/cache")
async def clear_cache():
    """Clear all LLM cache (for debugging)"""
    try:
        # Clear only our keys (parse:*, steps:*)
        for pattern in ["parse:*", "steps:*"]:
            keys = cache_client.keys(pattern)
            if keys:
                cache_client.delete(*keys)

        logger.info("Cleared LLM cache")
        return {"status": "cleared"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

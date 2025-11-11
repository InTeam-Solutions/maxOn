from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import os

from shared.utils.logger import setup_logger
from shared.utils.analytics import track_event, increment_user_counter
from app.state_machine import StateMachine, DialogState
import httpx

# Setup
app = FastAPI(
    title="Initio Orchestrator",
    description="Service coordination and state machine",
    version="0.1.0"
)

logger = setup_logger("orchestrator", level=os.getenv("LOG_LEVEL", "INFO"))

# Service URLs
CONTEXT_SERVICE_URL = os.getenv("CONTEXT_SERVICE_URL", "http://context:8002")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://llm:8003")
CORE_SERVICE_URL = os.getenv("CORE_SERVICE_URL", "http://core:8004")

# HTTP client (synchronous)
http_client = httpx.Client(timeout=30.0)


@app.on_event("startup")
async def startup():
    logger.info("Starting Orchestrator Service...")
    logger.info(f"Context: {CONTEXT_SERVICE_URL}")
    logger.info(f"LLM: {LLM_SERVICE_URL}")
    logger.info(f"Core: {CORE_SERVICE_URL}")
    logger.info("✅ Orchestrator Service started successfully")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down Orchestrator Service...")


# Health checks
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "orchestrator"}


@app.get("/ready")
async def ready():
    try:
        # Check all dependent services
        http_client.get(f"{CONTEXT_SERVICE_URL}/health")
        http_client.get(f"{LLM_SERVICE_URL}/health")
        http_client.get(f"{CORE_SERVICE_URL}/health")
        return {"ready": True}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unavailable")


# ==================== REQUEST/RESPONSE MODELS ====================

class ProcessMessageRequest(BaseModel):
    user_id: str
    message: str


class ProcessMessageResponse(BaseModel):
    success: bool
    response_type: str  # 'text' | 'table' | 'clarification' | 'inline_buttons'
    text: Optional[str] = None
    items: Optional[list] = None
    set_id: Optional[str] = None
    buttons: Optional[list] = None  # For inline buttons: [{"text": "...", "callback": "..."}]
    error: Optional[str] = None


# ==================== CORE ORCHESTRATION LOGIC ====================

async def get_user_context(user_id: str) -> Dict[str, Any]:
    """Fetch full user context from Context Service"""
    try:
        response = http_client.get(f"{CONTEXT_SERVICE_URL}/api/context/{user_id}")
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get context for user {user_id}: {e}")
        return {
            "profile": {"user_id": user_id, "timezone": "UTC", "language": "ru"},
            "conversation_history": [],
            "session_state": {"current_state": "idle", "context": {}},
            "active_goals": [],
            "upcoming_events": []
        }


async def parse_message(message: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Parse user message via LLM Service"""
    try:
        response = http_client.post(
            f"{LLM_SERVICE_URL}/api/parse",
            json={"message": message, "context": context}
        )

        # Check if LLM service returned error
        if response.status_code != 200:
            logger.error(f"LLM service error {response.status_code}: {response.text}")
            return {"intent": None, "error": response.text}

        return response.json()
    except Exception as e:
        logger.error(f"Failed to parse message: {e}")
        return {"intent": None, "error": str(e)}


async def execute_intent(intent: str, params: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Execute intent via Core Service"""

    # Map intent to Core Service endpoint
    if intent.startswith("event."):
        endpoint = "/api/events"
        action = intent.split(".")[1]  # search, create, update, delete, mutate

        # Adapter: event.mutate → event.create/update/delete
        if action == "mutate":
            operation = params.get("operation", "create")

            if operation == "create":
                # Extract new_* fields for creation
                create_params = {
                    "title": params.get("new_title") or params.get("title"),
                    "date": params.get("new_start_date") or params.get("start_date"),
                    "time": params.get("new_time"),
                    "repeat": params.get("new_repeat"),
                    "notes": params.get("new_notes"),
                }
                # Remove None values
                create_params = {k: v for k, v in create_params.items() if v is not None}
                response = http_client.post(f"{CORE_SERVICE_URL}{endpoint}", json={**create_params, "user_id": user_id})
                return response.json()

            elif operation in ["update", "delete"]:
                # First, search for event(s) matching the selector
                search_params = {
                    "user_id": user_id,
                    "title": params.get("title"),
                    "start_date": params.get("start_date"),
                    "end_date": params.get("end_date"),
                    "time": params.get("time"),
                }
                # Remove None values
                search_params = {k: v for k, v in search_params.items() if v is not None}

                search_response = http_client.get(f"{CORE_SERVICE_URL}{endpoint}", params=search_params)
                found_events = search_response.json()

                if not found_events:
                    return {"success": False, "error": "Событие не найдено"}

                if len(found_events) > 1:
                    return {"success": False, "error": f"Найдено {len(found_events)} событий. Уточните, какое именно."}

                event_id = found_events[0]["id"]

                if operation == "delete":
                    http_client.delete(f"{CORE_SERVICE_URL}{endpoint}/{event_id}")
                    return {"success": True, "deleted": found_events[0]}

                elif operation == "update":
                    # Update with new_* fields, but only time (not date!)
                    update_params = {}
                    if params.get("new_title"):
                        update_params["title"] = params["new_title"]
                    if params.get("new_time"):
                        update_params["time"] = params["new_time"]
                    if params.get("new_notes"):
                        update_params["notes"] = params["new_notes"]
                    # Only update date if it's actually different
                    if params.get("new_start_date") and params["new_start_date"] != found_events[0]["date"]:
                        update_params["date"] = params["new_start_date"]

                    if not update_params:
                        return {"success": False, "error": "Нет данных для обновления"}

                    response = http_client.put(
                        f"{CORE_SERVICE_URL}{endpoint}/{event_id}",
                        params={"user_id": user_id},
                        json=update_params
                    )
                    return response.json()
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}

        if action == "search":
            # GET with query params
            query_params = {k: v for k, v in params.items() if v is not None}
            query_params["user_id"] = user_id
            response = http_client.get(f"{CORE_SERVICE_URL}{endpoint}", params=query_params)
            return response.json()
        elif action == "create":
            response = http_client.post(f"{CORE_SERVICE_URL}{endpoint}", json={**params, "user_id": user_id})
            return response.json()
        elif action == "update":
            event_id = params.pop("id", None)
            if not event_id:
                return {"success": False, "error": "Event ID required for update"}
            response = http_client.put(f"{CORE_SERVICE_URL}{endpoint}/{event_id}", json=params)
            return response.json()
        elif action == "delete":
            event_id = params.get("id")
            if not event_id:
                return {"success": False, "error": "Event ID required for delete"}
            response = http_client.delete(f"{CORE_SERVICE_URL}{endpoint}/{event_id}")
            return response.json() if response.status_code != 204 else {"success": True}
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    elif intent.startswith("goal."):
        endpoint = "/api/goals"
        action = intent.split(".")[1]

        if action == "search":
            response = http_client.get(f"{CORE_SERVICE_URL}{endpoint}", params={"user_id": user_id})
            return response.json()
        elif action == "create":
            # Map goal_title → title for Core Service
            create_params = {
                "title": params.get("goal_title") or params.get("title"),
                "description": params.get("description"),
                "target_date": params.get("target_date"),
                "status": "active",
                "user_id": user_id
            }
            # Remove None values
            create_params = {k: v for k, v in create_params.items() if v is not None}
            response = http_client.post(f"{CORE_SERVICE_URL}{endpoint}", json=create_params)
            goal = response.json()

            # Auto-generate steps via LLM
            try:
                logger.info(f"[{user_id}] Generating steps for goal: {create_params['title']}")
                steps_response = http_client.post(
                    f"{LLM_SERVICE_URL}/api/generate-steps",
                    json={
                        "goal_title": create_params["title"],
                        "current_level": params.get("current_level") or "начинающий",
                        "time_commitment": params.get("time_commitment") or "1-2 часа в день",
                        "additional_context": params.get("description")
                    }
                )
                generated_steps = steps_response.json()
                logger.info(f"[{user_id}] Generated {len(generated_steps)} steps")

                # Save steps to Core Service
                for i, step_data in enumerate(generated_steps, 1):
                    logger.info(f"[{user_id}] Saving step {i}: {step_data['title'][:50]}...")
                    step_response = http_client.post(
                        f"{CORE_SERVICE_URL}{endpoint}/{goal['id']}/steps",
                        params={"user_id": user_id},
                        json={
                            "title": step_data["title"],
                            "order": i,
                            "estimated_hours": step_data.get("estimated_hours", 2.0)
                        }
                    )
                    logger.info(f"[{user_id}] Step {i} saved: {step_response.status_code}")
                    if step_response.status_code != 201:
                        logger.error(f"[{user_id}] Failed to save step {i}: {step_response.text}")

                # Fetch updated goal with steps
                logger.info(f"[{user_id}] Fetching updated goal...")
                updated_goal = http_client.get(f"{CORE_SERVICE_URL}{endpoint}/{goal['id']}", params={"user_id": user_id})
                final_goal = updated_goal.json()
                logger.info(f"[{user_id}] Final goal has {len(final_goal.get('steps', []))} steps")
                return final_goal
            except Exception as e:
                logger.exception(f"[{user_id}] Failed to generate/save steps")
                # Return goal without steps if generation fails
                return goal
        elif action == "update":
            goal_id = params.pop("id", None)
            if not goal_id:
                return {"success": False, "error": "Goal ID required"}
            response = http_client.put(f"{CORE_SERVICE_URL}{endpoint}/{goal_id}", json=params)
            return response.json()
        elif action == "delete":
            # Find goal by title
            goal_title = params.get("goal_title")
            search_response = http_client.get(f"{CORE_SERVICE_URL}{endpoint}", params={"user_id": user_id})
            goals = search_response.json()

            # Find matching goal
            matching_goal = None
            if goal_title:
                for goal in goals:
                    if goal_title.lower() in goal["title"].lower():
                        matching_goal = goal
                        break
            elif len(goals) == 1:
                matching_goal = goals[0]

            if not matching_goal:
                return {"success": False, "error": "Цель не найдена"}

            # Delete goal
            response = http_client.delete(
                f"{CORE_SERVICE_URL}{endpoint}/{matching_goal['id']}",
                params={"user_id": user_id}
            )

            if response.status_code == 204 or response.status_code == 200:
                return {
                    "success": True,
                    "message": f"Цель '{matching_goal['title']}' удалена",
                    "deleted_goal": matching_goal
                }
            else:
                return {"success": False, "error": "Не удалось удалить цель"}
        elif action == "update_step":
            # Find goal by title
            goal_title = params.get("goal_title")
            search_response = http_client.get(f"{CORE_SERVICE_URL}{endpoint}", params={"user_id": user_id})
            goals = search_response.json()

            # Find matching goal
            matching_goal = None
            if goal_title:
                for goal in goals:
                    if goal_title.lower() in goal["title"].lower():
                        matching_goal = goal
                        break
            elif len(goals) == 1:
                matching_goal = goals[0]

            if not matching_goal:
                return {"success": False, "error": "Цель не найдена"}

            if not matching_goal.get("steps"):
                return {"success": False, "error": "У цели нет шагов"}

            # Find step by number or title
            step_number = params.get("step_number")
            step_title = params.get("step_title")
            target_step = None

            if step_number and 1 <= step_number <= len(matching_goal["steps"]):
                target_step = matching_goal["steps"][step_number - 1]
            elif step_title:
                for step in matching_goal["steps"]:
                    if step_title.lower() in step["title"].lower():
                        target_step = step
                        break

            if not target_step:
                return {"success": False, "error": "Шаг не найден"}

            # Update step status or title
            new_status = params.get("new_status")
            new_title = params.get("new_title")

            if new_status:
                # Update status
                http_client.put(
                    f"{CORE_SERVICE_URL}/api/steps/{target_step['id']}/status",
                    json={"status": new_status, "user_id": user_id}
                )

            if new_title:
                # Update title
                http_client.put(
                    f"{CORE_SERVICE_URL}/api/steps/{target_step['id']}",
                    params={"user_id": user_id},
                    json={"title": new_title}
                )

            # Return updated goal
            updated_goal = http_client.get(f"{CORE_SERVICE_URL}{endpoint}/{matching_goal['id']}", params={"user_id": user_id})
            return updated_goal.json()
        elif action == "add_step":
            # Find goal by title
            goal_title = params.get("goal_title")
            search_response = http_client.get(f"{CORE_SERVICE_URL}{endpoint}", params={"user_id": user_id})
            goals = search_response.json()

            # Find matching goal
            matching_goal = None
            if goal_title:
                for goal in goals:
                    if goal_title.lower() in goal["title"].lower():
                        matching_goal = goal
                        break
            elif len(goals) == 1:
                matching_goal = goals[0]

            if not matching_goal:
                return {"success": False, "error": "Цель не найдена"}

            # Add step
            step_title = params.get("step_title")
            estimated_hours = params.get("estimated_hours")

            response = http_client.post(
                f"{CORE_SERVICE_URL}{endpoint}/{matching_goal['id']}/steps",
                params={"user_id": user_id},
                json={
                    "title": step_title,
                    "order": len(matching_goal.get("steps", [])),
                    "estimated_hours": estimated_hours
                }
            )

            if response.status_code != 201:
                return {"success": False, "error": "Не удалось добавить шаг"}

            # Return updated goal
            updated_goal = http_client.get(f"{CORE_SERVICE_URL}{endpoint}/{matching_goal['id']}", params={"user_id": user_id})
            return updated_goal.json()
        elif action == "delete_step":
            # Find goal by title
            goal_title = params.get("goal_title")
            search_response = http_client.get(f"{CORE_SERVICE_URL}{endpoint}", params={"user_id": user_id})
            goals = search_response.json()

            # Find matching goal
            matching_goal = None
            if goal_title:
                for goal in goals:
                    if goal_title.lower() in goal["title"].lower():
                        matching_goal = goal
                        break
            elif len(goals) == 1:
                matching_goal = goals[0]

            if not matching_goal:
                return {"success": False, "error": "Цель не найдена"}

            if not matching_goal.get("steps"):
                return {"success": False, "error": "У цели нет шагов"}

            # Find step by number or title
            step_number = params.get("step_number")
            step_title = params.get("step_title")
            target_step = None

            if step_number and 1 <= step_number <= len(matching_goal["steps"]):
                target_step = matching_goal["steps"][step_number - 1]
            elif step_title:
                for step in matching_goal["steps"]:
                    if step_title.lower() in step["title"].lower():
                        target_step = step
                        break

            if not target_step:
                return {"success": False, "error": "Шаг не найден"}

            # Delete step
            response = http_client.delete(
                f"{CORE_SERVICE_URL}/api/steps/{target_step['id']}",
                params={"user_id": user_id}
            )

            if response.status_code not in [200, 204]:
                return {"success": False, "error": "Не удалось удалить шаг"}

            # Return updated goal
            updated_goal = http_client.get(f"{CORE_SERVICE_URL}{endpoint}/{matching_goal['id']}", params={"user_id": user_id})
            return updated_goal.json()
        elif action == "query":
            # Show progress for specific goal
            goal_title = params.get("goal_title")
            search_response = http_client.get(f"{CORE_SERVICE_URL}{endpoint}", params={"user_id": user_id})
            goals = search_response.json()

            if goal_title:
                for goal in goals:
                    if goal_title.lower() in goal["title"].lower():
                        return goal
                return {"success": False, "error": "Цель не найдена"}
            else:
                # Return all goals if no specific title
                return goals
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    elif intent.startswith("product."):
        endpoint = "/api/products"
        action = intent.split(".")[1]

        if action == "search":
            response = http_client.get(f"{CORE_SERVICE_URL}{endpoint}", params={**params, "user_id": user_id})
            return response.json()
        elif action == "add_to_cart":
            response = http_client.post(f"{CORE_SERVICE_URL}/api/cart", json={**params, "user_id": user_id})
            return response.json()
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    elif intent == "small_talk":
        # Handle via LLM chat endpoint
        try:
            response = http_client.post(
                f"{LLM_SERVICE_URL}/api/chat",
                json={"message": params.get("original_message", "")}
            )
            return {"success": True, "response": response.json().get("response", "")}
        except Exception as e:
            logger.error(f"Small talk failed: {e}")
            return {"success": False, "error": str(e)}
    else:
        return {"success": False, "error": f"Unknown intent: {intent}"}


async def summarize_result(core_result: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize Core result via LLM Service"""
    try:
        response = http_client.post(
            f"{LLM_SERVICE_URL}/api/summarize",
            json={"core_result": core_result}
        )
        return response.json()
    except Exception as e:
        logger.error(f"Failed to summarize result: {e}")
        # Fallback to simple text response
        return {
            "intent": "final_text",
            "text": "Выполнено"
        }


async def update_conversation(user_id: str, role: str, content: str):
    """Add message to conversation history"""
    try:
        http_client.post(
            f"{CONTEXT_SERVICE_URL}/api/conversation/{user_id}/messages",
            json={"role": role, "content": content}
        )
    except Exception as e:
        logger.error(f"Failed to update conversation: {e}")


async def update_session_state(user_id: str, state: str, context: Dict[str, Any]):
    """Update session state in Context Service"""
    try:
        expiry_hours = StateMachine.get_context_expiry(state)
        http_client.put(
            f"{CONTEXT_SERVICE_URL}/api/session/{user_id}",
            json={
                "current_state": state,
                "context": context,
                "expiry_hours": expiry_hours
            }
        )
    except Exception as e:
        logger.error(f"Failed to update session state: {e}")


# ==================== MAIN ENDPOINT ====================

async def handle_scheduling_flow(user_id: str, message: str, current_state: str, session_context: Dict[str, Any]) -> Optional[ProcessMessageResponse]:
    """
    Handle scheduling flow states
    Returns ProcessMessageResponse if handled, None otherwise
    """
    from datetime import datetime, timedelta
    import re

    # GOAL_DEADLINE_REQUEST - User needs to provide deadline
    if current_state == DialogState.GOAL_DEADLINE_REQUEST:
        # Parse deadline from message
        deadline = None
        try:
            # Try to parse date from message
            # Simple patterns: "через N дней/недель/месяцев", "15 декабря", "2025-12-15"
            message_lower = message.lower()

            if "через" in message_lower:
                # Try to extract number, default to 1 if not found
                number_match = re.search(r'\d+', message)
                number = int(number_match.group()) if number_match else 1

                if "день" in message_lower or "дня" in message_lower or "дней" in message_lower:
                    deadline = (datetime.now() + timedelta(days=number)).date().isoformat()
                elif "недел" in message_lower:
                    deadline = (datetime.now() + timedelta(weeks=number)).date().isoformat()
                elif "месяц" in message_lower:
                    deadline = (datetime.now() + timedelta(days=number*30)).date().isoformat()
            else:
                # Try to parse absolute date
                from dateutil import parser as dtparser
                parsed_date = dtparser.parse(message, fuzzy=True)
                deadline = parsed_date.date().isoformat()
        except:
            logger.warning(f"[{user_id}] Could not parse deadline from: {message}")

        if not deadline:
            return ProcessMessageResponse(
                success=True,
                response_type="clarification",
                text="Не могу понять дату. Попробуй указать конкретнее, например: 'через 2 недели', '15 декабря' или '2025-12-15'"
            )

        goal_id = session_context.get("goal_id")
        if not goal_id:
            logger.error(f"[{user_id}] No goal_id in session context")
            await update_session_state(user_id, DialogState.IDLE, {})
            return ProcessMessageResponse(
                success=False,
                response_type="text",
                text="Произошла ошибка. Давай начнём заново."
            )

        # Update goal with deadline in database
        try:
            update_response = http_client.patch(
                f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
                params={"user_id": user_id},
                json={"target_date": deadline}
            )
            if update_response.status_code != 200:
                logger.error(f"[{user_id}] Failed to update goal deadline: {update_response.status_code}")
        except Exception as e:
            logger.exception(f"[{user_id}] Error updating goal deadline: {e}")

        # Check feasibility
        try:
            feasibility_response = http_client.post(
                f"{CORE_SERVICE_URL}/api/goals/{goal_id}/check-feasibility",
                json={
                    "user_id": user_id,
                    "deadline": deadline
                }
            )
            feasibility = feasibility_response.json()

            # Update session context with deadline and feasibility
            new_context = {
                **session_context,
                "deadline": deadline,
                "feasibility": feasibility
            }

            # Transition to GOAL_SCHEDULE_OFFER
            await update_session_state(user_id, DialogState.GOAL_SCHEDULE_OFFER, new_context)

            if feasibility.get("feasible"):
                text = f"Отлично! Дедлайн: {deadline}\n\n"
                text += "Хочешь, чтобы я запланировал эти шаги в твоём календаре? Я учту твои занятые слоты и распределю задачи равномерно. 📅"
                return ProcessMessageResponse(
                    success=True,
                    response_type="inline_buttons",
                    text=text,
                    buttons=[
                        {"text": "✅ Да, запланировать", "callback": f"schedule_accept:{goal_id}"},
                        {"text": "❌ Нет, сам разберусь", "callback": f"schedule_decline:{goal_id}"}
                    ]
                )
            else:
                required = feasibility.get("required_hours", 0)
                available = feasibility.get("available_hours", 0)
                suggested = feasibility.get("suggested_deadline")
                text = f"⚠️ К сожалению, до {deadline} может не хватить времени.\n\n"
                text += f"Для цели нужно: {required:.1f}ч\n"
                text += f"Доступно в календаре: {available:.1f}ч\n\n"
                if suggested:
                    text += f"Рекомендую перенести дедлайн на {suggested}.\n\n"
                text += "Всё равно попробовать запланировать?"
                return ProcessMessageResponse(
                    success=True,
                    response_type="inline_buttons",
                    text=text,
                    buttons=[
                        {"text": "✅ Да, попробуем", "callback": f"schedule_accept:{goal_id}"},
                        {"text": "❌ Нет, спасибо", "callback": f"schedule_decline:{goal_id}"}
                    ]
                )
        except Exception as e:
            logger.exception(f"[{user_id}] Error checking feasibility")
            await update_session_state(user_id, DialogState.IDLE, {})
            return ProcessMessageResponse(
                success=False,
                response_type="text",
                text="Произошла ошибка при проверке расписания. Попробуем позже?"
            )

    return None


@app.post("/api/process", response_model=ProcessMessageResponse)
async def process_message(request: ProcessMessageRequest):
    """
    Main orchestration endpoint:
    1. Load user context
    2. Parse message via LLM (with state awareness)
    3. Check state transitions
    4. Execute via Core Service
    5. Update conversation history
    6. Update session state if needed
    7. Summarize result via LLM
    8. Return formatted response
    """
    user_id = request.user_id
    message = request.message

    try:
        # Step 1: Get full context
        logger.info(f"[{user_id}] Processing message: {message[:50]}...")
        context = await get_user_context(user_id)
        current_state = context["session_state"]["current_state"]
        session_context = context["session_state"]["context"]

        logger.info(f"[{user_id}] Current state: {current_state}")

        # Handle goal clarification state - user provides goal title
        if current_state == "goal_clarification":
            logger.info(f"[{user_id}] Received goal title: {message}")

            # Transition to time commitment question
            await update_session_state(user_id, DialogState.GOAL_TIME_COMMITMENT, {
                "goal_title": message.strip()
            })

            # Ask about time commitment
            time_text = (
                f"👍 Отлично! Цель: <b>{message.strip()}</b>\n\n"
                "⏰ Сколько времени в день ты готов выделять на достижение этой цели?\n\n"
                "Например:\n"
                "• 30 минут\n"
                "• 1 час\n"
                "• 2 часа"
            )

            await update_conversation(user_id, "user", message)
            await update_conversation(user_id, "assistant", time_text)

            return ProcessMessageResponse(
                success=True,
                response_type="text",
                text=time_text
            )

        # Handle goal time commitment state - user provides time commitment
        if current_state == "goal_time_commitment":
            logger.info(f"[{user_id}] Received time commitment: {message}")

            goal_title = session_context.get("goal_title", "")
            if not goal_title:
                error_text = "Ошибка: название цели не найдено. Начни заново с /start"
                await update_session_state(user_id, DialogState.IDLE, {})
                return ProcessMessageResponse(
                    success=False,
                    response_type="text",
                    text=error_text
                )

            # Parse time commitment (simple parsing)
            import re
            time_commitment = message.strip()

            # Generate steps using LLM
            try:
                logger.info(f"[{user_id}] Generating steps for goal: {goal_title}, time: {time_commitment}")

                # Call LLM to generate steps
                llm_response = http_client.post(
                    f"{LLM_SERVICE_URL}/api/generate-steps",
                    json={
                        "goal_title": goal_title,
                        "time_commitment": time_commitment,
                        "additional_context": f"Пользователь готов выделять {time_commitment} в день"
                    }
                )

                if llm_response.status_code != 200:
                    raise Exception("Failed to generate steps")

                generated_steps = llm_response.json()
                logger.info(f"[{user_id}] Generated {len(generated_steps)} steps")

                # Add order field to each step
                for i, step in enumerate(generated_steps, 1):
                    step["order"] = i

                # Create goal with generated steps
                response = http_client.post(
                    f"{CORE_SERVICE_URL}/api/goals",
                    json={
                        "user_id": user_id,
                        "title": goal_title,
                        "description": f"Время в день: {time_commitment}",
                        "status": "active",
                        "steps": generated_steps
                    }
                )

                if response.status_code != 201:
                    logger.error(f"[{user_id}] Failed to create goal: {response.status_code}, {response.text}")
                    raise Exception(f"Failed to create goal: {response.text}")

                core_result = response.json()

                if core_result.get("id"):
                    # Goal created successfully, now analyze SMART
                    logger.info(f"[{user_id}] Goal created with ID: {core_result['id']}")

                    # Analyze goal with SMART criteria
                    smart_analysis = None
                    try:
                        logger.info(f"[{user_id}] Analyzing SMART for goal: {goal_title}")
                        smart_response = http_client.post(
                            f"{LLM_SERVICE_URL}/api/analyze-smart",
                            json={
                                "goal_title": goal_title,
                                "description": core_result.get("description"),
                                "target_date": core_result.get("target_date"),
                                "steps": core_result.get("steps", [])
                            }
                        )

                        if smart_response.status_code == 200:
                            smart_analysis = smart_response.json()
                            logger.info(f"[{user_id}] SMART score: {smart_analysis.get('overall_score')}/10, is_smart: {smart_analysis.get('is_smart')}")
                        else:
                            logger.warning(f"[{user_id}] SMART analysis failed: {smart_response.status_code}")
                    except Exception as e:
                        logger.error(f"[{user_id}] Error analyzing SMART: {e}")
                        # Continue without SMART analysis if it fails

                    # Update session state with SMART analysis
                    await update_session_state(user_id, DialogState.GOAL_DEADLINE_REQUEST, {
                        "goal_id": core_result["id"],
                        "goal_title": core_result.get("title", ""),
                        "time_commitment": time_commitment,
                        "smart_analysis": smart_analysis
                    })

                    # Build response with SMART feedback
                    goal_text = f"🎯 Отлично! Я создал цель: <b>{core_result.get('title')}</b>\n\n"
                    steps = core_result.get("steps", [])
                    if steps:
                        goal_text += f"📋 Создано {len(steps)} шагов:\n"
                        for i, step in enumerate(steps[:3], 1):
                            goal_text += f"{i}. {step['title']}\n"
                        if len(steps) > 3:
                            goal_text += f"... и ещё {len(steps) - 3}\n"
                        goal_text += "\n"

                    # Add SMART analysis feedback
                    if smart_analysis:
                        goal_text += f"📊 <b>SMART-анализ</b> (оценка: {smart_analysis.get('overall_score', 0)}/10)\n\n"

                        criteria = smart_analysis.get("criteria", {})
                        for key, data in criteria.items():
                            emoji = "✅" if data.get("passed") else "⚠️"
                            goal_text += f"{emoji} <b>{key.upper()}</b>: {data.get('feedback', '')}\n"

                        goal_text += f"\n💬 {smart_analysis.get('motivational_message', '')}\n\n"

                    goal_text += "📅 <b>Когда ты хочешь достичь этой цели?</b>\n"
                    goal_text += "Укажи дедлайн, например:\n"
                    goal_text += "• 'через 2 недели'\n"
                    goal_text += "• '15 декабря'\n"
                    goal_text += "• '2025-12-15'"

                    # Add button to edit goal if not SMART
                    buttons = None
                    if smart_analysis and not smart_analysis.get("is_smart"):
                        buttons = [
                            [{"text": "✏️ Изменить постановку цели", "callback_data": f"edit_goal_{core_result['id']}"}],
                            [{"text": "➡️ Продолжить с текущей целью", "callback_data": "continue_goal"}]
                        ]

                    # Update conversation
                    await update_conversation(user_id, "user", message)
                    await update_conversation(user_id, "assistant", goal_text)

                    return ProcessMessageResponse(
                        success=True,
                        response_type="text",
                        text=goal_text,
                        buttons=buttons
                    )
                else:
                    # Goal creation failed
                    error_text = "Не удалось создать цель. Попробуй еще раз."
                    await update_conversation(user_id, "user", message)
                    await update_conversation(user_id, "assistant", error_text)
                    await update_session_state(user_id, DialogState.IDLE, {})
                    return ProcessMessageResponse(
                        success=False,
                        response_type="text",
                        text=error_text
                    )
            except Exception as e:
                logger.error(f"[{user_id}] Error creating goal: {e}")
                error_text = "Произошла ошибка при создании цели. Попробуй еще раз."
                await update_conversation(user_id, "user", message)
                await update_conversation(user_id, "assistant", error_text)
                await update_session_state(user_id, DialogState.IDLE, {})
                return ProcessMessageResponse(
                    success=False,
                    response_type="text",
                    text=error_text
                )

        # Handle goal editing state - user provides new goal formulation
        if current_state == "goal_editing":
            logger.info(f"[{user_id}] Received new goal formulation: {message}")

            goal_id = session_context.get("goal_id")
            if not goal_id:
                error_text = "Ошибка: цель не найдена. Начни заново с /start"
                await update_session_state(user_id, DialogState.IDLE, {})
                return ProcessMessageResponse(
                    success=False,
                    response_type="text",
                    text=error_text
                )

            new_title = message.strip()

            try:
                # Update goal title
                logger.info(f"[{user_id}] Updating goal {goal_id} with new title: {new_title}")

                response = http_client.put(
                    f"{CORE_SERVICE_URL}/api/goals/{goal_id}",
                    json={
                        "user_id": user_id,
                        "title": new_title
                    }
                )

                if response.status_code != 200:
                    raise Exception(f"Failed to update goal: {response.text}")

                updated_goal = response.json()

                # Re-analyze with SMART
                logger.info(f"[{user_id}] Re-analyzing SMART for updated goal")
                smart_response = http_client.post(
                    f"{LLM_SERVICE_URL}/api/analyze-smart",
                    json={
                        "goal_title": new_title,
                        "description": updated_goal.get("description"),
                        "target_date": updated_goal.get("target_date"),
                        "steps": updated_goal.get("steps", [])
                    }
                )

                if smart_response.status_code != 200:
                    raise Exception("Failed to analyze SMART")

                smart_analysis = smart_response.json()
                logger.info(f"[{user_id}] SMART score: {smart_analysis.get('overall_score')}/10, is_smart: {smart_analysis.get('is_smart')}")

                # Build response with SMART feedback
                goal_text = f"✏️ <b>Цель обновлена!</b>\n\n"
                goal_text += f"🎯 Новая формулировка: <b>{new_title}</b>\n\n"

                goal_text += f"📊 <b>SMART-анализ</b> (оценка: {smart_analysis.get('overall_score', 0)}/10)\n\n"

                criteria = smart_analysis.get("criteria", {})
                for key, data in criteria.items():
                    emoji = "✅" if data.get("passed") else "⚠️"
                    goal_text += f"{emoji} <b>{key.upper()}</b>: {data.get('feedback', '')}\n"

                goal_text += f"\n💬 {smart_analysis.get('motivational_message', '')}\n\n"

                # Check if goal is now SMART
                if smart_analysis.get("is_smart"):
                    # Goal is SMART, proceed to deadline request
                    await update_session_state(user_id, DialogState.GOAL_DEADLINE_REQUEST, {
                        "goal_id": goal_id,
                        "goal_title": new_title,
                        "smart_analysis": smart_analysis
                    })

                    goal_text += "📅 <b>Теперь укажи дедлайн для достижения цели.</b>\n"
                    goal_text += "Например:\n"
                    goal_text += "• 'через 2 недели'\n"
                    goal_text += "• '15 декабря'\n"
                    goal_text += "• '2025-12-15'"

                    buttons = None
                else:
                    # Still not SMART, offer to edit again
                    await update_session_state(user_id, "goal_editing", {
                        "goal_id": goal_id,
                        "smart_analysis": smart_analysis
                    })

                    goal_text += "💡 <b>Цель можно улучшить.</b> Попробуй снова или продолжи с текущей формулировкой."

                    buttons = [
                        [{"text": "✏️ Улучшить формулировку", "callback_data": f"edit_goal_{goal_id}"}],
                        [{"text": "➡️ Продолжить с текущей целью", "callback_data": "continue_to_deadline"}]
                    ]

                await update_conversation(user_id, "user", message)
                await update_conversation(user_id, "assistant", goal_text)

                return ProcessMessageResponse(
                    success=True,
                    response_type="text",
                    text=goal_text,
                    buttons=buttons
                )

            except Exception as e:
                logger.error(f"[{user_id}] Error updating goal: {e}")
                error_text = "Произошла ошибка при обновлении цели. Попробуй еще раз."
                return ProcessMessageResponse(
                    success=False,
                    response_type="text",
                    text=error_text
                )

        # Handle scheduling flow states first
        scheduling_response = await handle_scheduling_flow(user_id, message, current_state, session_context)
        if scheduling_response:
            await update_conversation(user_id, "user", message)
            await update_conversation(user_id, "assistant", scheduling_response.text)
            return scheduling_response

        # Step 2: Parse message
        parsed = await parse_message(message, context)
        intent = parsed.get("intent")
        # LLM returns all fields in root object, not in "params"
        params = {k: v for k, v in parsed.items() if k not in ["intent", "text"]}

        logger.info(f"[{user_id}] Parsed intent: {intent}, params: {params}")

        # If LLM parsing failed, return error
        if not intent:
            logger.error(f"[{user_id}] No intent parsed from LLM. Response: {parsed}")
            return ProcessMessageResponse(
                success=False,
                response_type="text",
                text="Извини, не могу понять запрос. Попробуй переформулировать.",
                error="LLM parsing failed"
            )

        # Step 3: Handle small_talk immediately
        if intent == "small_talk":
            text = parsed.get("text", "")
            await update_conversation(user_id, "user", message)
            await update_conversation(user_id, "assistant", text)
            return ProcessMessageResponse(
                success=True,
                response_type="text",
                text=text
            )

        # Step 4: Execute intent via Core
        core_result = await execute_intent(intent, params, user_id)
        logger.info(f"[{user_id}] Core result: {core_result}")

        # Track intent execution
        track_event(user_id, "Intent Executed", {
            "intent": intent,
            "success": core_result.get("success", True) if isinstance(core_result, dict) else True,
            "state": current_state
        })

        # Step 5: Check state transitions
        new_state = StateMachine.should_transition(current_state, intent, {**session_context, **params})

        # Special handling for goal.create - transition to deadline request
        if intent == "goal.create" and isinstance(core_result, dict) and core_result.get("id"):
            logger.info(f"[{user_id}] Goal created, transitioning to deadline request")
            new_state = DialogState.GOAL_DEADLINE_REQUEST
            new_context = {
                "goal_id": core_result["id"],
                "goal_title": core_result.get("title", "")
            }
            await update_session_state(user_id, new_state, new_context)

            # Return special response asking for deadline
            await update_conversation(user_id, "user", message)

            # Build goal summary text (HTML formatting for Telegram)
            goal_text = f"🎯 Отлично! Я создал цель: <b>{core_result.get('title')}</b>\n\n"
            steps = core_result.get("steps", [])
            if steps:
                goal_text += f"📋 Создано {len(steps)} шагов:\n"
                for i, step in enumerate(steps[:3], 1):
                    goal_text += f"{i}. {step['title']}\n"
                if len(steps) > 3:
                    goal_text += f"... и ещё {len(steps) - 3}\n"
                goal_text += "\n"

            goal_text += "📅 <b>Когда ты хочешь достичь этой цели?</b>\n"
            goal_text += "Укажи дедлайн, например:\n"
            goal_text += "• 'через 2 недели'\n"
            goal_text += "• '15 декабря'\n"
            goal_text += "• '2025-12-15'"

            await update_conversation(user_id, "assistant", goal_text)

            return ProcessMessageResponse(
                success=True,
                response_type="text",
                text=goal_text
            )
        elif new_state:
            logger.info(f"[{user_id}] State transition: {current_state} -> {new_state}")
            await update_session_state(user_id, new_state, {**session_context, **params})
        elif current_state != DialogState.IDLE:
            # Reset to idle if no transition and not already idle
            await update_session_state(user_id, DialogState.IDLE, {})

        # Step 6: Summarize result
        # Wrap result for better LLM understanding
        result_wrapper = {
            "intent": intent,
            "data": core_result,
            "is_list": isinstance(core_result, list),
            "count": len(core_result) if isinstance(core_result, list) else None
        }
        summary = await summarize_result(result_wrapper)
        response_type = summary.get("intent", "final_text")

        # Step 7: Update conversation history
        await update_conversation(user_id, "user", message)
        if summary.get("text"):
            await update_conversation(user_id, "assistant", summary["text"])

        # Step 8: Format response
        if response_type == "render_table":
            return ProcessMessageResponse(
                success=True,
                response_type="table",
                text=summary.get("text"),
                items=summary.get("items"),
                set_id=summary.get("set_id")
            )
        elif response_type == "ask_clarification":
            return ProcessMessageResponse(
                success=True,
                response_type="clarification",
                text=summary.get("text")
            )
        else:
            return ProcessMessageResponse(
                success=True,
                response_type="text",
                text=summary.get("text", "Готово!")
            )

    except Exception as e:
        logger.exception(f"[{user_id}] Error processing message")
        return ProcessMessageResponse(
            success=False,
            response_type="text",
            text="Упс, произошла ошибка. Попробуй ещё раз.",
            error=str(e)
        )


# ==================== CALLBACK ENDPOINT ====================

class ProcessCallbackRequest(BaseModel):
    user_id: str
    callback_data: str


@app.post("/api/callback", response_model=ProcessMessageResponse)
async def process_callback(request: ProcessCallbackRequest):
    """
    Handle inline button callbacks from Telegram
    Format: action:param1:param2
    """
    user_id = request.user_id
    callback_data = request.callback_data

    try:
        logger.info(f"[{user_id}] Processing callback: {callback_data}")
        parts = callback_data.split(":")
        action = parts[0]

        context = await get_user_context(user_id)
        current_state = context["session_state"]["current_state"]
        session_context = context["session_state"]["context"]

        # Handle schedule_accept
        if action == "schedule_accept":
            goal_id = int(parts[1])
            logger.info(f"[{user_id}] User accepted scheduling for goal {goal_id}")

            # Update session context
            new_context = {
                **session_context,
                "schedule_accepted": True
            }
            await update_session_state(user_id, DialogState.GOAL_SCHEDULE_TIME_PREF, new_context)

            text = "⏰ <b>Когда тебе удобнее работать над целью?</b>\n(можно выбрать несколько)"
            buttons = [
                {"text": "🌅 Утро (9-12)", "callback": f"time_pref:morning:{goal_id}"},
                {"text": "☀️ День (12-18)", "callback": f"time_pref:afternoon:{goal_id}"},
                {"text": "🌙 Вечер (18-22)", "callback": f"time_pref:evening:{goal_id}"},
                {"text": "✅ Готово", "callback": f"time_pref_done:{goal_id}"}
            ]

            return ProcessMessageResponse(
                success=True,
                response_type="inline_buttons",
                text=text,
                buttons=buttons
            )

        # Handle schedule_decline
        elif action == "schedule_decline":
            goal_id = int(parts[1])
            logger.info(f"[{user_id}] User declined scheduling for goal {goal_id}")
            await update_session_state(user_id, DialogState.IDLE, {})

            return ProcessMessageResponse(
                success=True,
                response_type="text",
                text="Хорошо! Ты можешь планировать шаги вручную. Если передумаешь - просто напиши! 👍"
            )

        # Handle time_pref selection
        elif action == "time_pref":
            time_slot = parts[1]  # morning, afternoon, evening
            goal_id = int(parts[2])

            # Get current preferences
            preferred_times = session_context.get("preferred_times", [])
            if time_slot in preferred_times:
                preferred_times.remove(time_slot)
            else:
                preferred_times.append(time_slot)

            new_context = {
                **session_context,
                "preferred_times": preferred_times
            }
            await update_session_state(user_id, DialogState.GOAL_SCHEDULE_TIME_PREF, new_context)

            # Show updated selection
            time_names = {
                "morning": "🌅 Утро",
                "afternoon": "☀️ День",
                "evening": "🌙 Вечер"
            }
            selected = ", ".join([time_names[t] for t in preferred_times]) if preferred_times else "не выбрано"
            text = f"⏰ <b>Когда тебе удобнее работать над целью?</b>\n(можно выбрать несколько)\n\nВыбрано: {selected}"

            buttons = [
                {"text": f"{'✅ ' if 'morning' in preferred_times else ''}🌅 Утро (9-12)", "callback": f"time_pref:morning:{goal_id}"},
                {"text": f"{'✅ ' if 'afternoon' in preferred_times else ''}☀️ День (12-18)", "callback": f"time_pref:afternoon:{goal_id}"},
                {"text": f"{'✅ ' if 'evening' in preferred_times else ''}🌙 Вечер (18-22)", "callback": f"time_pref:evening:{goal_id}"},
                {"text": "➡️ Далее", "callback": f"time_pref_done:{goal_id}"}
            ]

            return ProcessMessageResponse(
                success=True,
                response_type="inline_buttons",
                text=text,
                buttons=buttons
            )

        # Handle time_pref_done
        elif action == "time_pref_done":
            goal_id = int(parts[1])
            preferred_times = session_context.get("preferred_times", [])

            if not preferred_times:
                return ProcessMessageResponse(
                    success=True,
                    response_type="text",
                    text="Выбери хотя бы один временной слот! ⏰"
                )

            # Transition to days selection
            await update_session_state(user_id, DialogState.GOAL_SCHEDULE_DAYS_PREF, session_context)

            text = "📅 <b>В какие дни недели тебе удобно?</b>\n(можно выбрать несколько)"
            buttons = [
                {"text": "Пн", "callback": f"day_pref:mon:{goal_id}"},
                {"text": "Вт", "callback": f"day_pref:tue:{goal_id}"},
                {"text": "Ср", "callback": f"day_pref:wed:{goal_id}"},
                {"text": "Чт", "callback": f"day_pref:thu:{goal_id}"},
                {"text": "Пт", "callback": f"day_pref:fri:{goal_id}"},
                {"text": "Сб", "callback": f"day_pref:sat:{goal_id}"},
                {"text": "Вс", "callback": f"day_pref:sun:{goal_id}"},
                {"text": "✅ Готово", "callback": f"day_pref_done:{goal_id}"}
            ]

            return ProcessMessageResponse(
                success=True,
                response_type="inline_buttons",
                text=text,
                buttons=buttons
            )

        # Handle day_pref selection
        elif action == "day_pref":
            day = parts[1]
            goal_id = int(parts[2])

            # Get current preferences
            preferred_days = session_context.get("preferred_days", [])
            if day in preferred_days:
                preferred_days.remove(day)
            else:
                preferred_days.append(day)

            new_context = {
                **session_context,
                "preferred_days": preferred_days
            }
            await update_session_state(user_id, DialogState.GOAL_SCHEDULE_DAYS_PREF, new_context)

            # Show updated selection
            selected = ", ".join(preferred_days) if preferred_days else "не выбрано"
            text = f"📅 <b>В какие дни недели тебе удобно?</b>\n(можно выбрать несколько)\n\nВыбрано: {selected}"

            day_buttons = []
            for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
                label = {"mon": "Пн", "tue": "Вт", "wed": "Ср", "thu": "Чт", "fri": "Пт", "sat": "Сб", "sun": "Вс"}[d]
                if d in preferred_days:
                    label = f"✅ {label}"
                day_buttons.append({"text": label, "callback": f"day_pref:{d}:{goal_id}"})

            day_buttons.append({"text": "➡️ Далее", "callback": f"day_pref_done:{goal_id}"})

            return ProcessMessageResponse(
                success=True,
                response_type="inline_buttons",
                text=text,
                buttons=day_buttons
            )

        # Handle day_pref_done - generate schedule
        elif action == "day_pref_done":
            goal_id = int(parts[1])
            preferred_days = session_context.get("preferred_days", [])

            if not preferred_days:
                return ProcessMessageResponse(
                    success=True,
                    response_type="text",
                    text="Выбери хотя бы один день недели! 📅"
                )

            # Fetch goal data
            goal_response = http_client.get(f"{CORE_SERVICE_URL}/api/goals/{goal_id}", params={"user_id": user_id})
            goal = goal_response.json()

            # Fetch existing events
            from datetime import datetime
            deadline = session_context.get("deadline")
            today = datetime.now().date().isoformat()

            events_response = http_client.get(
                f"{CORE_SERVICE_URL}/api/events",
                params={"user_id": user_id, "start_date": today, "end_date": deadline}
            )
            existing_events = events_response.json()

            # Get free slots
            time_prefs = session_context.get("preferred_times", [])
            slots_response = http_client.get(
                f"{CORE_SERVICE_URL}/api/goals/free-slots",
                params={
                    "user_id": user_id,
                    "start_date": today,
                    "end_date": deadline,
                    "preferred_times": ",".join(time_prefs),
                    "preferred_days": ",".join(preferred_days),
                    "duration_minutes": 120
                }
            )
            free_slots_data = slots_response.json()
            free_slots = free_slots_data.get("slots", [])

            # Generate schedule via LLM
            logger.info(f"[{user_id}] Generating schedule for goal {goal_id}")
            schedule_response = http_client.post(
                f"{LLM_SERVICE_URL}/api/generate-schedule",
                json={
                    "goal_title": goal["title"],
                    "steps": goal["steps"],
                    "start_date": today,
                    "deadline": deadline,
                    "preferred_times": time_prefs,
                    "preferred_days": preferred_days,
                    "duration_minutes": 120,
                    "existing_events": existing_events,
                    "free_slots": free_slots
                }
            )
            schedule_plan = schedule_response.json()

            # Handle both list and dict responses
            if isinstance(schedule_plan, dict):
                # LLM returned error or reason
                await update_session_state(user_id, DialogState.IDLE, {})
                reason = schedule_plan.get("reason", "Не удалось создать расписание")
                return ProcessMessageResponse(
                    success=False,
                    response_type="text",
                    text=f"К сожалению, {reason}. Попробуй изменить дедлайн или выбрать больше дней. 😔"
                )

            if not schedule_plan or len(schedule_plan) == 0:
                await update_session_state(user_id, DialogState.IDLE, {})
                return ProcessMessageResponse(
                    success=False,
                    response_type="text",
                    text="К сожалению, не удалось создать расписание с заданными параметрами. Попробуй изменить дедлайн или выбрать больше дней. 😔"
                )

            # Save schedule plan to session
            new_context = {
                **session_context,
                "schedule_plan": schedule_plan
            }
            await update_session_state(user_id, DialogState.GOAL_SCHEDULE_CONFIRM, new_context)

            # Format schedule preview
            text = "📋 <b>Вот твоё расписание:</b>\n\n"
            for item in schedule_plan[:10]:
                step_id = item["step_id"]
                step = next((s for s in goal["steps"] if s["id"] == step_id), None)
                if step:
                    date = item["planned_date"]
                    time = item["planned_time"]
                    text += f"📅 {date} в {time}\n   {step['title']}\n\n"

            if len(schedule_plan) > 10:
                text += f"... и ещё {len(schedule_plan) - 10} событий\n\n"

            text += "Добавить в календарь?"

            return ProcessMessageResponse(
                success=True,
                response_type="inline_buttons",
                text=text,
                buttons=[
                    {"text": "✅ Да, добавить", "callback": f"schedule_confirm:{goal_id}"},
                    {"text": "❌ Отменить", "callback": f"schedule_cancel:{goal_id}"}
                ]
            )

        # Handle schedule_confirm - actually create events
        elif action == "schedule_confirm":
            goal_id = int(parts[1])
            schedule_plan = session_context.get("schedule_plan", [])

            if not schedule_plan:
                return ProcessMessageResponse(
                    success=False,
                    response_type="text",
                    text="Расписание не найдено. Попробуй ещё раз."
                )

            # Create events via Core Service
            logger.info(f"[{user_id}] Creating {len(schedule_plan)} scheduled events for goal {goal_id}")
            create_response = http_client.post(
                f"{CORE_SERVICE_URL}/api/goals/{goal_id}/schedule",
                json={
                    "user_id": user_id,
                    "schedule_plan": schedule_plan,
                    "create_calendar_events": True
                }
            )

            if create_response.status_code != 200:
                await update_session_state(user_id, DialogState.IDLE, {})
                return ProcessMessageResponse(
                    success=False,
                    response_type="text",
                    text="Произошла ошибка при создании событий. Попробуй позже."
                )

            result = create_response.json()
            created_events = result.get("created_events", [])

            await update_session_state(user_id, DialogState.IDLE, {})

            text = f"✅ Отлично! Я добавил {len(created_events)} событий в твой календарь.\n\n"
            text += "Буду напоминать о них! Удачи в достижении цели! 🎯🚀"

            track_event(user_id, "Goal Scheduled", {
                "goal_id": goal_id,
                "events_created": len(created_events)
            })

            return ProcessMessageResponse(
                success=True,
                response_type="text",
                text=text
            )

        # Handle schedule_cancel
        elif action == "schedule_cancel":
            goal_id = int(parts[1])
            await update_session_state(user_id, DialogState.IDLE, {})

            return ProcessMessageResponse(
                success=True,
                response_type="text",
                text="Хорошо, отменил планирование. Если передумаешь - дай знать! 👍"
            )

        else:
            logger.warning(f"[{user_id}] Unknown callback action: {action}")
            return ProcessMessageResponse(
                success=False,
                response_type="text",
                text="Неизвестная команда. Попробуй ещё раз."
            )

    except Exception as e:
        logger.exception(f"[{user_id}] Error processing callback")
        return ProcessMessageResponse(
            success=False,
            response_type="text",
            text="Упс, произошла ошибка. Попробуй ещё раз.",
            error=str(e)
        )

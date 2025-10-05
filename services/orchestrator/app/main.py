from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import os

from shared.utils.logger import setup_logger
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
    response_type: str  # 'text' | 'table' | 'clarification'
    text: Optional[str] = None
    items: Optional[list] = None
    set_id: Optional[str] = None
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

            # Update step status
            new_status = params.get("new_status", "completed")
            response = http_client.put(
                f"{CORE_SERVICE_URL}/api/steps/{target_step['id']}/status",
                json={"status": new_status}
            )

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

        # Step 5: Check state transitions
        new_state = StateMachine.should_transition(current_state, intent, {**session_context, **params})

        if new_state:
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

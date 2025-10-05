"""
State Machine for multi-turn dialogues
"""
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class DialogState(str, Enum):
    IDLE = "idle"
    GOAL_CLARIFICATION = "goal_clarification"
    GOAL_STEPS_GENERATION = "goal_steps_generation"
    GOAL_CONFIRM = "goal_confirm"
    EVENT_CLARIFICATION = "event_clarification"
    PRODUCT_SEARCH = "product_search"


class StateMachine:
    """
    Manages dialogue state transitions and context
    """

    @staticmethod
    def should_transition(current_state: str, intent: str, context: Dict[str, Any]) -> Optional[str]:
        """
        Determine if state transition is needed based on intent and context

        Returns new state or None if no transition
        """
        # From IDLE
        if current_state == DialogState.IDLE:
            if intent == "goal.create":
                return DialogState.GOAL_CLARIFICATION
            elif intent == "event.create" and not context.get("date"):
                return DialogState.EVENT_CLARIFICATION
            elif intent == "product.search":
                return DialogState.PRODUCT_SEARCH

        # From GOAL_CLARIFICATION
        elif current_state == DialogState.GOAL_CLARIFICATION:
            if context.get("goal_title") and context.get("current_level"):
                return DialogState.GOAL_STEPS_GENERATION

        # From GOAL_STEPS_GENERATION
        elif current_state == DialogState.GOAL_STEPS_GENERATION:
            if context.get("generated_steps"):
                return DialogState.GOAL_CONFIRM

        # From GOAL_CONFIRM
        elif current_state == DialogState.GOAL_CONFIRM:
            if intent in ["goal.confirm", "goal.cancel"]:
                return DialogState.IDLE

        # From EVENT_CLARIFICATION
        elif current_state == DialogState.EVENT_CLARIFICATION:
            if context.get("date"):
                return DialogState.IDLE

        # From PRODUCT_SEARCH
        elif current_state == DialogState.PRODUCT_SEARCH:
            return DialogState.IDLE  # Single-turn for now

        return None

    @staticmethod
    def get_context_expiry(state: str) -> int:
        """Get context expiry in hours for given state"""
        expiry_map = {
            DialogState.IDLE: 1,
            DialogState.GOAL_CLARIFICATION: 4,
            DialogState.GOAL_STEPS_GENERATION: 2,
            DialogState.GOAL_CONFIRM: 2,
            DialogState.EVENT_CLARIFICATION: 2,
            DialogState.PRODUCT_SEARCH: 1,
        }
        return expiry_map.get(state, 1)

    @staticmethod
    def get_prompt_hint(state: str, context: Dict[str, Any]) -> str:
        """Get prompt hint for user based on current state"""
        hints = {
            DialogState.GOAL_CLARIFICATION: "Расскажи больше о цели: твой текущий уровень, сколько времени готов уделять?",
            DialogState.GOAL_CONFIRM: "Подтверди создание цели или попроси изменить шаги",
            DialogState.EVENT_CLARIFICATION: "Уточни дату и время события",
            DialogState.PRODUCT_SEARCH: "Уточни параметры поиска",
        }
        return hints.get(state, "")

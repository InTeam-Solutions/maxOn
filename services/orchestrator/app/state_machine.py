"""
State Machine for multi-turn dialogues
"""
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class DialogState(str, Enum):
    IDLE = "idle"
    GOAL_CLARIFICATION = "goal_clarification"
    GOAL_TIME_COMMITMENT = "goal_time_commitment"
    GOAL_STEPS_GENERATION = "goal_steps_generation"
    GOAL_CONFIRM = "goal_confirm"
    GOAL_DEADLINE_REQUEST = "goal_deadline_request"
    GOAL_SCHEDULE_OFFER = "goal_schedule_offer"
    GOAL_SCHEDULE_TIME_PREF = "goal_schedule_time_pref"
    GOAL_SCHEDULE_DAYS_PREF = "goal_schedule_days_pref"
    GOAL_SCHEDULE_CONFIRM = "goal_schedule_confirm"
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
                # After confirming goal, ask for deadline
                return DialogState.GOAL_DEADLINE_REQUEST

        # From GOAL_DEADLINE_REQUEST
        elif current_state == DialogState.GOAL_DEADLINE_REQUEST:
            if context.get("deadline"):
                # After deadline is provided, offer to schedule
                return DialogState.GOAL_SCHEDULE_OFFER

        # From GOAL_SCHEDULE_OFFER
        elif current_state == DialogState.GOAL_SCHEDULE_OFFER:
            if context.get("schedule_accepted") is True:
                # User wants to schedule, ask for time preferences
                return DialogState.GOAL_SCHEDULE_TIME_PREF
            elif context.get("schedule_accepted") is False:
                # User declined scheduling
                return DialogState.IDLE

        # From GOAL_SCHEDULE_TIME_PREF
        elif current_state == DialogState.GOAL_SCHEDULE_TIME_PREF:
            if context.get("preferred_times"):
                # Time preferences received, ask for day preferences
                return DialogState.GOAL_SCHEDULE_DAYS_PREF

        # From GOAL_SCHEDULE_DAYS_PREF
        elif current_state == DialogState.GOAL_SCHEDULE_DAYS_PREF:
            if context.get("preferred_days"):
                # All preferences collected, generate and confirm schedule
                return DialogState.GOAL_SCHEDULE_CONFIRM

        # From GOAL_SCHEDULE_CONFIRM
        elif current_state == DialogState.GOAL_SCHEDULE_CONFIRM:
            if context.get("schedule_confirmed"):
                # Schedule confirmed, create events and return to idle
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
            DialogState.GOAL_TIME_COMMITMENT: 4,
            DialogState.GOAL_STEPS_GENERATION: 2,
            DialogState.GOAL_CONFIRM: 2,
            DialogState.GOAL_DEADLINE_REQUEST: 4,
            DialogState.GOAL_SCHEDULE_OFFER: 2,
            DialogState.GOAL_SCHEDULE_TIME_PREF: 2,
            DialogState.GOAL_SCHEDULE_DAYS_PREF: 2,
            DialogState.GOAL_SCHEDULE_CONFIRM: 2,
            DialogState.EVENT_CLARIFICATION: 2,
            DialogState.PRODUCT_SEARCH: 1,
        }
        return expiry_map.get(state, 1)

    @staticmethod
    def get_prompt_hint(state: str, context: Dict[str, Any]) -> str:
        """Get prompt hint for user based on current state"""
        hints = {
            DialogState.GOAL_CLARIFICATION: "Расскажи больше о цели: твой текущий уровень, сколько времени готов уделять?",
            DialogState.GOAL_TIME_COMMITMENT: "Укажи, сколько времени в день готов выделять на эту цель",
            DialogState.GOAL_CONFIRM: "Подтверди создание цели или попроси изменить шаги",
            DialogState.GOAL_DEADLINE_REQUEST: "Укажи дедлайн для достижения цели",
            DialogState.GOAL_SCHEDULE_OFFER: "Хочешь запланировать шаги в календаре?",
            DialogState.GOAL_SCHEDULE_TIME_PREF: "Выбери удобное время для работы",
            DialogState.GOAL_SCHEDULE_DAYS_PREF: "Выбери дни недели для работы над целью",
            DialogState.GOAL_SCHEDULE_CONFIRM: "Подтверди расписание или попроси изменить",
            DialogState.EVENT_CLARIFICATION: "Уточни дату и время события",
            DialogState.PRODUCT_SEARCH: "Уточни параметры поиска",
        }
        return hints.get(state, "")

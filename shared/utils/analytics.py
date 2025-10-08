import os
from typing import Dict, Any, Optional
from mixpanel import Mixpanel, MixpanelException
import logging
from .pricing import calculate_cost, calculate_audio_cost

logger = logging.getLogger("analytics")
logging.basicConfig(level=logging.INFO)

MIXPANEL_TOKEN = os.getenv("MIXPANEL_TOKEN")

# Initialize Mixpanel with EU endpoint
mp = None
if MIXPANEL_TOKEN:
    from mixpanel import Consumer

    # Create custom consumer for EU endpoint
    consumer = Consumer(
        events_url="https://api-eu.mixpanel.com/track",
        people_url="https://api-eu.mixpanel.com/engage"
    )

    mp = Mixpanel(MIXPANEL_TOKEN, consumer=consumer)
    logger.info(f"✅ Mixpanel (EU) initialized with token: {MIXPANEL_TOKEN[:8]}...")
else:
    logger.warning("⚠️ Mixpanel not configured (no token)")


def track_event(
    user_id: str,
    event_name: str,
    properties: Optional[Dict[str, Any]] = None
):
    """
    Track event to Mixpanel with automatic cost calculation

    Args:
        user_id: User identifier (distinct_id in Mixpanel)
        event_name: Event name (e.g., "Message Received", "LLM Parse")
        properties: Additional event properties (e.g., tokens, model, intent)
    """
    if not mp:
        logger.warning(f"Mixpanel not configured, skipping event: {event_name}")
        return

    try:
        props = properties or {}

        # Calculate cost if model and tokens are provided
        cost_calculated = 0.0
        if "model" in props:
            model = props.get("model")
            input_tokens = props.get("tokens_input", 0)
            output_tokens = props.get("tokens_output", 0)
            cache_tokens = props.get("tokens_cache", 0)

            cost = calculate_cost(model, input_tokens, output_tokens, cache_tokens)
            if cost > 0:
                cost_calculated = cost
                props["cost_rub"] = round(cost, 4)

        # Calculate audio cost if audio_seconds provided
        if "audio_seconds" in props and "model" in props:
            audio_cost = calculate_audio_cost(props["model"], props["audio_seconds"])
            if audio_cost > 0:
                cost_calculated = audio_cost
                props["cost_rub"] = round(audio_cost, 4)

        mp.track(user_id, event_name, props)

        # Increment total cost for user
        if cost_calculated > 0:
            mp.people_increment(user_id, {"total_cost_rub": round(cost_calculated, 4)})

        logger.info(f"✅ Tracked event: {event_name} for user {user_id}")
    except MixpanelException as e:
        logger.error(f"❌ Mixpanel error tracking {event_name}: {e}")
    except Exception as e:
        logger.error(f"Failed to track event {event_name}: {e}")


def set_user_profile(
    user_id: str,
    properties: Dict[str, Any]
):
    """
    Set user profile properties in Mixpanel

    Args:
        user_id: User identifier
        properties: User properties (e.g., $name, $email, language)
    """
    if not mp:
        return

    try:
        mp.people_set(user_id, properties)
        logger.info(f"✅ Updated profile for user {user_id}")
    except MixpanelException as e:
        logger.error(f"❌ Mixpanel error updating profile for {user_id}: {e}")
    except Exception as e:
        logger.error(f"Failed to update profile for {user_id}: {e}")


def increment_user_counter(
    user_id: str,
    property_name: str,
    increment: int = 1
):
    """
    Increment user profile counter in Mixpanel

    Args:
        user_id: User identifier
        property_name: Counter property name (e.g., "total_messages", "total_tokens")
        increment: Amount to increment (default: 1)
    """
    if not mp:
        return

    try:
        mp.people_increment(user_id, {property_name: increment})
        logger.info(f"✅ Incremented {property_name} by {increment} for user {user_id}")
    except MixpanelException as e:
        logger.error(f"❌ Mixpanel error incrementing {property_name} for {user_id}: {e}")
    except Exception as e:
        logger.error(f"Failed to increment {property_name} for {user_id}: {e}")

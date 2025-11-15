"""
LLM Pricing Configuration
All prices in RUB per 1M tokens
Source: ProxyAPI pricing as of October 2025
"""

# OpenAI Models Pricing (RUB per 1M tokens)
OPENAI_PRICING = {
    # GPT-5 Series
    "gpt-5-2025-08-07": {"input": 306, "output": 2448, "cache": 30.60},
    "gpt-5-chat-latest": {"input": 306, "output": 2448, "cache": 30.60},
    "gpt-5-codex": {"input": 306, "output": 2448, "cache": 30.60},
    "gpt-5-mini-2025-08-07": {"input": 61.20, "output": 489.60, "cache": 6.12},
    "gpt-5-nano-2025-04-14": {"input": 12.24, "output": 97.92, "cache": 1.22},

    # GPT-4.1 Series
    "gpt-4.1-2025-04-14": {"input": 489.60, "output": 1958.40, "cache": 122.40},
    "gpt-4.1-mini-2025-04-14": {"input": 97.92, "output": 391.68, "cache": 24.48},
    "gpt-4.1-nano-2025-04-14": {"input": 24.48, "output": 97.92, "cache": 6.12},

    # GPT-4o Series
    "gpt-4o-2024-11-20": {"input": 612, "output": 2448, "cache": 306},
    "gpt-4o-2024-08-06": {"input": 612, "output": 2448, "cache": 306},
    "gpt-4o-2024-05-13": {"input": 1224, "output": 3672},
    "gpt-4o-mini-2024-07-18": {"input": 36.72, "output": 146.88, "cache": 18.36},
    "gpt-4o-mini": {"input": 36.72, "output": 146.88, "cache": 18.36},

    # GPT-4 Turbo
    "gpt-4-turbo-2024-04-09": {"input": 2448, "output": 7344},
    "gpt-4-1106-preview": {"input": 2448, "output": 7344},
    "gpt-4-0125-preview": {"input": 2448, "output": 7344},

    # GPT-3.5 Turbo
    "gpt-3.5-turbo-0125": {"input": 122.40, "output": 367.20},
    "gpt-3.5-turbo-1106": {"input": 255.00, "output": 510.00},

    # O-series Models
    "o4-mini-2025-04-16": {"input": 269.28, "output": 1077.12, "cache": 67.32},
    "o3-2025-04-16": {"input": 576, "output": 1600, "cache": 144},
    "o3-mini-2025-01-31": {"input": 269.28, "output": 1077.12, "cache": 134.64},
    "o3-pro-2025-06-10": {"input": 2400, "output": 9600},
    "o1-2024-12-17": {"input": 2550, "output": 7650, "cache": 1275},
    "o1-mini-2024-09-12": {"input": 734.40, "output": 1530, "cache": 367.20},
    "o1-preview-2024-09-12": {"input": 2550, "output": 7650, "cache": 1275},
    "o1-pro-2025-03-19": {"input": 15300, "output": 76500},
}

# Anthropic Models Pricing (RUB per 1M tokens)
ANTHROPIC_PRICING = {
    "claude-sonnet-4-5-20250929": {
        "input": 734.40,
        "output": 3672,
        "cache_read": 73.44,
        "cache_write": 918
    },
    "claude-sonnet-4-20250514": {
        "input": 734.40,
        "output": 3672,
        "cache_read": 73.44,
        "cache_write": 918
    },
    "claude-3-7-sonnet-20250219": {
        "input": 734.40,
        "output": 3672,
        "cache_read": 73.44,
        "cache_write": 918
    },
    "claude-3-5-sonnet-20241022": {
        "input": 734.40,
        "output": 3672,
        "cache_read": 73.44,
        "cache_write": 918
    },
    "claude-3-5-haiku-20241022": {
        "input": 244.80,
        "output": 1224,
        "cache_read": 24.48,
        "cache_write": 306
    },
    "claude-3-haiku-20240307": {
        "input": 61.20,
        "output": 306
    },
    "claude-opus-4-20250514": {
        "input": 3672,
        "output": 18360,
        "cache_read": 367.20,
        "cache_write": 4590
    },
}

# Google Models Pricing (RUB per 1M tokens)
GOOGLE_PRICING = {
    "gemini-2.5-pro": {"input": 306, "output": 2448, "input_200k": 612, "output_200k": 3672},
    "gemini-2.5-flash": {"input": 73.44, "output": 612, "audio_input": 244.80},
    "gemini-2.5-flash-lite": {"input": 24.48, "output": 122.40},
    "gemini-2.0-flash": {"input": 24.48, "output": 97.92, "audio_input": 171.36},
    "gemini-1.5-pro": {"input": 856.80, "output": 1713.60, "input_128k": 2570.40, "output_128k": 5140.80},
    "gemini-1.5-flash": {"input": 18.36, "output": 73.44},
}

# Audio Models Pricing
AUDIO_PRICING = {
    # Whisper (RUB per 1M seconds of audio)
    "whisper-1": {"audio": 1.47},
    "gpt-4o-transcribe": {"audio": 1.47},
    "gpt-4o-mini-transcribe": {"audio": 0.73},

    # TTS (RUB per 1M characters)
    "tts-1": {"output": 3672},
    "tts-1-hd": {"output": 7344},
    "gpt-4o-mini-tts": {"output": 2937.60},
}


def calculate_cost(model: str, input_tokens: int = 0, output_tokens: int = 0, cache_tokens: int = 0) -> float:
    """
    Calculate cost in RUB for LLM usage

    Args:
        model: Model name (e.g., "gpt-4o-mini", "claude-3-5-sonnet-20241022")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cache_tokens: Number of cached tokens (for supported models)

    Returns:
        Total cost in RUB
    """
    # Try OpenAI pricing
    if model in OPENAI_PRICING:
        pricing = OPENAI_PRICING[model]
        cost = (input_tokens / 1_000_000) * pricing["input"]
        cost += (output_tokens / 1_000_000) * pricing["output"]
        if cache_tokens > 0 and "cache" in pricing:
            cost += (cache_tokens / 1_000_000) * pricing["cache"]
        return cost

    # Try Anthropic pricing
    if model in ANTHROPIC_PRICING:
        pricing = ANTHROPIC_PRICING[model]
        cost = (input_tokens / 1_000_000) * pricing["input"]
        cost += (output_tokens / 1_000_000) * pricing["output"]
        if cache_tokens > 0 and "cache_read" in pricing:
            cost += (cache_tokens / 1_000_000) * pricing["cache_read"]
        return cost

    # Try Google pricing
    if model in GOOGLE_PRICING:
        pricing = GOOGLE_PRICING[model]
        cost = (input_tokens / 1_000_000) * pricing["input"]
        cost += (output_tokens / 1_000_000) * pricing["output"]
        return cost

    # Unknown model
    return 0.0


def calculate_audio_cost(model: str, audio_seconds: float = 0) -> float:
    """
    Calculate cost for audio processing (Whisper)

    Args:
        model: Model name (e.g., "whisper-1")
        audio_seconds: Duration in seconds

    Returns:
        Cost in RUB
    """
    if model in AUDIO_PRICING:
        pricing = AUDIO_PRICING[model]
        if "audio" in pricing:
            return (audio_seconds / 1_000_000) * pricing["audio"]
    return 0.0

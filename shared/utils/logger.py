import logging
import sys
from typing import Any, Dict


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Setup structured logger for services"""

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    # Format
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


def log_with_context(logger: logging.Logger, level: str, message: str, **context: Any):
    """Log with additional context"""
    context_str = " ".join([f"{k}={v}" for k, v in context.items()])
    full_message = f"{message} {context_str}" if context else message

    log_func = getattr(logger, level.lower())
    log_func(full_message)
"""
Structured logging configuration using loguru.
"""

import sys
from loguru import logger
from app.core.config import settings


def configure_logging() -> None:
    """Set up application logging."""
    logger.remove()  # Remove default handler

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Console output
    logger.add(
        sys.stdout,
        format=log_format,
        level="DEBUG" if settings.debug else "INFO",
        colorize=True,
    )

    # File output (structured JSON for production)
    if settings.is_production:
        logger.add(
            "logs/app.log",
            format="{time} | {level} | {name}:{function}:{line} | {message}",
            level="INFO",
            rotation="100 MB",
            retention="30 days",
            serialize=True,  # JSON format
        )

    logger.info(
        "Logging configured | env={env} | debug={debug}",
        env=settings.app_env,
        debug=settings.debug,
    )

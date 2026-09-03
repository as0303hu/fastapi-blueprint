from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime
from typing import Any

from loguru import logger

POD_ID = os.environ.get("HOSTNAME", "local")


class JSONFormatter(logging.Formatter):
    """Structured JSON formatter for log aggregators (DataDog, SPlunk, CloudWatch)."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "pod": POD_ID,
        }
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id  # type: ignore
        if hasattr(record, "session_id"):
            log_entry["session_id"] = record.session_id  # type:ignore
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


class InterceptHandler(logging.Handler):
    """Redirect all stdlib logging calls to Loguru for unified output."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


NOISY_LOGGERS = (
    "pdfminer",
    "httpcore",
    "httpx",
    "azure",
    "urllib3",
    "opentelemetry",
    "asyncio",
    "multipart",
)

LOGGER_FORMAT = "<level>{level: <8}</level> <green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"


def setup_logging(level: str = "INFO", json_output: bool | None = None) -> None:
    """Configure logging for the application.

    Args:
        level: Root log level.
        json_output: Force JSON output. If None, auto-detects from ENVIRONMENT.
    """
    from src.config import settings

    if json_output is None:
        json_output = settings.ENVIRONMENT != "development"

    # Remove default loguru handler
    logger.remove()

    if json_output:
        # Production: structured JSON to stdout
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setFormatter(JSONFormatter())
        logging.root.handlers = [console_handler]
        logging.root.setLevel(getattr(logging, level.upper(), logging.INFO))
    else:
        # Development: human-readable colored output via loguru
        logger.add(
            sys.stdout,
            format=LOGGER_FORMAT,
            level=level.upper(),
            colorize=True,
        )

    # Intercept stdlib loggers -> loguru
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Suppress noisy third-party loggers
    for noisy in NOISY_LOGGERS:
        logging.getLogger(noisy).setLevel(logging.WARNING)


def init_logger() -> None:
    """Convenience function called at app startup."""
    from src.config import settings

    setup_logging(level=settings.LOG_LEVEL)

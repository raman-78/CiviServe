"""Structured logging via structlog, tied to a requestId contextvar.

Override default fields per env: pretty console in development, single-line JSON
in staging/production (docs/architecture/14). Importing this module does NOT
configure logging; call ``configure_logging()`` from the app factory.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from contextvars import ContextVar
from typing import Any, cast
from uuid import uuid4

import structlog

from app.core.config import Settings, get_settings
from app.core.constants import SERVICE_NAME

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return request_id_var.get()


def set_request_id(rid: str | None = None) -> str:
    value = rid or uuid4().hex
    request_id_var.set(value)
    structlog.contextvars.bind_contextvars(request_id=value)
    return value


def _add_meta(
    logger: Any,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Attach standard fields to every event."""
    event_dict.setdefault("service", SERVICE_NAME)
    event_dict.setdefault("requestId", get_request_id())
    return event_dict


def configure_logging(settings: Settings | None = None) -> None:
    """Configure stdlib + structlog for the chosen environment."""
    settings = settings or get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    pre_chain: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_meta,
    ]

    if settings.env == "development":
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *pre_chain,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=pre_chain,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str = "civiserve_server") -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger for ``name == __name__``."""
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))

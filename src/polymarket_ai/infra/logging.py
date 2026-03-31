from __future__ import annotations

import json
import logging
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "event"):
            payload["event"] = record.event
        if hasattr(record, "context"):
            payload["context"] = record.context
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str, *, trace_id: str | None = None, agent_name: str | None = None) -> logging.LoggerAdapter:
    context: dict[str, Any] = {}
    if trace_id is not None:
        context["trace_id"] = trace_id
    if agent_name is not None:
        context["agent_name"] = agent_name
    return logging.LoggerAdapter(logging.getLogger(name), {"context": context})

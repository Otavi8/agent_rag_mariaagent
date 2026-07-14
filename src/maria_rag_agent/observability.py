from __future__ import annotations

import os
import time
from contextvars import ContextVar
from typing import Any

from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST

from .config import Settings


_tool_trace: ContextVar[list[dict[str, Any]] | None] = ContextVar("tool_trace", default=None)

agent_requests_total = Counter(
    "maria_agent_requests_total",
    "Total agent requests.",
    ["channel", "status"],
)
agent_request_duration_seconds = Histogram(
    "maria_agent_request_duration_seconds",
    "Agent request duration in seconds.",
    ["channel"],
    buckets=[0.25, 0.5, 1, 2, 5, 10, 30, 60],
)
agent_tool_calls_total = Counter(
    "maria_agent_tool_calls_total",
    "Total tool calls performed by the agent.",
    ["tool_name", "status"],
)
http_requests_total = Counter(
    "maria_http_requests_total",
    "Total HTTP requests handled by the application.",
    ["service", "method", "path", "status"],
)
http_request_duration_seconds = Histogram(
    "maria_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["service", "method", "path"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10],
)


def reset_tool_trace():
    return _tool_trace.set([])


def restore_tool_trace(token) -> None:
    _tool_trace.reset(token)


def get_tool_trace() -> list[dict[str, Any]]:
    return list(_tool_trace.get() or [])


def record_tool_call(tool_name: str, tool_input: Any, tool_output: Any, status: str = "success") -> None:
    agent_tool_calls_total.labels(tool_name=tool_name, status=status).inc()
    trace = _tool_trace.get()
    if trace is None:
        return
    trace.append(
        {
            "tool_name": tool_name,
            "input": _short_text(tool_input),
            "output_preview": _short_text(tool_output, limit=1200),
            "status": status,
        }
    )


def get_langfuse_callbacks(settings: Settings) -> list[Any]:
    if not settings.langfuse_enabled:
        return []
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return []

    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)
    os.environ.setdefault("LANGFUSE_BASE_URL", settings.langfuse_host)

    try:
        from langfuse.langchain import CallbackHandler
    except Exception:
        return []

    return [CallbackHandler()]


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


def timed_agent_request(channel: str):
    return _AgentRequestTimer(channel)


class _AgentRequestTimer:
    def __init__(self, channel: str):
        self.channel = channel
        self.started_at = 0.0

    def __enter__(self):
        self.started_at = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, traceback):
        duration = time.perf_counter() - self.started_at
        status = "error" if exc_type else "success"
        agent_requests_total.labels(channel=self.channel, status=status).inc()
        agent_request_duration_seconds.labels(channel=self.channel).observe(duration)
        return False


def _short_text(value: Any, limit: int = 500) -> str:
    text = value if isinstance(value, str) else str(value)
    return text[:limit]

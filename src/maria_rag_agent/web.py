from __future__ import annotations

import time
from typing import Any

from flask import Flask, Response, jsonify, render_template, request
from prometheus_flask_exporter import PrometheusMetrics

from .agent import ask_agent
from .config import Settings, get_settings
from .database import init_database
from .guardrails import GuardrailViolation
from .observability import http_request_duration_seconds, http_requests_total, metrics_response
from .vectorstore import ensure_vector_store_ready


app = Flask(__name__)
PrometheusMetrics(app, path=None)


def _settings() -> Settings:
    return get_settings()


@app.before_request
def _start_timer() -> None:
    request.environ["maria_started_at"] = time.perf_counter()


@app.after_request
def _record_http_metrics(response):
    started_at = request.environ.get("maria_started_at", time.perf_counter())
    duration = time.perf_counter() - started_at
    http_requests_total.labels(
        service="web",
        method=request.method,
        path=request.url_rule.rule if request.url_rule else request.path,
        status=str(response.status_code),
    ).inc()
    http_request_duration_seconds.labels(
        service="web",
        method=request.method,
        path=request.url_rule.rule if request.url_rule else request.path,
    ).observe(duration)
    return response


@app.get("/")
def index():
    return render_template(
        "chat.html",
        answer=None,
        question="",
        conversation_id="",
        user_id=_settings().web_user_id,
        store_id="",
        tool_calls=[],
        error=None,
    )


@app.post("/chat")
def chat():
    settings = _settings()
    question = request.form.get("question", "").strip()
    conversation_id = request.form.get("conversation_id", "").strip() or None
    user_id = request.form.get("user_id", "").strip() or settings.web_user_id
    store_id = request.form.get("store_id", "").strip() or None

    try:
        ensure_vector_store_ready(settings)
        reply = ask_agent(
            question=question,
            settings=settings,
            conversation_id=conversation_id,
            user_id=user_id,
            store_id=store_id,
            channel="web",
        )
        return render_template(
            "chat.html",
            answer=reply.answer,
            question=question,
            conversation_id=reply.conversation_id,
            user_id=reply.user_id,
            store_id=reply.store_id or "",
            tool_calls=reply.tool_calls or [],
            error=None,
        )
    except (GuardrailViolation, ValueError, RuntimeError) as exc:
        return render_template(
            "chat.html",
            answer=None,
            question=question,
            conversation_id=conversation_id or "",
            user_id=user_id,
            store_id=store_id or "",
            tool_calls=[],
            error=str(exc),
        ), 400


@app.post("/api/chat")
def api_chat():
    settings = _settings()
    payload: dict[str, Any] = request.get_json(silent=True) or {}
    try:
        reply = ask_agent(
            question=str(payload.get("question", "")),
            settings=settings,
            conversation_id=payload.get("conversation_id"),
            user_id=str(payload.get("user_id") or settings.web_user_id),
            store_id=payload.get("store_id"),
            channel="web",
        )
        if not reply.answer.strip():
            return jsonify({"error": "A Maria retornou uma resposta vazia. Tente reformular a pergunta."}), 502
        return jsonify(
            {
                "answer": reply.answer,
                "conversation_id": reply.conversation_id,
                "user_id": reply.user_id,
                "store_id": reply.store_id,
                "tool_calls": reply.tool_calls or [],
            }
        )
    except (GuardrailViolation, ValueError, RuntimeError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/metrics")
def metrics():
    payload, content_type = metrics_response()
    return Response(payload, content_type=content_type)


def main() -> None:
    settings = _settings()
    init_database(settings)
    app.run(host=settings.web_host, port=settings.web_port)


if __name__ == "__main__":
    main()

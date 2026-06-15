from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage

from .config import Settings
from .database import (
    append_conversation_message,
    count_conversation_messages,
    fetch_conversation,
    fetch_conversation_messages,
    fetch_conversation_summary,
    fetch_recent_conversation_messages,
    fetch_user_memories,
    insert_user_memory,
    list_conversations,
    upsert_conversation,
    upsert_conversation_summary,
)


@dataclass
class ConversationSession:
    conversation_id: str
    user_id: str
    store_id: str | None = None


def generate_conversation_id() -> str:
    return f"conv_{uuid4().hex[:12]}"


def ensure_conversation(
    settings: Settings,
    user_id: str,
    conversation_id: str | None = None,
    store_id: str | None = None,
    title: str | None = None,
) -> ConversationSession:
    resolved_conversation_id = conversation_id or generate_conversation_id()
    existing_conversation = fetch_conversation(settings, resolved_conversation_id)
    if existing_conversation and existing_conversation["user_id"] != user_id:
        raise ValueError(
            "This conversation_id already belongs to another user_id."
        )
    upsert_conversation(
        settings=settings,
        conversation_id=resolved_conversation_id,
        user_id=user_id,
        store_id=store_id,
        title=title,
    )
    return ConversationSession(
        conversation_id=resolved_conversation_id,
        user_id=user_id,
        store_id=store_id,
    )


def conversation_exists(settings: Settings, conversation_id: str) -> bool:
    summary = fetch_conversation_summary(settings, conversation_id)
    messages = fetch_recent_conversation_messages(settings, conversation_id, limit=1)
    return summary is not None or bool(messages)


def add_user_memory(
    settings: Settings,
    user_id: str,
    content: str,
    memory_type: str = "note",
    store_id: str | None = None,
    priority: int = 1,
) -> int:
    return insert_user_memory(
        settings=settings,
        user_id=user_id,
        content=content,
        memory_type=memory_type,
        store_id=store_id,
        priority=priority,
    )


def build_memory_messages(
    settings: Settings,
    conversation_id: str,
    user_id: str,
    store_id: str | None = None,
) -> list[dict[str, str]]:
    if not settings.enable_conversation_memory:
        return []

    messages: list[dict[str, str]] = []

    summary_row = fetch_conversation_summary(settings, conversation_id)
    if summary_row:
        messages.append(
            {
                "role": "system",
                "content": (
                    "Conversation summary for continuity. Use it as memory, but prefer more recent"
                    " messages when they conflict.\n"
                    f"{summary_row['summary']}"
                ),
            }
        )

    if settings.enable_user_memory:
        memory_rows = fetch_user_memories(
            settings,
            user_id=user_id,
            limit=settings.user_memory_top_k,
            store_id=store_id,
        )
        if memory_rows:
            payload = [
                {
                    "memory_type": row["memory_type"],
                    "content": row["content"],
                    "priority": row["priority"],
                    "store_id": row["store_id"],
                }
                for row in memory_rows
            ]
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Durable user/store memories. Use them only when relevant and do not invent"
                        " details beyond these notes.\n"
                        + json.dumps(payload, ensure_ascii=True, indent=2)
                    ),
                }
            )

    recent_rows = fetch_recent_conversation_messages(
        settings,
        conversation_id=conversation_id,
        limit=settings.memory_recent_messages,
    )
    for row in recent_rows:
        messages.append({"role": row["role"], "content": row["content"]})

    return messages


def store_turn(
    settings: Settings,
    conversation_id: str,
    user_text: str,
    assistant_text: str,
) -> None:
    append_conversation_message(settings, conversation_id, "user", user_text)
    append_conversation_message(settings, conversation_id, "assistant", assistant_text)


def maybe_refresh_conversation_summary(
    settings: Settings,
    conversation_id: str,
    model,
) -> None:
    if not settings.enable_conversation_memory:
        return

    total_messages = count_conversation_messages(settings, conversation_id)
    if total_messages < settings.memory_summarize_after_messages:
        return

    recent_rows = fetch_recent_conversation_messages(
        settings,
        conversation_id=conversation_id,
        limit=settings.memory_recent_messages,
    )
    if not recent_rows:
        return

    cutoff_message_id = recent_rows[0]["id"] - 1
    if cutoff_message_id < 1:
        return

    existing_summary = fetch_conversation_summary(settings, conversation_id)
    summarized_until = (
        int(existing_summary["summarized_until_message_id"]) if existing_summary else 0
    )

    if cutoff_message_id <= summarized_until:
        return

    incremental_rows = fetch_conversation_messages(
        settings,
        conversation_id=conversation_id,
        after_message_id=summarized_until,
    )
    rows_to_summarize = [row for row in incremental_rows if row["id"] <= cutoff_message_id]
    if not rows_to_summarize:
        return

    transcript_parts: list[str] = []
    for row in rows_to_summarize:
        transcript_parts.append(f"{row['role'].upper()}: {row['content']}")
    transcript = "\n".join(transcript_parts)

    old_summary = existing_summary["summary"] if existing_summary else "No previous summary."

    summary_messages = [
        SystemMessage(
            content=(
                "You summarize business conversations for memory compression.\n"
                f"Produce a concise summary with at most {settings.memory_summary_max_chars} characters.\n"
                "Keep only durable context: user goals, operational facts, decisions, pending items,"
                " constraints, preferred reporting style, and relevant store context.\n"
                "Do not include greetings, filler, or low-value repetition."
            )
        ),
        HumanMessage(
            content=(
                "Previous summary:\n"
                f"{old_summary}\n\n"
                "New messages to merge into the summary:\n"
                f"{transcript}\n\n"
                "Return the updated conversation summary only."
            )
        ),
    ]

    response = model.invoke(summary_messages)
    summary_text = getattr(response, "content", str(response))
    if isinstance(summary_text, list):
        parts = []
        for item in summary_text:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        summary_text = "\n".join(part for part in parts if part)

    upsert_conversation_summary(
        settings=settings,
        conversation_id=conversation_id,
        summary=str(summary_text).strip(),
        summarized_until_message_id=cutoff_message_id,
    )


def format_conversation_rows(rows) -> list[dict[str, object]]:
    return [dict(row) for row in rows]


def get_conversation_messages_for_display(
    settings: Settings, conversation_id: str, limit: int = 20
) -> list[dict[str, object]]:
    rows = fetch_recent_conversation_messages(settings, conversation_id, limit=limit)
    return format_conversation_rows(rows)


def get_conversations_for_display(
    settings: Settings, user_id: str | None = None, limit: int = 20
) -> list[dict[str, object]]:
    rows = list_conversations(settings, user_id=user_id, limit=limit)
    return format_conversation_rows(rows)


def get_user_memories_for_display(
    settings: Settings, user_id: str, store_id: str | None = None
) -> list[dict[str, object]]:
    rows = fetch_user_memories(
        settings,
        user_id=user_id,
        store_id=store_id,
        limit=max(settings.user_memory_top_k, 20),
    )
    return format_conversation_rows(rows)

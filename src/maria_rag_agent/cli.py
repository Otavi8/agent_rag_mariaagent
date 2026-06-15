from __future__ import annotations

import argparse
import json

from .config import get_settings
from .database import init_database, seed_database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maria RAG Agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Create the SQLite schema.")
    subparsers.add_parser("seed-db", help="Insert sample data into the SQLite database.")
    subparsers.add_parser("reindex", help="Rebuild the local vector database.")
    subparsers.add_parser("show-config", help="Print the loaded configuration.")

    ask_parser = subparsers.add_parser("ask", help="Ask a question to the hybrid RAG agent.")
    ask_parser.add_argument("question", help="Question for the agent.")
    ask_parser.add_argument("--conversation-id", dest="conversation_id", help="Existing conversation id.")
    ask_parser.add_argument("--user-id", dest="user_id", default="default-user", help="User id for memory isolation.")
    ask_parser.add_argument("--store-id", dest="store_id", help="Optional store id.")

    list_conversations_parser = subparsers.add_parser(
        "list-conversations", help="List saved conversations."
    )
    list_conversations_parser.add_argument("--user-id", dest="user_id", help="Filter by user id.")
    list_conversations_parser.add_argument("--limit", dest="limit", type=int, default=20)

    show_conversation_parser = subparsers.add_parser(
        "show-conversation", help="Show recent messages from a conversation."
    )
    show_conversation_parser.add_argument("conversation_id", help="Conversation id.")
    show_conversation_parser.add_argument("--limit", dest="limit", type=int, default=20)

    add_memory_parser = subparsers.add_parser(
        "add-user-memory", help="Save a durable user memory note."
    )
    add_memory_parser.add_argument("user_id", help="User id.")
    add_memory_parser.add_argument("content", help="Memory content.")
    add_memory_parser.add_argument("--memory-type", dest="memory_type", default="note")
    add_memory_parser.add_argument("--store-id", dest="store_id")
    add_memory_parser.add_argument("--priority", dest="priority", type=int, default=1)

    list_memories_parser = subparsers.add_parser(
        "list-user-memories", help="List durable memories for a user."
    )
    list_memories_parser.add_argument("user_id", help="User id.")
    list_memories_parser.add_argument("--store-id", dest="store_id")

    return parser


def handle_init_db() -> None:
    settings = get_settings()
    init_database(settings)
    print(f"SQLite initialized at {settings.sqlite_path_abs}")


def handle_seed_db() -> None:
    settings = get_settings()
    stats = seed_database(settings)
    print(f"Seed data loaded into {settings.sqlite_path_abs}")
    print(json.dumps(stats, ensure_ascii=True, indent=2))


def handle_reindex() -> None:
    settings = get_settings()
    from .vectorstore import reindex_vector_store

    stats = reindex_vector_store(settings)
    print(json.dumps(stats, ensure_ascii=True, indent=2))


def handle_show_config() -> None:
    settings = get_settings()
    print(json.dumps(settings.as_public_dict(), ensure_ascii=True, indent=2, default=str))


def handle_ask(
    question: str,
    conversation_id: str | None,
    user_id: str,
    store_id: str | None,
) -> None:
    settings = get_settings()
    from .agent import ask_agent
    from .vectorstore import reindex_vector_store, vector_store_is_ready

    if settings.auto_reindex_on_empty_index and not vector_store_is_ready(settings):
        reindex_vector_store(settings)

    reply = ask_agent(
        question=question,
        settings=settings,
        conversation_id=conversation_id,
        user_id=user_id,
        store_id=store_id,
    )
    print(f"[conversation_id={reply.conversation_id}]")
    print(reply.answer)


def handle_list_conversations(user_id: str | None, limit: int) -> None:
    settings = get_settings()
    from .memory import get_conversations_for_display

    payload = get_conversations_for_display(settings, user_id=user_id, limit=limit)
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def handle_show_conversation(conversation_id: str, limit: int) -> None:
    settings = get_settings()
    from .memory import get_conversation_messages_for_display

    payload = get_conversation_messages_for_display(
        settings,
        conversation_id=conversation_id,
        limit=limit,
    )
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def handle_add_user_memory(
    user_id: str,
    content: str,
    memory_type: str,
    store_id: str | None,
    priority: int,
) -> None:
    settings = get_settings()
    from .memory import add_user_memory

    memory_id = add_user_memory(
        settings=settings,
        user_id=user_id,
        content=content,
        memory_type=memory_type,
        store_id=store_id,
        priority=priority,
    )
    print(
        json.dumps(
            {
                "memory_id": memory_id,
                "user_id": user_id,
                "store_id": store_id,
                "memory_type": memory_type,
                "priority": priority,
            },
            ensure_ascii=True,
            indent=2,
        )
    )


def handle_list_user_memories(user_id: str, store_id: str | None) -> None:
    settings = get_settings()
    from .memory import get_user_memories_for_display

    payload = get_user_memories_for_display(settings, user_id=user_id, store_id=store_id)
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init-db":
        handle_init_db()
        return

    if args.command == "seed-db":
        handle_seed_db()
        return

    if args.command == "reindex":
        handle_reindex()
        return

    if args.command == "show-config":
        handle_show_config()
        return

    if args.command == "ask":
        handle_ask(args.question, args.conversation_id, args.user_id, args.store_id)
        return

    if args.command == "list-conversations":
        handle_list_conversations(args.user_id, args.limit)
        return

    if args.command == "show-conversation":
        handle_show_conversation(args.conversation_id, args.limit)
        return

    if args.command == "add-user-memory":
        handle_add_user_memory(
            args.user_id,
            args.content,
            args.memory_type,
            args.store_id,
            args.priority,
        )
        return

    if args.command == "list-user-memories":
        handle_list_user_memories(args.user_id, args.store_id)
        return

    parser.error(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()

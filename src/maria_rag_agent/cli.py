from __future__ import annotations

import argparse
import json
import sys

from .config import get_settings
from .database import init_database, seed_database
from .evolution import normalize_phone_number
from .guardrails import GuardrailViolation


def print_user_error(message: str) -> None:
    print(f"Maria: {message}", file=sys.stderr)


def run_user_safe(action) -> int:
    try:
        action()
        return 0
    except GuardrailViolation as exc:
        print_user_error(str(exc))
        return 2
    except ValueError as exc:
        print_user_error(str(exc))
        return 2
    except RuntimeError as exc:
        print_user_error(str(exc))
        return 2
    except Exception as exc:
        print_user_error(
            "Ocorreu um erro inesperado ao executar a solicitacao. "
            "Revise a configuracao e tente novamente."
        )
        print_user_error(f"Detalhe tecnico: {exc}")
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maria RAG Agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Create the PostgreSQL schema.")
    subparsers.add_parser("seed-db", help="Insert sample data into the PostgreSQL database.")
    migrate_sqlite_parser = subparsers.add_parser(
        "migrate-sqlite",
        help="Import data from a legacy SQLite database into PostgreSQL.",
    )
    migrate_sqlite_parser.add_argument(
        "--sqlite-path",
        dest="sqlite_path",
        default="data/maria_agent.db",
        help="Path to the legacy SQLite database file.",
    )
    migrate_sqlite_parser.add_argument(
        "--replace-existing",
        dest="replace_existing",
        action="store_true",
        help="Replace existing PostgreSQL data before importing the SQLite content.",
    )
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

    authorize_whatsapp_parser = subparsers.add_parser(
        "authorize-whatsapp-user",
        help="Authorize a WhatsApp number to receive answers from the agent.",
    )
    authorize_whatsapp_parser.add_argument("user_name", help="Display name for the authorized user.")
    authorize_whatsapp_parser.add_argument("phone_number", help="WhatsApp number.")
    authorize_whatsapp_parser.add_argument("--notes", dest="notes")

    list_whatsapp_users_parser = subparsers.add_parser(
        "list-whatsapp-users",
        help="List authorized WhatsApp users.",
    )
    list_whatsapp_users_parser.add_argument("--all", dest="include_inactive", action="store_true")

    deactivate_whatsapp_parser = subparsers.add_parser(
        "deactivate-whatsapp-user",
        help="Deactivate an authorized WhatsApp number without deleting its history.",
    )
    deactivate_whatsapp_parser.add_argument("phone_number", help="WhatsApp number.")

    list_blocked_whatsapp_parser = subparsers.add_parser(
        "list-blocked-whatsapp",
        help="List blocked WhatsApp numbers.",
    )
    list_blocked_whatsapp_parser.add_argument("--limit", dest="limit", type=int, default=100)

    unblock_whatsapp_parser = subparsers.add_parser(
        "unblock-whatsapp-number",
        help="Remove a WhatsApp number from the blocked list.",
    )
    unblock_whatsapp_parser.add_argument("phone_number", help="WhatsApp number.")

    return parser


def handle_init_db() -> None:
    settings = get_settings()
    init_database(settings)
    print(f"PostgreSQL schema initialized for database {settings.database_name}")


def handle_seed_db() -> None:
    settings = get_settings()
    stats = seed_database(settings)
    print(f"Seed data loaded into PostgreSQL database {settings.database_name}")
    print(json.dumps(stats, ensure_ascii=True, indent=2))


def handle_migrate_sqlite(sqlite_path: str, replace_existing: bool) -> None:
    settings = get_settings()
    from .migrations import migrate_sqlite_to_postgres

    stats = migrate_sqlite_to_postgres(
        settings,
        sqlite_path=sqlite_path,
        replace_existing=replace_existing,
    )
    print(f"SQLite data imported into PostgreSQL database {settings.database_name}")
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
    from .vectorstore import ensure_vector_store_ready

    ensure_vector_store_ready(settings)

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


def handle_authorize_whatsapp_user(
    user_name: str,
    phone_number: str,
    notes: str | None,
) -> None:
    settings = get_settings()
    from .database import delete_whatsapp_blocked_contact, upsert_whatsapp_allowed_contact

    normalized_phone = normalize_phone_number(phone_number)
    if not normalized_phone:
        raise ValueError("Informe um numero de WhatsApp valido para autorizacao.")

    row = upsert_whatsapp_allowed_contact(
        settings=settings,
        user_name=user_name,
        phone_number=normalized_phone,
        notes=notes,
        is_active=True,
    )
    delete_whatsapp_blocked_contact(settings, normalized_phone)
    print(json.dumps(dict(row), ensure_ascii=True, indent=2, default=str))


def handle_list_whatsapp_users(include_inactive: bool) -> None:
    settings = get_settings()
    from .database import list_whatsapp_allowed_contacts

    rows = list_whatsapp_allowed_contacts(settings, active_only=not include_inactive)
    print(json.dumps(rows, ensure_ascii=True, indent=2, default=str))


def handle_deactivate_whatsapp_user(phone_number: str) -> None:
    settings = get_settings()
    from .database import set_whatsapp_allowed_contact_active

    normalized_phone = normalize_phone_number(phone_number)
    if not normalized_phone:
        raise ValueError("Informe um numero de WhatsApp valido para desativacao.")

    row = set_whatsapp_allowed_contact_active(settings, normalized_phone, is_active=False)
    if not row:
        raise ValueError("Numero nao encontrado na lista de autorizados.")
    print(json.dumps(dict(row), ensure_ascii=True, indent=2, default=str))


def handle_list_blocked_whatsapp(limit: int) -> None:
    settings = get_settings()
    from .database import list_whatsapp_blocked_contacts

    rows = list_whatsapp_blocked_contacts(settings, limit=limit)
    print(json.dumps(rows, ensure_ascii=True, indent=2, default=str))


def handle_unblock_whatsapp_number(phone_number: str) -> None:
    settings = get_settings()
    from .database import delete_whatsapp_blocked_contact

    normalized_phone = normalize_phone_number(phone_number)
    if not normalized_phone:
        raise ValueError("Informe um numero de WhatsApp valido para desbloqueio.")

    removed = delete_whatsapp_blocked_contact(settings, normalized_phone)
    if not removed:
        raise ValueError("Numero nao encontrado na lista de bloqueados.")
    print(
        json.dumps(
            {"phone_number": normalized_phone, "unblocked": True},
            ensure_ascii=True,
            indent=2,
        )
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init-db":
        raise SystemExit(run_user_safe(handle_init_db))

    if args.command == "seed-db":
        raise SystemExit(run_user_safe(handle_seed_db))

    if args.command == "migrate-sqlite":
        raise SystemExit(
            run_user_safe(
                lambda: handle_migrate_sqlite(args.sqlite_path, args.replace_existing)
            )
        )

    if args.command == "reindex":
        raise SystemExit(run_user_safe(handle_reindex))

    if args.command == "show-config":
        raise SystemExit(run_user_safe(handle_show_config))

    if args.command == "ask":
        raise SystemExit(
            run_user_safe(
                lambda: handle_ask(
                    args.question,
                    args.conversation_id,
                    args.user_id,
                    args.store_id,
                )
            )
        )

    if args.command == "list-conversations":
        raise SystemExit(run_user_safe(lambda: handle_list_conversations(args.user_id, args.limit)))

    if args.command == "show-conversation":
        raise SystemExit(
            run_user_safe(lambda: handle_show_conversation(args.conversation_id, args.limit))
        )

    if args.command == "add-user-memory":
        raise SystemExit(
            run_user_safe(
                lambda: handle_add_user_memory(
                    args.user_id,
                    args.content,
                    args.memory_type,
                    args.store_id,
                    args.priority,
                )
            )
        )

    if args.command == "list-user-memories":
        raise SystemExit(
            run_user_safe(lambda: handle_list_user_memories(args.user_id, args.store_id))
        )

    if args.command == "authorize-whatsapp-user":
        raise SystemExit(
            run_user_safe(
                lambda: handle_authorize_whatsapp_user(
                    args.user_name,
                    args.phone_number,
                    args.notes,
                )
            )
        )

    if args.command == "list-whatsapp-users":
        raise SystemExit(run_user_safe(lambda: handle_list_whatsapp_users(args.include_inactive)))

    if args.command == "deactivate-whatsapp-user":
        raise SystemExit(
            run_user_safe(lambda: handle_deactivate_whatsapp_user(args.phone_number))
        )

    if args.command == "list-blocked-whatsapp":
        raise SystemExit(run_user_safe(lambda: handle_list_blocked_whatsapp(args.limit)))

    if args.command == "unblock-whatsapp-number":
        raise SystemExit(
            run_user_safe(lambda: handle_unblock_whatsapp_number(args.phone_number))
        )

    parser.error(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()

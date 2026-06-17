from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from psycopg import sql

from .config import Settings
from .database import init_database, postgres_connection


TABLE_MIGRATIONS: list[tuple[str, tuple[str, ...]]] = [
    (
        "product_catalog",
        (
            "id",
            "sku",
            "description",
            "category",
            "department",
            "unit_measure",
            "supplier_name",
            "cost_price",
            "selling_price",
            "gross_margin_pct",
            "current_stock_qty",
            "reorder_point_qty",
            "status",
            "last_inventory_at",
        ),
    ),
    (
        "employees",
        (
            "id",
            "id_colaborador",
            "employee_name",
            "sector",
            "role_name",
            "status",
            "primary_shift",
            "cross_trained_sectors",
            "weekly_hours",
        ),
    ),
    (
        "sales",
        (
            "id",
            "sale_date",
            "sku",
            "product_description",
            "category",
            "quantity_sold",
            "unit_price",
            "gross_revenue",
            "discount_value",
            "net_revenue",
            "cash_generation",
            "payment_method",
            "sales_channel",
            "shift",
        ),
    ),
    (
        "absenteeism_events",
        (
            "id",
            "event_date",
            "id_colaborador",
            "sector",
            "scheduled_shift",
            "absence_type",
            "absence_hours",
            "coverage_priority",
            "replacement_required",
            "notes",
        ),
    ),
    (
        "conversations",
        (
            "conversation_id",
            "user_id",
            "store_id",
            "title",
            "created_at",
            "updated_at",
        ),
    ),
    (
        "conversation_messages",
        (
            "id",
            "conversation_id",
            "role",
            "content",
            "created_at",
        ),
    ),
    (
        "conversation_summaries",
        (
            "conversation_id",
            "summary",
            "summarized_until_message_id",
            "updated_at",
        ),
    ),
    (
        "user_memories",
        (
            "id",
            "user_id",
            "store_id",
            "memory_type",
            "content",
            "priority",
            "created_at",
            "updated_at",
        ),
    ),
    (
        "evolution_instance_state",
        (
            "instance_id",
            "instance_name",
            "instance_token",
            "last_event",
            "connection_status",
            "qr_code_base64",
            "phone_jid",
            "push_name",
            "metadata_json",
            "updated_at",
        ),
    ),
]

SERIAL_TABLES = (
    "product_catalog",
    "employees",
    "sales",
    "absenteeism_events",
    "conversation_messages",
    "user_memories",
)


def _sqlite_row_to_postgres_values(table_name: str, row: sqlite3.Row, columns: tuple[str, ...]) -> tuple[Any, ...]:
    values: list[Any] = []
    for column in columns:
        value = row[column]
        if table_name == "absenteeism_events" and column == "replacement_required" and value is not None:
            value = bool(value)
        values.append(value)
    return tuple(values)


def migrate_sqlite_to_postgres(
    settings: Settings,
    sqlite_path: str | Path,
    *,
    replace_existing: bool = False,
) -> dict[str, int]:
    source_path = Path(sqlite_path).expanduser().resolve()
    if not source_path.exists():
        raise RuntimeError(f"SQLite source file not found: {source_path}")

    init_database(settings)

    sqlite_connection = sqlite3.connect(source_path)
    sqlite_connection.row_factory = sqlite3.Row

    try:
        with postgres_connection(settings) as postgres_connection_handle:
            with postgres_connection_handle.cursor() as postgres_cursor:
                sqlite_tables = {
                    row["name"]
                    for row in sqlite_connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }

                if replace_existing:
                    postgres_cursor.execute(
                        """
                        TRUNCATE TABLE
                            evolution_instance_state,
                            conversation_summaries,
                            conversation_messages,
                            conversations,
                            user_memories,
                            absenteeism_events,
                            sales,
                            employees,
                            product_catalog
                        RESTART IDENTITY CASCADE
                        """
                    )
                else:
                    postgres_cursor.execute(
                        """
                        SELECT
                            (SELECT COUNT(*) FROM product_catalog)
                            + (SELECT COUNT(*) FROM sales)
                            + (SELECT COUNT(*) FROM employees)
                            + (SELECT COUNT(*) FROM absenteeism_events)
                            + (SELECT COUNT(*) FROM conversations)
                            + (SELECT COUNT(*) FROM conversation_messages)
                            + (SELECT COUNT(*) FROM conversation_summaries)
                            + (SELECT COUNT(*) FROM user_memories)
                            + (SELECT COUNT(*) FROM evolution_instance_state) AS total
                        """
                    )
                    total_rows = int(postgres_cursor.fetchone()["total"])
                    if total_rows > 0:
                        raise RuntimeError(
                            "O PostgreSQL de destino ja possui dados. "
                            "Use --replace-existing para substituir o conteudo atual."
                        )

                migrated_counts: dict[str, int] = {}

                for table_name, columns in TABLE_MIGRATIONS:
                    if table_name not in sqlite_tables:
                        migrated_counts[table_name] = 0
                        continue

                    select_columns = ", ".join(columns)
                    source_rows = sqlite_connection.execute(
                        f"SELECT {select_columns} FROM {table_name} ORDER BY ROWID"
                    ).fetchall()

                    if not source_rows:
                        migrated_counts[table_name] = 0
                        continue

                    insert_query = sql.SQL(
                        "INSERT INTO {} ({}) VALUES ({})"
                    ).format(
                        sql.Identifier(table_name),
                        sql.SQL(", ").join(sql.Identifier(column) for column in columns),
                        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
                    )
                    postgres_cursor.executemany(
                        insert_query,
                        [
                            _sqlite_row_to_postgres_values(table_name, row, columns)
                            for row in source_rows
                        ],
                    )
                    migrated_counts[table_name] = len(source_rows)

                for table_name in SERIAL_TABLES:
                    postgres_cursor.execute(
                        sql.SQL(
                            """
                            SELECT setval(
                                pg_get_serial_sequence({}, 'id'),
                                COALESCE((SELECT MAX(id) FROM {}), 1),
                                (SELECT MAX(id) IS NOT NULL FROM {})
                            )
                            """
                        ).format(
                            sql.Literal(table_name),
                            sql.Identifier(table_name),
                            sql.Identifier(table_name),
                        )
                    )

            postgres_connection_handle.commit()
    finally:
        sqlite_connection.close()

    return migrated_counts

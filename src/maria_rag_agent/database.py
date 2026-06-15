from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
import re
from typing import Iterator

from .config import Settings


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def validate_table_name(table_name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name):
        raise ValueError(f"Invalid table name: {table_name}")
    return table_name


@contextmanager
def sqlite_connection(settings: Settings) -> Iterator[sqlite3.Connection]:
    ensure_parent_dir(settings.sqlite_path_abs)
    connection = sqlite3.connect(settings.sqlite_path_abs)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


def init_database(settings: Settings) -> None:
    with sqlite_connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS product_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                department TEXT NOT NULL,
                unit_measure TEXT NOT NULL,
                supplier_name TEXT NOT NULL,
                cost_price REAL NOT NULL,
                selling_price REAL NOT NULL,
                gross_margin_pct REAL NOT NULL,
                current_stock_qty REAL NOT NULL,
                reorder_point_qty REAL NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('active', 'inactive')),
                last_inventory_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_date TEXT NOT NULL,
                sku TEXT NOT NULL,
                product_description TEXT NOT NULL,
                category TEXT NOT NULL,
                quantity_sold REAL NOT NULL,
                unit_price REAL NOT NULL,
                gross_revenue REAL NOT NULL,
                discount_value REAL NOT NULL,
                net_revenue REAL NOT NULL,
                cash_generation REAL NOT NULL,
                payment_method TEXT NOT NULL,
                sales_channel TEXT NOT NULL,
                shift TEXT NOT NULL,
                FOREIGN KEY (sku) REFERENCES product_catalog(sku)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_colaborador TEXT NOT NULL UNIQUE,
                employee_name TEXT NOT NULL,
                sector TEXT NOT NULL,
                role_name TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('a', 'i')),
                primary_shift TEXT NOT NULL,
                cross_trained_sectors TEXT,
                weekly_hours INTEGER NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS absenteeism_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_date TEXT NOT NULL,
                id_colaborador TEXT NOT NULL,
                sector TEXT NOT NULL,
                scheduled_shift TEXT NOT NULL,
                absence_type TEXT NOT NULL,
                absence_hours REAL NOT NULL,
                coverage_priority TEXT NOT NULL,
                replacement_required INTEGER NOT NULL CHECK(replacement_required IN (0, 1)),
                notes TEXT,
                FOREIGN KEY (id_colaborador) REFERENCES employees(id_colaborador)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                store_id TEXT,
                title TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                conversation_id TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                summarized_until_message_id INTEGER NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                store_id TEXT,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_catalog_sku ON product_catalog(sku)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_sale_date ON sales(sale_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_sku ON sales(sku)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_employees_sector_status ON employees(sector, status)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_absenteeism_event_date ON absenteeism_events(event_date)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id ON conversation_messages(conversation_id, id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_memories_user_store ON user_memories(user_id, store_id, priority)"
        )
        connection.commit()


def seed_database(settings: Settings) -> dict[str, int]:
    init_database(settings)
    with sqlite_connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM absenteeism_events")
        cursor.execute("DELETE FROM sales")
        cursor.execute("DELETE FROM employees")
        cursor.execute("DELETE FROM product_catalog")

        products = [
            ("HF001", "Banana prata", "frutas", "hortifrutti", "kg", "Fazenda Vale Verde", 3.25, 5.99, 83.0, 82.0, 22.0, "active", "2026-06-12"),
            ("HF002", "Maca gala premium", "frutas", "hortifrutti", "kg", "Pomar Serra Alta", 5.10, 8.49, 66.47, 61.0, 18.0, "active", "2026-06-12"),
            ("HF003", "Laranja pera", "frutas", "hortifrutti", "kg", "Citros Sol Nascente", 2.95, 4.79, 62.37, 74.0, 26.0, "active", "2026-06-12"),
            ("HF004", "Mamao formosa", "frutas", "hortifrutti", "kg", "Sao Bento Frutas", 4.40, 7.29, 65.68, 38.0, 14.0, "active", "2026-06-12"),
            ("HF005", "Abacaxi perola unidade", "frutas", "hortifrutti", "un", "Tropical Minas", 4.80, 8.99, 87.29, 24.0, 10.0, "active", "2026-06-12"),
            ("HF006", "Tomate italiano", "legumes", "hortifrutti", "kg", "Sitio Boa Safra", 4.35, 7.99, 83.68, 67.0, 20.0, "active", "2026-06-12"),
            ("HF007", "Batata lavada", "legumes", "hortifrutti", "kg", "Campos do Sul", 3.60, 5.69, 58.06, 89.0, 25.0, "active", "2026-06-12"),
            ("HF008", "Cebola amarela", "legumes", "hortifrutti", "kg", "Agro Prime", 2.85, 4.99, 75.09, 57.0, 18.0, "active", "2026-06-12"),
            ("HF009", "Cenoura extra", "legumes", "hortifrutti", "kg", "Campos do Sul", 2.70, 4.59, 70.0, 49.0, 16.0, "active", "2026-06-12"),
            ("HF010", "Alface crespa unidade", "verduras", "hortifrutti", "un", "Horta Santa Luzia", 1.10, 2.49, 126.36, 93.0, 28.0, "active", "2026-06-12"),
            ("HF011", "Couve manteiga molho", "verduras", "hortifrutti", "un", "Horta Santa Luzia", 1.45, 3.29, 126.9, 64.0, 20.0, "active", "2026-06-12"),
            ("HF012", "Rucula hidroponica", "verduras", "hortifrutti", "un", "Verde Vivo", 1.95, 4.29, 120.0, 33.0, 15.0, "active", "2026-06-12"),
            ("HF013", "Cheiro-verde molho", "temperos", "hortifrutti", "un", "Horta Santa Luzia", 0.95, 2.19, 130.53, 78.0, 24.0, "active", "2026-06-12"),
            ("HF014", "Morango bandeja 250g", "frutas", "hortifrutti", "un", "Berry Fresh", 4.90, 8.79, 79.39, 21.0, 12.0, "active", "2026-06-12"),
            ("HF015", "Uva thompson sem semente", "frutas", "hortifrutti", "kg", "Vinhas do Oeste", 8.20, 13.99, 70.61, 17.0, 8.0, "active", "2026-06-12"),
            ("HF016", "Pepino japones", "legumes", "hortifrutti", "kg", "Sitio Boa Safra", 3.10, 5.49, 77.1, 26.0, 12.0, "active", "2026-06-12"),
            ("HF017", "Beterraba extra", "legumes", "hortifrutti", "kg", "Agro Prime", 2.55, 4.39, 72.16, 29.0, 14.0, "active", "2026-06-12"),
            ("HF018", "Mix folhas organicas", "organicos", "hortifrutti", "un", "Verde Vivo", 3.65, 6.99, 91.51, 14.0, 9.0, "active", "2026-06-12"),
        ]
        cursor.executemany(
            """
            INSERT INTO product_catalog
            (
                sku, description, category, department, unit_measure, supplier_name,
                cost_price, selling_price, gross_margin_pct, current_stock_qty,
                reorder_point_qty, status, last_inventory_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            products,
        )

        employees = [
            ("C1001", "Ana Paula Souza", "caixa", "Operadora de caixa", "a", "manha", "atendimento,frente_de_loja", 44),
            ("C1002", "Bruno Henrique Lima", "hortifrutti", "Repositor senior", "a", "manha", "recebimento,estoque", 44),
            ("C1003", "Carla Mendes Rocha", "hortifrutti", "Repositor", "a", "tarde", "estoque,quebra", 44),
            ("C1004", "Diego Martins", "recebimento", "Conferente", "a", "manha", "estoque,hortifrutti", 44),
            ("C1005", "Elaine Cristina", "caixa", "Fiscal de caixa", "a", "tarde", "atendimento,frente_de_loja", 44),
            ("C1006", "Fabio Nogueira", "estoque", "Auxiliar de estoque", "a", "noite", "recebimento,hortifrutti", 44),
            ("C1007", "Gabriela Pires", "hortifrutti", "Lider de setor", "a", "manha", "estoque,recebimento,quebra", 44),
            ("C1008", "Helio Barbosa", "padaria_apoio", "Apoio operacional", "i", "manha", "hortifrutti,recebimento", 44),
            ("C1009", "Isabela Freitas", "atendimento", "Atendente", "a", "tarde", "caixa,frente_de_loja", 36),
            ("C1010", "Joao Victor Alves", "recebimento", "Auxiliar de carga", "a", "manha", "estoque,hortifrutti", 44),
            ("C1011", "Karen Ribeiro", "hortifrutti", "Promotora de abastecimento", "a", "noite", "quebra,estoque", 36),
            ("C1012", "Lucas Ferreira", "caixa", "Empacotador", "a", "tarde", "atendimento,hortifrutti", 36),
        ]
        cursor.executemany(
            """
            INSERT INTO employees
            (
                id_colaborador, employee_name, sector, role_name, status, primary_shift,
                cross_trained_sectors, weekly_hours
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            employees,
        )

        sales = [
            ("2026-06-01", "HF001", "Banana prata", "frutas", 48.5, 5.99, 290.52, 12.40, 278.12, 278.12, "pix", "loja_fisica", "manha"),
            ("2026-06-01", "HF006", "Tomate italiano", "legumes", 32.0, 7.99, 255.68, 9.60, 246.08, 238.70, "credito", "loja_fisica", "tarde"),
            ("2026-06-01", "HF010", "Alface crespa unidade", "verduras", 54.0, 2.49, 134.46, 4.50, 129.96, 129.96, "dinheiro", "loja_fisica", "manha"),
            ("2026-06-02", "HF002", "Maca gala premium", "frutas", 27.0, 8.49, 229.23, 7.80, 221.43, 214.79, "credito", "delivery", "tarde"),
            ("2026-06-02", "HF014", "Morango bandeja 250g", "frutas", 22.0, 8.79, 193.38, 6.00, 187.38, 187.38, "pix", "loja_fisica", "noite"),
            ("2026-06-02", "HF009", "Cenoura extra", "legumes", 25.0, 4.59, 114.75, 3.60, 111.15, 111.15, "debito", "loja_fisica", "manha"),
            ("2026-06-03", "HF003", "Laranja pera", "frutas", 51.0, 4.79, 244.29, 10.20, 234.09, 234.09, "pix", "loja_fisica", "manha"),
            ("2026-06-03", "HF007", "Batata lavada", "legumes", 40.0, 5.69, 227.60, 8.80, 218.80, 212.24, "credito", "loja_fisica", "tarde"),
            ("2026-06-03", "HF013", "Cheiro-verde molho", "temperos", 38.0, 2.19, 83.22, 0.00, 83.22, 83.22, "dinheiro", "loja_fisica", "manha"),
            ("2026-06-04", "HF004", "Mamao formosa", "frutas", 29.0, 7.29, 211.41, 5.40, 206.01, 199.83, "credito", "loja_fisica", "tarde"),
            ("2026-06-04", "HF011", "Couve manteiga molho", "verduras", 31.0, 3.29, 101.99, 2.10, 99.89, 99.89, "pix", "loja_fisica", "manha"),
            ("2026-06-04", "HF016", "Pepino japones", "legumes", 23.5, 5.49, 129.02, 1.80, 127.22, 127.22, "debito", "loja_fisica", "noite"),
            ("2026-06-05", "HF005", "Abacaxi perola unidade", "frutas", 19.0, 8.99, 170.81, 4.00, 166.81, 161.81, "credito", "loja_fisica", "tarde"),
            ("2026-06-05", "HF008", "Cebola amarela", "legumes", 34.0, 4.99, 169.66, 6.20, 163.46, 163.46, "pix", "loja_fisica", "manha"),
            ("2026-06-05", "HF018", "Mix folhas organicas", "organicos", 16.0, 6.99, 111.84, 0.00, 111.84, 108.48, "credito", "delivery", "noite"),
            ("2026-06-06", "HF001", "Banana prata", "frutas", 56.0, 5.99, 335.44, 12.80, 322.64, 322.64, "pix", "loja_fisica", "manha"),
            ("2026-06-06", "HF015", "Uva thompson sem semente", "frutas", 14.0, 13.99, 195.86, 5.60, 190.26, 184.55, "credito", "loja_fisica", "tarde"),
            ("2026-06-06", "HF017", "Beterraba extra", "legumes", 28.0, 4.39, 122.92, 2.00, 120.92, 120.92, "debito", "loja_fisica", "manha"),
            ("2026-06-07", "HF010", "Alface crespa unidade", "verduras", 61.0, 2.49, 151.89, 5.20, 146.69, 146.69, "dinheiro", "loja_fisica", "manha"),
            ("2026-06-07", "HF012", "Rucula hidroponica", "verduras", 24.0, 4.29, 102.96, 1.50, 101.46, 101.46, "pix", "delivery", "tarde"),
            ("2026-06-07", "HF006", "Tomate italiano", "legumes", 37.0, 7.99, 295.63, 11.40, 284.23, 275.70, "credito", "loja_fisica", "noite"),
            ("2026-06-08", "HF002", "Maca gala premium", "frutas", 30.0, 8.49, 254.70, 8.20, 246.50, 246.50, "pix", "loja_fisica", "manha"),
            ("2026-06-08", "HF011", "Couve manteiga molho", "verduras", 33.0, 3.29, 108.57, 2.70, 105.87, 102.69, "credito", "loja_fisica", "tarde"),
            ("2026-06-08", "HF013", "Cheiro-verde molho", "temperos", 42.0, 2.19, 91.98, 0.00, 91.98, 91.98, "pix", "loja_fisica", "manha"),
            ("2026-06-09", "HF003", "Laranja pera", "frutas", 47.5, 4.79, 227.53, 9.10, 218.43, 211.88, "credito", "loja_fisica", "tarde"),
            ("2026-06-09", "HF007", "Batata lavada", "legumes", 43.0, 5.69, 244.67, 7.90, 236.77, 236.77, "debito", "loja_fisica", "manha"),
            ("2026-06-09", "HF014", "Morango bandeja 250g", "frutas", 25.0, 8.79, 219.75, 6.50, 213.25, 213.25, "pix", "delivery", "noite"),
            ("2026-06-10", "HF004", "Mamao formosa", "frutas", 26.0, 7.29, 189.54, 5.00, 184.54, 184.54, "pix", "loja_fisica", "manha"),
            ("2026-06-10", "HF009", "Cenoura extra", "legumes", 29.0, 4.59, 133.11, 3.10, 130.01, 126.11, "credito", "loja_fisica", "tarde"),
            ("2026-06-10", "HF018", "Mix folhas organicas", "organicos", 18.0, 6.99, 125.82, 2.40, 123.42, 123.42, "pix", "delivery", "noite"),
            ("2026-06-11", "HF001", "Banana prata", "frutas", 52.0, 5.99, 311.48, 10.20, 301.28, 292.24, "credito", "loja_fisica", "manha"),
            ("2026-06-11", "HF006", "Tomate italiano", "legumes", 35.0, 7.99, 279.65, 10.50, 269.15, 269.15, "pix", "loja_fisica", "tarde"),
            ("2026-06-11", "HF015", "Uva thompson sem semente", "frutas", 13.0, 13.99, 181.87, 4.20, 177.67, 172.34, "credito", "loja_fisica", "noite"),
            ("2026-06-12", "HF005", "Abacaxi perola unidade", "frutas", 21.0, 8.99, 188.79, 3.50, 185.29, 179.73, "credito", "delivery", "manha"),
            ("2026-06-12", "HF010", "Alface crespa unidade", "verduras", 58.0, 2.49, 144.42, 4.80, 139.62, 139.62, "dinheiro", "loja_fisica", "tarde"),
            ("2026-06-12", "HF017", "Beterraba extra", "legumes", 26.0, 4.39, 114.14, 2.00, 112.14, 112.14, "pix", "loja_fisica", "noite"),
        ]
        cursor.executemany(
            """
            INSERT INTO sales
            (
                sale_date, sku, product_description, category, quantity_sold, unit_price,
                gross_revenue, discount_value, net_revenue, cash_generation, payment_method,
                sales_channel, shift
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            sales,
        )

        absenteeism_events = [
            ("2026-06-03", "C1003", "hortifrutti", "tarde", "atestado_medico", 8.0, "alta", 1, "Reposicao de folhosos ficou descoberta por meio turno."),
            ("2026-06-04", "C1012", "caixa", "tarde", "falta_nao_justificada", 6.0, "media", 1, "Fluxo do caixa exigiu remanejamento da frente de loja."),
            ("2026-06-06", "C1004", "recebimento", "manha", "consulta_medica", 4.0, "alta", 1, "Recebimento de banana e tomate precisou de apoio do estoque."),
            ("2026-06-07", "C1011", "hortifrutti", "noite", "licenca_curta", 8.0, "media", 1, "Abastecimento noturno de frutas sensiveis ficou reduzido."),
            ("2026-06-09", "C1001", "caixa", "manha", "atestado_medico", 8.0, "alta", 1, "Fiscal de caixa assumiu abertura de dois PDVs."),
            ("2026-06-10", "C1010", "recebimento", "manha", "falta_justificada", 8.0, "alta", 1, "Conferencia de mercadoria foi redistribuida entre estoque e lider de setor."),
            ("2026-06-12", "C1002", "hortifrutti", "manha", "consulta_medica", 4.0, "alta", 1, "Setor perdeu apoio na reposicao de alto giro pela manha."),
            ("2026-06-12", "C1009", "atendimento", "tarde", "falta_nao_justificada", 6.0, "baixa", 0, "Cobertura feita pelo time do caixa sem necessidade de reforco adicional."),
        ]
        cursor.executemany(
            """
            INSERT INTO absenteeism_events
            (
                event_date, id_colaborador, sector, scheduled_shift, absence_type,
                absence_hours, coverage_priority, replacement_required, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            absenteeism_events,
        )

        connection.commit()

    return {
        "product_catalog": len(products),
        "sales": len(sales),
        "employees": len(employees),
        "absenteeism_events": len(absenteeism_events),
    }


def fetch_rows_for_indexing(settings: Settings) -> dict[str, list[sqlite3.Row]]:
    init_database(settings)
    rows_by_table: dict[str, list[sqlite3.Row]] = {}
    with sqlite_connection(settings) as connection:
        cursor = connection.cursor()
        for table_name in settings.source_table_list:
            safe_table_name = validate_table_name(table_name)
            rows = cursor.execute(f"SELECT * FROM {safe_table_name}").fetchall()
            rows_by_table[table_name] = rows
    return rows_by_table


def describe_schema(settings: Settings) -> str:
    init_database(settings)
    descriptions: list[str] = []
    with sqlite_connection(settings) as connection:
        cursor = connection.cursor()
        for table_name in settings.source_table_list:
            safe_table_name = validate_table_name(table_name)
            columns = cursor.execute(f"PRAGMA table_info({safe_table_name})").fetchall()
            descriptions.append(f"Table {table_name}:")
            for column in columns:
                descriptions.append(
                    f"- {column['name']} ({column['type']})"
                    + (" PRIMARY KEY" if column["pk"] else "")
                )
    return "\n".join(descriptions)


def run_read_only_query(settings: Settings, query: str) -> list[dict[str, object]]:
    init_database(settings)
    with sqlite_connection(settings) as connection:
        cursor = connection.cursor()
        rows = cursor.execute(query).fetchmany(settings.sql_max_rows)
        return [dict(row) for row in rows]


def upsert_conversation(
    settings: Settings,
    conversation_id: str,
    user_id: str,
    store_id: str | None = None,
    title: str | None = None,
) -> None:
    init_database(settings)
    with sqlite_connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO conversations (conversation_id, user_id, store_id, title)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
                user_id = excluded.user_id,
                store_id = COALESCE(excluded.store_id, conversations.store_id),
                title = COALESCE(conversations.title, excluded.title),
                updated_at = CURRENT_TIMESTAMP
            """,
            (conversation_id, user_id, store_id, title),
        )
        connection.commit()


def append_conversation_message(
    settings: Settings,
    conversation_id: str,
    role: str,
    content: str,
) -> int:
    init_database(settings)
    with sqlite_connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO conversation_messages (conversation_id, role, content)
            VALUES (?, ?, ?)
            """,
            (conversation_id, role, content),
        )
        cursor.execute(
            """
            UPDATE conversations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        )
        connection.commit()
        return int(cursor.lastrowid)


def fetch_conversation_messages(
    settings: Settings,
    conversation_id: str,
    limit: int | None = None,
    after_message_id: int | None = None,
) -> list[sqlite3.Row]:
    init_database(settings)
    query = """
        SELECT id, conversation_id, role, content, created_at
        FROM conversation_messages
        WHERE conversation_id = ?
    """
    parameters: list[object] = [conversation_id]

    if after_message_id is not None:
        query += " AND id > ?"
        parameters.append(after_message_id)

    query += " ORDER BY id ASC"

    if limit is not None:
        query += " LIMIT ?"
        parameters.append(limit)

    with sqlite_connection(settings) as connection:
        cursor = connection.cursor()
        rows = cursor.execute(query, parameters).fetchall()
    return rows


def fetch_recent_conversation_messages(
    settings: Settings,
    conversation_id: str,
    limit: int,
) -> list[sqlite3.Row]:
    init_database(settings)
    with sqlite_connection(settings) as connection:
        cursor = connection.cursor()
        rows = cursor.execute(
            """
            SELECT id, conversation_id, role, content, created_at
            FROM conversation_messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (conversation_id, limit),
        ).fetchall()
    return list(reversed(rows))


def count_conversation_messages(settings: Settings, conversation_id: str) -> int:
    init_database(settings)
    with sqlite_connection(settings) as connection:
        cursor = connection.cursor()
        row = cursor.execute(
            "SELECT COUNT(*) AS total FROM conversation_messages WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
    return int(row["total"])


def fetch_conversation_summary(settings: Settings, conversation_id: str) -> sqlite3.Row | None:
    init_database(settings)
    with sqlite_connection(settings) as connection:
        cursor = connection.cursor()
        row = cursor.execute(
            """
            SELECT conversation_id, summary, summarized_until_message_id, updated_at
            FROM conversation_summaries
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        ).fetchone()
    return row


def upsert_conversation_summary(
    settings: Settings,
    conversation_id: str,
    summary: str,
    summarized_until_message_id: int,
) -> None:
    init_database(settings)
    with sqlite_connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO conversation_summaries
            (conversation_id, summary, summarized_until_message_id, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(conversation_id) DO UPDATE SET
                summary = excluded.summary,
                summarized_until_message_id = excluded.summarized_until_message_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (conversation_id, summary, summarized_until_message_id),
        )
        connection.commit()


def insert_user_memory(
    settings: Settings,
    user_id: str,
    content: str,
    memory_type: str = "note",
    store_id: str | None = None,
    priority: int = 1,
) -> int:
    init_database(settings)
    with sqlite_connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO user_memories
            (user_id, store_id, memory_type, content, priority)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, store_id, memory_type, content, priority),
        )
        connection.commit()
        return int(cursor.lastrowid)


def fetch_user_memories(
    settings: Settings,
    user_id: str,
    limit: int,
    store_id: str | None = None,
) -> list[sqlite3.Row]:
    init_database(settings)
    query = """
        SELECT id, user_id, store_id, memory_type, content, priority, created_at, updated_at
        FROM user_memories
        WHERE user_id = ?
    """
    parameters: list[object] = [user_id]

    if store_id:
        query += " AND (store_id = ? OR store_id IS NULL)"
        parameters.append(store_id)

    query += " ORDER BY priority DESC, updated_at DESC, id DESC LIMIT ?"
    parameters.append(limit)

    with sqlite_connection(settings) as connection:
        cursor = connection.cursor()
        rows = cursor.execute(query, parameters).fetchall()
    return rows


def list_conversations(
    settings: Settings,
    user_id: str | None = None,
    limit: int = 20,
) -> list[sqlite3.Row]:
    init_database(settings)
    query = """
        SELECT conversation_id, user_id, store_id, title, created_at, updated_at
        FROM conversations
    """
    parameters: list[object] = []

    if user_id:
        query += " WHERE user_id = ?"
        parameters.append(user_id)

    query += " ORDER BY updated_at DESC LIMIT ?"
    parameters.append(limit)

    with sqlite_connection(settings) as connection:
        cursor = connection.cursor()
        rows = cursor.execute(query, parameters).fetchall()
    return rows


def fetch_conversation(settings: Settings, conversation_id: str) -> sqlite3.Row | None:
    init_database(settings)
    with sqlite_connection(settings) as connection:
        cursor = connection.cursor()
        row = cursor.execute(
            """
            SELECT conversation_id, user_id, store_id, title, created_at, updated_at
            FROM conversations
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        ).fetchone()
    return row

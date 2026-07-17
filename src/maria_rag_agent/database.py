from __future__ import annotations

import json
import re
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Any, Iterator

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from .config import Settings


DbRow = dict[str, Any]


def validate_table_name(table_name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name):
        raise ValueError(f"Invalid table name: {table_name}")
    return table_name


@contextmanager
def postgres_connection(settings: Settings) -> Iterator[psycopg.Connection]:
    connection = psycopg.connect(settings.database_url, row_factory=dict_row)
    try:
        yield connection
    finally:
        connection.close()


def init_database(settings: Settings) -> None:
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS product_catalog (
                    id SERIAL PRIMARY KEY,
                    sku TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    department TEXT NOT NULL,
                    unit_measure TEXT NOT NULL,
                    supplier_name TEXT NOT NULL,
                    cost_price DOUBLE PRECISION NOT NULL,
                    selling_price DOUBLE PRECISION NOT NULL,
                    gross_margin_pct DOUBLE PRECISION NOT NULL,
                    current_stock_qty DOUBLE PRECISION NOT NULL,
                    reorder_point_qty DOUBLE PRECISION NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('active', 'inactive')),
                    last_inventory_at DATE NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sales (
                    id SERIAL PRIMARY KEY,
                    sale_date DATE NOT NULL,
                    sku TEXT NOT NULL,
                    product_description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    quantity_sold DOUBLE PRECISION NOT NULL,
                    unit_price DOUBLE PRECISION NOT NULL,
                    gross_revenue DOUBLE PRECISION NOT NULL,
                    discount_value DOUBLE PRECISION NOT NULL,
                    net_revenue DOUBLE PRECISION NOT NULL,
                    cash_generation DOUBLE PRECISION NOT NULL,
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
                    id SERIAL PRIMARY KEY,
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
                    id SERIAL PRIMARY KEY,
                    event_date DATE NOT NULL,
                    id_colaborador TEXT NOT NULL,
                    sector TEXT NOT NULL,
                    scheduled_shift TEXT NOT NULL,
                    absence_type TEXT NOT NULL,
                    absence_hours DOUBLE PRECISION NOT NULL,
                    coverage_priority TEXT NOT NULL,
                    replacement_required BOOLEAN NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (id_colaborador) REFERENCES employees(id_colaborador)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS purchase_orders (
                    id SERIAL PRIMARY KEY,
                    po_code TEXT NOT NULL UNIQUE,
                    order_date DATE NOT NULL,
                    expected_delivery_date DATE NOT NULL,
                    supplier_name TEXT NOT NULL,
                    sku TEXT NOT NULL,
                    quantity_ordered DOUBLE PRECISION NOT NULL,
                    unit_cost DOUBLE PRECISION NOT NULL,
                    total_cost DOUBLE PRECISION NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('open', 'partial', 'delivered', 'cancelled')),
                    buyer_name TEXT NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (sku) REFERENCES product_catalog(sku)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory_movements (
                    id SERIAL PRIMARY KEY,
                    movement_date DATE NOT NULL,
                    sku TEXT NOT NULL,
                    movement_type TEXT NOT NULL,
                    quantity_delta DOUBLE PRECISION NOT NULL,
                    stock_after_qty DOUBLE PRECISION NOT NULL,
                    reference_type TEXT NOT NULL,
                    reference_code TEXT,
                    notes TEXT,
                    FOREIGN KEY (sku) REFERENCES product_catalog(sku)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_stock_snapshot (
                    id SERIAL PRIMARY KEY,
                    snapshot_date DATE NOT NULL,
                    sku TEXT NOT NULL,
                    available_qty DOUBLE PRECISION NOT NULL,
                    reserved_qty DOUBLE PRECISION NOT NULL,
                    reorder_point_qty DOUBLE PRECISION NOT NULL,
                    stock_status TEXT NOT NULL CHECK(stock_status IN ('ok', 'attention', 'critical', 'stockout')),
                    days_of_cover DOUBLE PRECISION NOT NULL,
                    FOREIGN KEY (sku) REFERENCES product_catalog(sku)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS customer_orders (
                    id SERIAL PRIMARY KEY,
                    order_code TEXT NOT NULL UNIQUE,
                    order_date DATE NOT NULL,
                    customer_name TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    sku TEXT NOT NULL,
                    quantity_ordered DOUBLE PRECISION NOT NULL,
                    order_value DOUBLE PRECISION NOT NULL,
                    order_status TEXT NOT NULL CHECK(order_status IN ('new', 'confirmed', 'fulfilled', 'delayed', 'cancelled')),
                    promised_date DATE NOT NULL,
                    fulfilled_date DATE,
                    store_id TEXT NOT NULL,
                    FOREIGN KEY (sku) REFERENCES product_catalog(sku)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sales_targets (
                    id SERIAL PRIMARY KEY,
                    target_month DATE NOT NULL,
                    category TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    revenue_target DOUBLE PRECISION NOT NULL,
                    gross_margin_target_pct DOUBLE PRECISION NOT NULL,
                    responsible_sector TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS supplier_deliveries (
                    id SERIAL PRIMARY KEY,
                    delivery_date DATE NOT NULL,
                    supplier_name TEXT NOT NULL,
                    po_code TEXT NOT NULL,
                    sku TEXT NOT NULL,
                    quantity_delivered DOUBLE PRECISION NOT NULL,
                    delivery_status TEXT NOT NULL CHECK(delivery_status IN ('on_time', 'late', 'partial', 'rejected')),
                    delay_days INTEGER NOT NULL,
                    invoice_number TEXT NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (sku) REFERENCES product_catalog(sku),
                    FOREIGN KEY (po_code) REFERENCES purchase_orders(po_code)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS product_price_history (
                    id SERIAL PRIMARY KEY,
                    changed_at DATE NOT NULL,
                    sku TEXT NOT NULL,
                    old_price DOUBLE PRECISION NOT NULL,
                    new_price DOUBLE PRECISION NOT NULL,
                    change_reason TEXT NOT NULL,
                    approved_by TEXT NOT NULL,
                    FOREIGN KEY (sku) REFERENCES product_catalog(sku)
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
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id SERIAL PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
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
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_memories (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    store_id TEXT,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS evolution_instance_state (
                    instance_id TEXT PRIMARY KEY,
                    instance_name TEXT,
                    instance_token TEXT,
                    last_event TEXT,
                    connection_status TEXT,
                    qr_code_base64 TEXT,
                    phone_jid TEXT,
                    push_name TEXT,
                    metadata_json TEXT,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS evolution_processed_messages (
                    instance_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (instance_id, message_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS whatsapp_allowed_contacts (
                    id SERIAL PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    phone_number TEXT NOT NULL UNIQUE,
                    notes TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMPTZ
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS whatsapp_blocked_contacts (
                    id SERIAL PRIMARY KEY,
                    phone_number TEXT NOT NULL UNIQUE,
                    push_name TEXT,
                    block_reason TEXT NOT NULL,
                    first_message_text TEXT,
                    last_message_text TEXT,
                    reply_sent BOOLEAN NOT NULL DEFAULT FALSE,
                    last_instance_id TEXT,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_product_catalog_sku ON product_catalog(sku)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_sale_date ON sales(sale_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_sku ON sales(sku)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_employees_sector_status ON employees(sector, status)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_absenteeism_event_date ON absenteeism_events(event_date)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_purchase_orders_date_status ON purchase_orders(order_date, status)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_purchase_orders_sku ON purchase_orders(sku)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_inventory_movements_date_sku ON inventory_movements(movement_date, sku)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_daily_stock_snapshot_date_sku ON daily_stock_snapshot(snapshot_date, sku)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_customer_orders_date_status ON customer_orders(order_date, order_status)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_customer_orders_sku ON customer_orders(sku)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_sales_targets_month_category ON sales_targets(target_month, category)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_supplier_deliveries_date_status ON supplier_deliveries(delivery_date, delivery_status)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_product_price_history_sku_date ON product_price_history(sku, changed_at)"
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
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_evolution_instance_state_name ON evolution_instance_state(instance_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_whatsapp_allowed_contacts_active ON whatsapp_allowed_contacts(is_active, user_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_whatsapp_blocked_contacts_updated_at ON whatsapp_blocked_contacts(updated_at DESC)"
            )
        connection.commit()


def seed_database(settings: Settings) -> dict[str, int]:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                TRUNCATE TABLE
                    product_price_history,
                    supplier_deliveries,
                    sales_targets,
                    customer_orders,
                    daily_stock_snapshot,
                    inventory_movements,
                    purchase_orders,
                    absenteeism_events,
                    sales,
                    employees,
                    product_catalog
                RESTART IDENTITY CASCADE
                """
            )
            demo_start_date = date(2026, 4, 17)
            demo_end_date = date(2026, 7, 17)
            demo_days = (demo_end_date - demo_start_date).days + 1

            products = [
                ("AP001", "Pastilha de freio dianteira ceramic", "freios", "autopecas", "jogo", "FreioMax Distribuidora", 78.90, 129.90, 64.64, 34.0, 12.0, "active", "2026-06-15"),
                ("AP002", "Disco de freio ventilado aro 14", "freios", "autopecas", "un", "MetalBrake", 92.50, 156.90, 69.62, 18.0, 8.0, "active", "2026-06-15"),
                ("AP003", "Oleo sintetico 5W30 1L", "lubrificantes", "autopecas", "lt", "LubriOne", 21.40, 36.90, 72.43, 72.0, 24.0, "active", "2026-06-15"),
                ("AP004", "Filtro de oleo universal", "filtros", "autopecas", "un", "FiltroTech", 14.80, 28.90, 95.27, 46.0, 15.0, "active", "2026-06-15"),
                ("AP005", "Bateria automotiva 60Ah", "eletrica", "autopecas", "un", "PowerVolt", 248.00, 379.90, 53.19, 9.0, 4.0, "active", "2026-06-15"),
                ("AP006", "Amortecedor dianteiro pressurizado", "suspensao", "autopecas", "un", "RidePro", 132.00, 214.90, 62.8, 16.0, 6.0, "active", "2026-06-15"),
                ("AP007", "Kit correia dentada completo", "motor", "autopecas", "kit", "MotorSync", 168.50, 279.90, 66.11, 11.0, 5.0, "active", "2026-06-15"),
                ("AP008", "Jogo de velas de ignicao iridium", "ignicao", "autopecas", "jogo", "SparkLine", 88.20, 149.90, 69.95, 21.0, 8.0, "active", "2026-06-15"),
                ("AP009", "Filtro de ar do motor", "filtros", "autopecas", "un", "FiltroTech", 16.70, 31.90, 91.02, 39.0, 14.0, "active", "2026-06-15"),
                ("AP010", "Palheta limpador 24 polegadas", "acessorios", "autopecas", "un", "VisionParts", 11.90, 24.90, 109.24, 54.0, 20.0, "active", "2026-06-15"),
                ("AP011", "Lampada halogena H7 12V", "eletrica", "autopecas", "par", "LumiCar", 18.30, 34.90, 90.71, 33.0, 12.0, "active", "2026-06-15"),
                ("AP012", "Aditivo para radiador 1L", "arrefecimento", "autopecas", "lt", "CoolFlow", 12.60, 25.90, 105.56, 28.0, 10.0, "active", "2026-06-15"),
                ("AP013", "Pivo de suspensao inferior", "suspensao", "autopecas", "un", "RidePro", 34.20, 68.90, 101.46, 17.0, 7.0, "active", "2026-06-15"),
                ("AP014", "Terminal de direcao", "direcao", "autopecas", "un", "SteerMax", 29.80, 59.90, 101.01, 13.0, 6.0, "active", "2026-06-15"),
                ("AP015", "Kit de embreagem completo", "transmissao", "autopecas", "kit", "TorqueDrive", 242.00, 398.90, 64.83, 8.0, 4.0, "active", "2026-06-15"),
                ("AP016", "Fluido de freio DOT4 500ml", "freios", "autopecas", "un", "FreioMax Distribuidora", 9.40, 19.90, 111.7, 31.0, 10.0, "active", "2026-06-15"),
                ("AP017", "Sensor ABS dianteiro", "eletrica", "autopecas", "un", "ElectroParts", 74.60, 132.90, 78.15, 10.0, 4.0, "active", "2026-06-15"),
                ("AP018", "Rolamento de roda traseira", "suspensao", "autopecas", "un", "RidePro", 58.20, 109.90, 88.83, 12.0, 5.0, "active", "2026-06-15"),
            ]
            products = [(*product[:12], demo_end_date.isoformat()) for product in products]
            cursor.executemany(
                """
                INSERT INTO product_catalog
                (
                    sku, description, category, department, unit_measure, supplier_name,
                    cost_price, selling_price, gross_margin_pct, current_stock_qty,
                    reorder_point_qty, status, last_inventory_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                products,
            )

            employees = [
                ("C1001", "Ana Paula Souza", "caixa", "Operadora de caixa", "a", "manha", "vendas_balcao,televendas", 44),
                ("C1002", "Bruno Henrique Lima", "vendas_balcao", "Vendedor tecnico senior", "a", "manha", "estoque,televendas", 44),
                ("C1003", "Carla Mendes Rocha", "vendas_balcao", "Vendedora tecnica", "a", "tarde", "caixa,televendas", 44),
                ("C1004", "Diego Martins", "recebimento", "Conferente de mercadorias", "a", "manha", "estoque,expedicao", 44),
                ("C1005", "Elaine Cristina", "caixa", "Fiscal de caixa", "a", "tarde", "vendas_balcao,televendas", 44),
                ("C1006", "Fabio Nogueira", "estoque", "Auxiliar de estoque", "a", "noite", "recebimento,expedicao", 44),
                ("C1007", "Gabriela Pires", "estoque", "Lider de estoque", "a", "manha", "recebimento,expedicao,vendas_balcao", 44),
                ("C1008", "Helio Barbosa", "expedicao", "Auxiliar de expedicao", "i", "manha", "estoque,recebimento", 44),
                ("C1009", "Isabela Freitas", "televendas", "Atendente de televendas", "a", "tarde", "vendas_balcao,caixa", 36),
                ("C1010", "Joao Victor Alves", "recebimento", "Auxiliar de carga", "a", "manha", "estoque,expedicao", 44),
                ("C1011", "Karen Ribeiro", "estoque", "Separadora de pedidos", "a", "noite", "expedicao,vendas_balcao", 36),
                ("C1012", "Lucas Ferreira", "caixa", "Assistente de loja", "a", "tarde", "televendas,vendas_balcao", 36),
                ("C1013", "Mariana Costa", "televendas", "Consultora de pecas", "a", "manha", "vendas_balcao,caixa", 44),
                ("C1014", "Rafael Gomes", "expedicao", "Motorista interno", "a", "tarde", "estoque,recebimento", 44),
            ]
            cursor.executemany(
                """
                INSERT INTO employees
                (
                    id_colaborador, employee_name, sector, role_name, status, primary_shift,
                    cross_trained_sectors, weekly_hours
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                employees,
            )

            payment_methods = ["pix", "credito", "debito", "dinheiro"]
            sales_channels = ["loja_fisica", "vendas_balcao", "televendas", "marketplace"]
            shifts = ["manha", "tarde", "noite"]
            sales = []
            for day_index in range(demo_days):
                current_date = demo_start_date + timedelta(days=day_index)
                for sale_offset in range(3):
                    product = products[(day_index * 3 + sale_offset) % len(products)]
                    sku = product[0]
                    description = product[1]
                    category = product[2]
                    unit_price = float(product[7])
                    quantity = float(((day_index + sale_offset * 2) % 7) + 1)
                    gross_revenue = round(quantity * unit_price, 2)
                    discount_pct = 0.04 if (day_index + sale_offset) % 5 == 0 else 0.015
                    discount_value = round(gross_revenue * discount_pct, 2)
                    net_revenue = round(gross_revenue - discount_value, 2)
                    payment_method = payment_methods[(day_index + sale_offset) % len(payment_methods)]
                    cash_generation = round(net_revenue * 0.97, 2) if payment_method == "credito" else net_revenue
                    sales.append(
                        (
                            current_date.isoformat(),
                            sku,
                            description,
                            category,
                            quantity,
                            unit_price,
                            gross_revenue,
                            discount_value,
                            net_revenue,
                            cash_generation,
                            payment_method,
                            sales_channels[(day_index + sale_offset) % len(sales_channels)],
                            shifts[(day_index + sale_offset) % len(shifts)],
                        )
                    )

            for product in products[:4]:
                quantity = 2.0 + float(products.index(product) % 3)
                gross_revenue = round(quantity * float(product[7]), 2)
                discount_value = round(gross_revenue * 0.02, 2)
                net_revenue = round(gross_revenue - discount_value, 2)
                sales.append(
                    (
                        demo_end_date.isoformat(),
                        product[0],
                        product[1],
                        product[2],
                        quantity,
                        float(product[7]),
                        gross_revenue,
                        discount_value,
                        net_revenue,
                        net_revenue,
                        "pix",
                        "vendas_balcao",
                        "tarde",
                    )
                )
            cursor.executemany(
                """
                INSERT INTO sales
                (
                    sale_date, sku, product_description, category, quantity_sold, unit_price,
                    gross_revenue, discount_value, net_revenue, cash_generation, payment_method,
                    sales_channel, shift
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                sales,
            )

            absence_types = ["consulta_medica", "falta_justificada", "atestado_medico", "licenca_curta"]
            absenteeism_events = []
            for event_index, day_index in enumerate(range(2, demo_days, 6)):
                current_date = demo_start_date + timedelta(days=day_index)
                employee = employees[event_index % len(employees)]
                absence_hours = 4.0 if event_index % 3 == 0 else 8.0
                priority = "alta" if event_index % 4 in (0, 1) else "media"
                absenteeism_events.append(
                    (
                        current_date.isoformat(),
                        employee[0],
                        employee[2],
                        employee[5],
                        absence_types[event_index % len(absence_types)],
                        absence_hours,
                        priority,
                        priority == "alta",
                        "Evento demonstrativo para cobertura operacional entre abril e julho de 2026.",
                    )
                )

            absenteeism_events.extend(
                [
                    (
                        demo_end_date.isoformat(),
                        "C1002",
                        "vendas_balcao",
                        "manha",
                        "atestado_medico",
                        8.0,
                        "alta",
                        True,
                        "Atendimento tecnico no balcao perdeu o vendedor de maior ticket medio no dia da demonstracao.",
                    ),
                    (
                        demo_end_date.isoformat(),
                        "C1013",
                        "televendas",
                        "manha",
                        "licenca_curta",
                        4.0,
                        "media",
                        True,
                        "Equipe de orcamento remoto ficou reduzida em horario de pico no dia da demonstracao.",
                    ),
                ]
            )
            cursor.executemany(
                """
                INSERT INTO absenteeism_events
                (
                    event_date, id_colaborador, sector, scheduled_shift, absence_type,
                    absence_hours, coverage_priority, replacement_required, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                absenteeism_events,
            )

            purchase_orders = []
            for order_index, day_index in enumerate(range(0, demo_days, 5), start=1):
                current_date = demo_start_date + timedelta(days=day_index)
                product = products[(order_index * 2) % len(products)]
                expected_delivery = current_date + timedelta(days=3 + (order_index % 4))
                status = "delivered"
                if expected_delivery > demo_end_date:
                    status = "open"
                elif order_index % 9 == 0:
                    status = "partial"
                quantity = float(12 + (order_index % 6) * 4)
                unit_cost = float(product[6])
                purchase_orders.append(
                    (
                        f"PO-2026-{order_index:04d}",
                        current_date.isoformat(),
                        expected_delivery.isoformat(),
                        product[5],
                        product[0],
                        quantity,
                        unit_cost,
                        round(quantity * unit_cost, 2),
                        status,
                        ["Ana Paula Souza", "Gabriela Pires", "Diego Martins"][order_index % 3],
                        "Pedido de reposicao planejado para sustentar cobertura de estoque.",
                    )
                )

            purchase_orders.append(
                (
                    "PO-2026-9999",
                    "2026-07-10",
                    demo_end_date.isoformat(),
                    "FreioMax Distribuidora",
                    "AP001",
                    24.0,
                    78.90,
                    round(24.0 * 78.90, 2),
                    "delivered",
                    "Gabriela Pires",
                    "Pedido critico entregue no dia da apresentacao para recompor freios.",
                )
            )
            cursor.executemany(
                """
                INSERT INTO purchase_orders
                (
                    po_code, order_date, expected_delivery_date, supplier_name, sku,
                    quantity_ordered, unit_cost, total_cost, status, buyer_name, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                purchase_orders,
            )

            supplier_deliveries = []
            for delivery_index, purchase_order in enumerate(purchase_orders, start=1):
                status = purchase_order[8]
                if status == "open":
                    continue
                expected_delivery = date.fromisoformat(purchase_order[2])
                delivery_date = expected_delivery + timedelta(days=1 if delivery_index % 7 == 0 else 0)
                if delivery_date > demo_end_date:
                    delivery_date = demo_end_date
                delivered_qty = float(purchase_order[5])
                delivery_status = "on_time"
                delay_days = max((delivery_date - expected_delivery).days, 0)
                if status == "partial":
                    delivered_qty = round(delivered_qty * 0.6, 2)
                    delivery_status = "partial"
                elif delay_days > 0:
                    delivery_status = "late"
                supplier_deliveries.append(
                    (
                        delivery_date.isoformat(),
                        purchase_order[3],
                        purchase_order[0],
                        purchase_order[4],
                        delivered_qty,
                        delivery_status,
                        delay_days,
                        f"NF-{20260000 + delivery_index}",
                        "Entrega registrada para acompanhamento de fornecedor e ruptura.",
                    )
                )
            cursor.executemany(
                """
                INSERT INTO supplier_deliveries
                (
                    delivery_date, supplier_name, po_code, sku, quantity_delivered,
                    delivery_status, delay_days, invoice_number, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                supplier_deliveries,
            )

            inventory_movements = []
            for day_index in range(demo_days):
                current_date = demo_start_date + timedelta(days=day_index)
                for movement_offset in range(2):
                    product = products[(day_index + movement_offset * 4) % len(products)]
                    quantity_delta = -float(((day_index + movement_offset) % 5) + 1)
                    stock_after_qty = max(0.0, float(product[9]) + 35.0 - day_index * 0.18 + quantity_delta)
                    inventory_movements.append(
                        (
                            current_date.isoformat(),
                            product[0],
                            "saida_venda",
                            quantity_delta,
                            round(stock_after_qty, 2),
                            "sales",
                            f"SALE-{day_index + 1:03d}-{movement_offset + 1}",
                            "Baixa automatica por venda.",
                        )
                    )
                if day_index % 5 == 0:
                    product = products[(day_index // 5) % len(products)]
                    quantity_delta = float(10 + (day_index % 4) * 3)
                    inventory_movements.append(
                        (
                            current_date.isoformat(),
                            product[0],
                            "entrada_compra",
                            quantity_delta,
                            round(float(product[9]) + quantity_delta, 2),
                            "purchase_orders",
                            f"PO-2026-{(day_index // 5) + 1:04d}",
                            "Entrada de compra planejada.",
                        )
                    )
            cursor.executemany(
                """
                INSERT INTO inventory_movements
                (
                    movement_date, sku, movement_type, quantity_delta, stock_after_qty,
                    reference_type, reference_code, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                inventory_movements,
            )

            daily_stock_snapshot = []
            for day_index in range(demo_days):
                current_date = demo_start_date + timedelta(days=day_index)
                for product_index, product in enumerate(products):
                    base_stock = float(product[9])
                    reorder_point = float(product[10])
                    available_qty = max(0.0, round(base_stock + 28.0 - day_index * 0.22 + (product_index % 5), 2))
                    reserved_qty = float((day_index + product_index) % 4)
                    days_of_cover = round(available_qty / max(1.0, 1.2 + (product_index % 5)), 1)
                    if available_qty == 0:
                        stock_status = "stockout"
                    elif available_qty <= reorder_point * 0.75:
                        stock_status = "critical"
                    elif available_qty <= reorder_point:
                        stock_status = "attention"
                    else:
                        stock_status = "ok"
                    daily_stock_snapshot.append(
                        (
                            current_date.isoformat(),
                            product[0],
                            available_qty,
                            reserved_qty,
                            reorder_point,
                            stock_status,
                            days_of_cover,
                        )
                    )
            cursor.executemany(
                """
                INSERT INTO daily_stock_snapshot
                (
                    snapshot_date, sku, available_qty, reserved_qty, reorder_point_qty,
                    stock_status, days_of_cover
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                daily_stock_snapshot,
            )

            customer_names = [
                "Auto Center Avenida",
                "Oficina Sao Miguel",
                "Mecanica Dois Irmaos",
                "Rapido Car Service",
                "Frota Norte Transportes",
                "Cliente Balcao Pessoa Fisica",
            ]
            customer_orders = []
            for day_index in range(demo_days):
                current_date = demo_start_date + timedelta(days=day_index)
                for order_offset in range(2):
                    product = products[(day_index * 2 + order_offset) % len(products)]
                    quantity = float(((day_index + order_offset) % 4) + 1)
                    order_value = round(quantity * float(product[7]), 2)
                    status = "fulfilled"
                    if day_index >= demo_days - 4 and order_offset == 1:
                        status = "confirmed"
                    elif day_index % 17 == 0:
                        status = "delayed"
                    promised_date = current_date + timedelta(days=1 + order_offset)
                    fulfilled_date = None if status in ("confirmed", "delayed") else current_date.isoformat()
                    customer_orders.append(
                        (
                            f"CO-2026-{day_index + 1:03d}-{order_offset + 1}",
                            current_date.isoformat(),
                            customer_names[(day_index + order_offset) % len(customer_names)],
                            sales_channels[(day_index + order_offset) % len(sales_channels)],
                            product[0],
                            quantity,
                            order_value,
                            status,
                            promised_date.isoformat(),
                            fulfilled_date,
                            "loja-matriz",
                        )
                    )
            cursor.executemany(
                """
                INSERT INTO customer_orders
                (
                    order_code, order_date, customer_name, channel, sku, quantity_ordered,
                    order_value, order_status, promised_date, fulfilled_date, store_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                customer_orders,
            )

            categories = sorted({str(product[2]) for product in products})
            target_months = [date(2026, 4, 1), date(2026, 5, 1), date(2026, 6, 1), date(2026, 7, 1)]
            sales_targets = []
            for month_index, target_month in enumerate(target_months):
                for category_index, category in enumerate(categories):
                    channel = sales_channels[(month_index + category_index) % len(sales_channels)]
                    sales_targets.append(
                        (
                            target_month.isoformat(),
                            category,
                            channel,
                            float(18000 + month_index * 1250 + category_index * 850),
                            float(42 + (category_index % 6) * 2),
                            "comercial",
                        )
                    )
            cursor.executemany(
                """
                INSERT INTO sales_targets
                (
                    target_month, category, channel, revenue_target,
                    gross_margin_target_pct, responsible_sector
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                sales_targets,
            )

            price_months = [date(2026, 4, 17), date(2026, 5, 17), date(2026, 6, 17), demo_end_date]
            product_price_history = []
            for product_index, product in enumerate(products):
                base_price = float(product[7])
                for month_index, changed_at in enumerate(price_months):
                    old_price = round(base_price * (0.94 + month_index * 0.015), 2)
                    new_price = round(base_price * (0.96 + month_index * 0.018), 2)
                    product_price_history.append(
                        (
                            changed_at.isoformat(),
                            product[0],
                            old_price,
                            new_price,
                            ["reajuste_fornecedor", "campanha_margem", "reposicionamento_competitivo", "revisao_julho"][month_index],
                            ["Elaine Cristina", "Gabriela Pires", "Bruno Henrique Lima"][product_index % 3],
                        )
                    )
            cursor.executemany(
                """
                INSERT INTO product_price_history
                (
                    changed_at, sku, old_price, new_price, change_reason, approved_by
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                product_price_history,
            )
        connection.commit()

    return {
        "product_catalog": len(products),
        "sales": len(sales),
        "employees": len(employees),
        "absenteeism_events": len(absenteeism_events),
        "purchase_orders": len(purchase_orders),
        "inventory_movements": len(inventory_movements),
        "daily_stock_snapshot": len(daily_stock_snapshot),
        "customer_orders": len(customer_orders),
        "sales_targets": len(sales_targets),
        "supplier_deliveries": len(supplier_deliveries),
        "product_price_history": len(product_price_history),
    }


def fetch_rows_for_indexing(settings: Settings) -> dict[str, list[DbRow]]:
    init_database(settings)
    rows_by_table: dict[str, list[DbRow]] = {}
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            for table_name in settings.source_table_list:
                safe_table_name = validate_table_name(table_name)
                query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(safe_table_name))
                cursor.execute(query)
                rows_by_table[table_name] = cursor.fetchall()
    return rows_by_table


def describe_schema(settings: Settings) -> str:
    init_database(settings)
    descriptions: list[str] = []
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            for table_name in settings.source_table_list:
                safe_table_name = validate_table_name(table_name)
                cursor.execute(
                    """
                    SELECT column_name, data_type, udt_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (safe_table_name,),
                )
                columns = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                      ON tc.constraint_name = kcu.constraint_name
                     AND tc.table_schema = kcu.table_schema
                    WHERE tc.table_schema = 'public'
                      AND tc.table_name = %s
                      AND tc.constraint_type = 'PRIMARY KEY'
                    """,
                    (safe_table_name,),
                )
                primary_keys = {row["column_name"] for row in cursor.fetchall()}

                descriptions.append(f"Table {safe_table_name}:")
                for column in columns:
                    type_name = column["data_type"]
                    if type_name == "USER-DEFINED":
                        type_name = column["udt_name"]
                    descriptions.append(
                        f"- {column['column_name']} ({type_name})"
                        + (" PRIMARY KEY" if column["column_name"] in primary_keys else "")
                    )
    return "\n".join(descriptions)


def run_read_only_query(settings: Settings, query: str) -> list[DbRow]:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchmany(settings.sql_max_rows)
    return rows


def upsert_conversation(
    settings: Settings,
    conversation_id: str,
    user_id: str,
    store_id: str | None = None,
    title: str | None = None,
) -> None:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO conversations (conversation_id, user_id, store_id, title)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (conversation_id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    store_id = COALESCE(EXCLUDED.store_id, conversations.store_id),
                    title = COALESCE(conversations.title, EXCLUDED.title),
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
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO conversation_messages (conversation_id, role, content)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (conversation_id, role, content),
            )
            message_id = int(cursor.fetchone()["id"])
            cursor.execute(
                """
                UPDATE conversations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE conversation_id = %s
                """,
                (conversation_id,),
            )
        connection.commit()
    return message_id


def fetch_conversation_messages(
    settings: Settings,
    conversation_id: str,
    limit: int | None = None,
    after_message_id: int | None = None,
) -> list[DbRow]:
    init_database(settings)
    query = """
        SELECT id, conversation_id, role, content, created_at
        FROM conversation_messages
        WHERE conversation_id = %s
    """
    parameters: list[object] = [conversation_id]

    if after_message_id is not None:
        query += " AND id > %s"
        parameters.append(after_message_id)

    query += " ORDER BY id ASC"

    if limit is not None:
        query += " LIMIT %s"
        parameters.append(limit)

    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            rows = cursor.fetchall()
    return rows


def fetch_recent_conversation_messages(
    settings: Settings,
    conversation_id: str,
    limit: int,
) -> list[DbRow]:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, conversation_id, role, content, created_at
                FROM conversation_messages
                WHERE conversation_id = %s
                ORDER BY id DESC
                LIMIT %s
                """,
                (conversation_id, limit),
            )
            rows = cursor.fetchall()
    return list(reversed(rows))


def count_conversation_messages(settings: Settings, conversation_id: str) -> int:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM conversation_messages WHERE conversation_id = %s",
                (conversation_id,),
            )
            row = cursor.fetchone()
    return int(row["total"])


def fetch_conversation_summary(settings: Settings, conversation_id: str) -> DbRow | None:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT conversation_id, summary, summarized_until_message_id, updated_at
                FROM conversation_summaries
                WHERE conversation_id = %s
                """,
                (conversation_id,),
            )
            row = cursor.fetchone()
    return row


def upsert_conversation_summary(
    settings: Settings,
    conversation_id: str,
    summary: str,
    summarized_until_message_id: int,
) -> None:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO conversation_summaries
                (conversation_id, summary, summarized_until_message_id, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (conversation_id) DO UPDATE SET
                    summary = EXCLUDED.summary,
                    summarized_until_message_id = EXCLUDED.summarized_until_message_id,
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
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_memories
                (user_id, store_id, memory_type, content, priority)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, store_id, memory_type, content, priority),
            )
            memory_id = int(cursor.fetchone()["id"])
        connection.commit()
    return memory_id


def fetch_user_memories(
    settings: Settings,
    user_id: str,
    limit: int,
    store_id: str | None = None,
) -> list[DbRow]:
    init_database(settings)
    query = """
        SELECT id, user_id, store_id, memory_type, content, priority, created_at, updated_at
        FROM user_memories
        WHERE user_id = %s
    """
    parameters: list[object] = [user_id]

    if store_id:
        query += " AND (store_id = %s OR store_id IS NULL)"
        parameters.append(store_id)

    query += " ORDER BY priority DESC, updated_at DESC, id DESC LIMIT %s"
    parameters.append(limit)

    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            rows = cursor.fetchall()
    return rows


def list_conversations(
    settings: Settings,
    user_id: str | None = None,
    limit: int = 20,
) -> list[DbRow]:
    init_database(settings)
    query = """
        SELECT conversation_id, user_id, store_id, title, created_at, updated_at
        FROM conversations
    """
    parameters: list[object] = []

    if user_id:
        query += " WHERE user_id = %s"
        parameters.append(user_id)

    query += " ORDER BY updated_at DESC LIMIT %s"
    parameters.append(limit)

    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            rows = cursor.fetchall()
    return rows


def fetch_conversation(settings: Settings, conversation_id: str) -> DbRow | None:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT conversation_id, user_id, store_id, title, created_at, updated_at
                FROM conversations
                WHERE conversation_id = %s
                """,
                (conversation_id,),
            )
            row = cursor.fetchone()
    return row


def upsert_evolution_instance_state(
    settings: Settings,
    instance_id: str,
    instance_name: str | None = None,
    instance_token: str | None = None,
    last_event: str | None = None,
    connection_status: str | None = None,
    qr_code_base64: str | None = None,
    phone_jid: str | None = None,
    push_name: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    init_database(settings)
    metadata_json = json.dumps(metadata, ensure_ascii=True) if metadata is not None else None
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO evolution_instance_state
                (
                    instance_id,
                    instance_name,
                    instance_token,
                    last_event,
                    connection_status,
                    qr_code_base64,
                    phone_jid,
                    push_name,
                    metadata_json,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (instance_id) DO UPDATE SET
                    instance_name = COALESCE(EXCLUDED.instance_name, evolution_instance_state.instance_name),
                    instance_token = COALESCE(EXCLUDED.instance_token, evolution_instance_state.instance_token),
                    last_event = COALESCE(EXCLUDED.last_event, evolution_instance_state.last_event),
                    connection_status = COALESCE(EXCLUDED.connection_status, evolution_instance_state.connection_status),
                    qr_code_base64 = COALESCE(EXCLUDED.qr_code_base64, evolution_instance_state.qr_code_base64),
                    phone_jid = COALESCE(EXCLUDED.phone_jid, evolution_instance_state.phone_jid),
                    push_name = COALESCE(EXCLUDED.push_name, evolution_instance_state.push_name),
                    metadata_json = COALESCE(EXCLUDED.metadata_json, evolution_instance_state.metadata_json),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    instance_id,
                    instance_name,
                    instance_token,
                    last_event,
                    connection_status,
                    qr_code_base64,
                    phone_jid,
                    push_name,
                    metadata_json,
                ),
            )
        connection.commit()


def fetch_evolution_instance_state(settings: Settings, instance_id: str) -> DbRow | None:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    instance_id,
                    instance_name,
                    instance_token,
                    last_event,
                    connection_status,
                    qr_code_base64,
                    phone_jid,
                    push_name,
                    metadata_json,
                    updated_at
                FROM evolution_instance_state
                WHERE instance_id = %s
                """,
                (instance_id,),
            )
            row = cursor.fetchone()
    return row


def fetch_evolution_instance_state_by_name(
    settings: Settings, instance_name: str
) -> DbRow | None:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    instance_id,
                    instance_name,
                    instance_token,
                    last_event,
                    connection_status,
                    qr_code_base64,
                    phone_jid,
                    push_name,
                    metadata_json,
                    updated_at
                FROM evolution_instance_state
                WHERE instance_name = %s
                """,
                (instance_name,),
            )
            row = cursor.fetchone()
    return row


def list_evolution_instance_states(settings: Settings) -> list[DbRow]:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    instance_id,
                    instance_name,
                    instance_token,
                    last_event,
                    connection_status,
                    qr_code_base64,
                    phone_jid,
                    push_name,
                    metadata_json,
                    updated_at
                FROM evolution_instance_state
                ORDER BY updated_at DESC
                """
            )
            rows = cursor.fetchall()
    return rows


def register_processed_evolution_message(
    settings: Settings,
    instance_id: str,
    message_id: str,
) -> bool:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO evolution_processed_messages (instance_id, message_id)
                VALUES (%s, %s)
                ON CONFLICT (instance_id, message_id) DO NOTHING
                RETURNING message_id
                """,
                (instance_id, message_id),
            )
            row = cursor.fetchone()
        connection.commit()
    return row is not None


def upsert_whatsapp_allowed_contact(
    settings: Settings,
    user_name: str,
    phone_number: str,
    notes: str | None = None,
    is_active: bool = True,
) -> DbRow:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO whatsapp_allowed_contacts (user_name, phone_number, notes, is_active)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (phone_number) DO UPDATE SET
                    user_name = EXCLUDED.user_name,
                    notes = EXCLUDED.notes,
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING
                    id,
                    user_name,
                    phone_number,
                    notes,
                    is_active,
                    created_at,
                    updated_at,
                    last_seen_at
                """,
                (user_name, phone_number, notes, is_active),
            )
            row = cursor.fetchone()
        connection.commit()
    return row


def set_whatsapp_allowed_contact_active(
    settings: Settings,
    phone_number: str,
    is_active: bool,
) -> DbRow | None:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE whatsapp_allowed_contacts
                SET
                    is_active = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE phone_number = %s
                RETURNING
                    id,
                    user_name,
                    phone_number,
                    notes,
                    is_active,
                    created_at,
                    updated_at,
                    last_seen_at
                """,
                (is_active, phone_number),
            )
            row = cursor.fetchone()
        connection.commit()
    return row


def fetch_whatsapp_allowed_contact(settings: Settings, phone_number: str) -> DbRow | None:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    user_name,
                    phone_number,
                    notes,
                    is_active,
                    created_at,
                    updated_at,
                    last_seen_at
                FROM whatsapp_allowed_contacts
                WHERE phone_number = %s
                """,
                (phone_number,),
            )
            row = cursor.fetchone()
    return row


def list_whatsapp_allowed_contacts(
    settings: Settings,
    active_only: bool = True,
) -> list[DbRow]:
    init_database(settings)
    query = """
        SELECT
            id,
            user_name,
            phone_number,
            notes,
            is_active,
            created_at,
            updated_at,
            last_seen_at
        FROM whatsapp_allowed_contacts
    """
    parameters: list[object] = []
    if active_only:
        query += " WHERE is_active = TRUE"
    query += " ORDER BY user_name ASC, phone_number ASC"
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            rows = cursor.fetchall()
    return rows


def count_active_whatsapp_allowed_contacts(settings: Settings) -> int:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM whatsapp_allowed_contacts
                WHERE is_active = TRUE
                """
            )
            row = cursor.fetchone()
    return int(row["total"])


def touch_whatsapp_allowed_contact_seen(settings: Settings, phone_number: str) -> None:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE whatsapp_allowed_contacts
                SET
                    last_seen_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE phone_number = %s
                """,
                (phone_number,),
            )
        connection.commit()


def fetch_whatsapp_blocked_contact(settings: Settings, phone_number: str) -> DbRow | None:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    phone_number,
                    push_name,
                    block_reason,
                    first_message_text,
                    last_message_text,
                    reply_sent,
                    last_instance_id,
                    created_at,
                    updated_at,
                    last_seen_at
                FROM whatsapp_blocked_contacts
                WHERE phone_number = %s
                """,
                (phone_number,),
            )
            row = cursor.fetchone()
    return row


def upsert_whatsapp_blocked_contact(
    settings: Settings,
    phone_number: str,
    block_reason: str,
    push_name: str | None = None,
    message_text: str | None = None,
    instance_id: str | None = None,
) -> tuple[DbRow, bool]:
    init_database(settings)
    existing = fetch_whatsapp_blocked_contact(settings, phone_number)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            if existing:
                cursor.execute(
                    """
                    UPDATE whatsapp_blocked_contacts
                    SET
                        push_name = COALESCE(%s, push_name),
                        block_reason = %s,
                        last_message_text = COALESCE(%s, last_message_text),
                        last_instance_id = COALESCE(%s, last_instance_id),
                        updated_at = CURRENT_TIMESTAMP,
                        last_seen_at = CURRENT_TIMESTAMP
                    WHERE phone_number = %s
                    RETURNING
                        id,
                        phone_number,
                        push_name,
                        block_reason,
                        first_message_text,
                        last_message_text,
                        reply_sent,
                        last_instance_id,
                        created_at,
                        updated_at,
                        last_seen_at
                    """,
                    (push_name, block_reason, message_text, instance_id, phone_number),
                )
                row = cursor.fetchone()
                created = False
            else:
                cursor.execute(
                    """
                    INSERT INTO whatsapp_blocked_contacts
                    (
                        phone_number,
                        push_name,
                        block_reason,
                        first_message_text,
                        last_message_text,
                        last_instance_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING
                        id,
                        phone_number,
                        push_name,
                        block_reason,
                        first_message_text,
                        last_message_text,
                        reply_sent,
                        last_instance_id,
                        created_at,
                        updated_at,
                        last_seen_at
                    """,
                    (phone_number, push_name, block_reason, message_text, message_text, instance_id),
                )
                row = cursor.fetchone()
                created = True
        connection.commit()
    return row, created


def mark_whatsapp_blocked_contact_replied(settings: Settings, phone_number: str) -> None:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE whatsapp_blocked_contacts
                SET
                    reply_sent = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE phone_number = %s
                """,
                (phone_number,),
            )
        connection.commit()


def delete_whatsapp_blocked_contact(settings: Settings, phone_number: str) -> bool:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM whatsapp_blocked_contacts WHERE phone_number = %s RETURNING phone_number",
                (phone_number,),
            )
            row = cursor.fetchone()
        connection.commit()
    return row is not None


def list_whatsapp_blocked_contacts(
    settings: Settings,
    limit: int = 100,
) -> list[DbRow]:
    init_database(settings)
    with postgres_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    phone_number,
                    push_name,
                    block_reason,
                    first_message_text,
                    last_message_text,
                    reply_sent,
                    last_instance_id,
                    created_at,
                    updated_at,
                    last_seen_at
                FROM whatsapp_blocked_contacts
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cursor.fetchall()
    return rows

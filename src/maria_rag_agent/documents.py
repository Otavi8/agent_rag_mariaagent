from __future__ import annotations

from typing import Any

from langchain_core.documents import Document


def translate_employee_status(status: str) -> str:
    mapping = {
        "a": "ativo",
        "i": "inativo",
    }
    return mapping.get(status.lower(), status)


def render_row(table_name: str, row: dict[str, Any]) -> str:
    if table_name == "product_catalog":
        return (
            "Tipo de documento: cadastro de produto\n"
            f"SKU: {row['sku']}\n"
            f"Descricao: {row['description']}\n"
            f"Categoria: {row['category']}\n"
            f"Departamento: {row['department']}\n"
            f"Unidade de medida: {row['unit_measure']}\n"
            f"Fornecedor: {row['supplier_name']}\n"
            f"Preco de custo: {row['cost_price']}\n"
            f"Preco de venda: {row['selling_price']}\n"
            f"Margem bruta percentual: {row['gross_margin_pct']}\n"
            f"Estoque atual: {row['current_stock_qty']}\n"
            f"Ponto de reposicao: {row['reorder_point_qty']}\n"
            f"Status: {row['status']}\n"
            f"Ultimo inventario em: {row['last_inventory_at']}"
        )

    if table_name == "sales":
        return (
            "Tipo de documento: registro de venda\n"
            f"Data da venda: {row['sale_date']}\n"
            f"SKU: {row['sku']}\n"
            f"Descricao do produto: {row['product_description']}\n"
            f"Categoria: {row['category']}\n"
            f"Quantidade vendida: {row['quantity_sold']}\n"
            f"Preco unitario: {row['unit_price']}\n"
            f"Receita bruta: {row['gross_revenue']}\n"
            f"Valor de desconto: {row['discount_value']}\n"
            f"Receita liquida: {row['net_revenue']}\n"
            f"Geracao de caixa: {row['cash_generation']}\n"
            f"Forma de pagamento: {row['payment_method']}\n"
            f"Canal de venda: {row['sales_channel']}\n"
            f"Turno: {row['shift']}"
        )

    if table_name == "employees":
        return (
            "Tipo de documento: cadastro de funcionario\n"
            f"Id do colaborador: {row['id_colaborador']}\n"
            f"Nome do colaborador: {row['employee_name']}\n"
            f"Setor: {row['sector']}\n"
            f"Cargo: {row['role_name']}\n"
            f"Status: {translate_employee_status(row['status'])} (codigo original: {row['status']})\n"
            f"Turno principal: {row['primary_shift']}\n"
            f"Setores com treinamento cruzado: {row['cross_trained_sectors'] or 'n/a'}\n"
            f"Carga horaria semanal: {row['weekly_hours']}"
        )

    if table_name == "absenteeism_events":
        return (
            "Tipo de documento: evento de absenteismo\n"
            f"Data do evento: {row['event_date']}\n"
            f"Id do colaborador: {row['id_colaborador']}\n"
            f"Setor: {row['sector']}\n"
            f"Turno previsto: {row['scheduled_shift']}\n"
            f"Tipo de ausencia: {row['absence_type']}\n"
            f"Horas de ausencia: {row['absence_hours']}\n"
            f"Prioridade de cobertura: {row['coverage_priority']}\n"
            f"Reposicao obrigatoria: {row['replacement_required']}\n"
            f"Observacoes: {row['notes'] or 'n/a'}"
        )

    if table_name == "purchase_orders":
        return (
            "Tipo de documento: pedido de compra\n"
            f"Codigo do pedido: {row['po_code']}\n"
            f"Data do pedido: {row['order_date']}\n"
            f"Data prevista de entrega: {row['expected_delivery_date']}\n"
            f"Fornecedor: {row['supplier_name']}\n"
            f"SKU: {row['sku']}\n"
            f"Quantidade pedida: {row['quantity_ordered']}\n"
            f"Custo unitario: {row['unit_cost']}\n"
            f"Custo total: {row['total_cost']}\n"
            f"Status do pedido: {row['status']}\n"
            f"Comprador responsavel: {row['buyer_name']}\n"
            f"Observacoes: {row['notes'] or 'n/a'}"
        )

    if table_name == "inventory_movements":
        return (
            "Tipo de documento: movimentacao de estoque\n"
            f"Data da movimentacao: {row['movement_date']}\n"
            f"SKU: {row['sku']}\n"
            f"Tipo de movimentacao: {row['movement_type']}\n"
            f"Quantidade movimentada: {row['quantity_delta']}\n"
            f"Estoque apos movimentacao: {row['stock_after_qty']}\n"
            f"Tipo de referencia: {row['reference_type']}\n"
            f"Codigo de referencia: {row['reference_code'] or 'n/a'}\n"
            f"Observacoes: {row['notes'] or 'n/a'}"
        )

    if table_name == "daily_stock_snapshot":
        return (
            "Tipo de documento: snapshot diario de estoque\n"
            f"Data do snapshot: {row['snapshot_date']}\n"
            f"SKU: {row['sku']}\n"
            f"Quantidade disponivel: {row['available_qty']}\n"
            f"Quantidade reservada: {row['reserved_qty']}\n"
            f"Ponto de reposicao: {row['reorder_point_qty']}\n"
            f"Status do estoque: {row['stock_status']}\n"
            f"Dias de cobertura: {row['days_of_cover']}"
        )

    if table_name == "customer_orders":
        return (
            "Tipo de documento: pedido de cliente\n"
            f"Codigo do pedido: {row['order_code']}\n"
            f"Data do pedido: {row['order_date']}\n"
            f"Cliente: {row['customer_name']}\n"
            f"Canal: {row['channel']}\n"
            f"SKU: {row['sku']}\n"
            f"Quantidade pedida: {row['quantity_ordered']}\n"
            f"Valor do pedido: {row['order_value']}\n"
            f"Status do pedido: {row['order_status']}\n"
            f"Data prometida: {row['promised_date']}\n"
            f"Data atendida: {row['fulfilled_date'] or 'n/a'}\n"
            f"Loja: {row['store_id']}"
        )

    if table_name == "sales_targets":
        return (
            "Tipo de documento: meta comercial\n"
            f"Mes da meta: {row['target_month']}\n"
            f"Categoria: {row['category']}\n"
            f"Canal: {row['channel']}\n"
            f"Meta de receita: {row['revenue_target']}\n"
            f"Meta de margem bruta percentual: {row['gross_margin_target_pct']}\n"
            f"Setor responsavel: {row['responsible_sector']}"
        )

    if table_name == "supplier_deliveries":
        return (
            "Tipo de documento: entrega de fornecedor\n"
            f"Data da entrega: {row['delivery_date']}\n"
            f"Fornecedor: {row['supplier_name']}\n"
            f"Codigo do pedido de compra: {row['po_code']}\n"
            f"SKU: {row['sku']}\n"
            f"Quantidade entregue: {row['quantity_delivered']}\n"
            f"Status da entrega: {row['delivery_status']}\n"
            f"Dias de atraso: {row['delay_days']}\n"
            f"Numero da nota fiscal: {row['invoice_number']}\n"
            f"Observacoes: {row['notes'] or 'n/a'}"
        )

    if table_name == "product_price_history":
        return (
            "Tipo de documento: historico de preco de produto\n"
            f"Data da alteracao: {row['changed_at']}\n"
            f"SKU: {row['sku']}\n"
            f"Preco anterior: {row['old_price']}\n"
            f"Preco novo: {row['new_price']}\n"
            f"Motivo da alteracao: {row['change_reason']}\n"
            f"Aprovado por: {row['approved_by']}"
        )

    lines = [f"Tipo de documento: linha de banco da tabela {table_name}"]
    for key in row.keys():
        lines.append(f"{key}: {row[key]}")
    return "\n".join(lines)


def build_documents(rows_by_table: dict[str, list[dict[str, Any]]]) -> list[Document]:
    documents: list[Document] = []
    for table_name, rows in rows_by_table.items():
        for row in rows:
            record_id = row["id"] if "id" in row.keys() else "unknown"
            source = table_name
            title = None
            if "description" in row.keys():
                title = row["description"]
            elif "employee_name" in row.keys():
                title = row["employee_name"]
            elif "product_description" in row.keys():
                title = row["product_description"]
            elif "po_code" in row.keys():
                title = row["po_code"]
            elif "order_code" in row.keys():
                title = row["order_code"]
            elif "supplier_name" in row.keys():
                title = row["supplier_name"]
            elif "sku" in row.keys():
                title = row["sku"]
            documents.append(
                Document(
                    page_content=render_row(table_name, row),
                    metadata={
                        "table": table_name,
                        "record_id": record_id,
                        "source": source,
                        "title": title,
                    },
                )
            )
    return documents

from __future__ import annotations

import sqlite3

from langchain_core.documents import Document


def render_row(table_name: str, row: sqlite3.Row) -> str:
    if table_name == "product_catalog":
        return (
            "Document type: product catalog item\n"
            f"SKU: {row['sku']}\n"
            f"Description: {row['description']}\n"
            f"Category: {row['category']}\n"
            f"Department: {row['department']}\n"
            f"Unit measure: {row['unit_measure']}\n"
            f"Supplier: {row['supplier_name']}\n"
            f"Cost price: {row['cost_price']}\n"
            f"Selling price: {row['selling_price']}\n"
            f"Gross margin pct: {row['gross_margin_pct']}\n"
            f"Current stock qty: {row['current_stock_qty']}\n"
            f"Reorder point qty: {row['reorder_point_qty']}\n"
            f"Status: {row['status']}\n"
            f"Last inventory at: {row['last_inventory_at']}"
        )

    if table_name == "sales":
        return (
            "Document type: sales record\n"
            f"Sale date: {row['sale_date']}\n"
            f"SKU: {row['sku']}\n"
            f"Product description: {row['product_description']}\n"
            f"Category: {row['category']}\n"
            f"Quantity sold: {row['quantity_sold']}\n"
            f"Unit price: {row['unit_price']}\n"
            f"Gross revenue: {row['gross_revenue']}\n"
            f"Discount value: {row['discount_value']}\n"
            f"Net revenue: {row['net_revenue']}\n"
            f"Cash generation: {row['cash_generation']}\n"
            f"Payment method: {row['payment_method']}\n"
            f"Sales channel: {row['sales_channel']}\n"
            f"Shift: {row['shift']}"
        )

    if table_name == "employees":
        return (
            "Document type: employee registry\n"
            f"Employee id: {row['id_colaborador']}\n"
            f"Employee name: {row['employee_name']}\n"
            f"Sector: {row['sector']}\n"
            f"Role: {row['role_name']}\n"
            f"Status: {row['status']}\n"
            f"Primary shift: {row['primary_shift']}\n"
            f"Cross trained sectors: {row['cross_trained_sectors'] or 'n/a'}\n"
            f"Weekly hours: {row['weekly_hours']}"
        )

    if table_name == "absenteeism_events":
        return (
            "Document type: absenteeism event\n"
            f"Event date: {row['event_date']}\n"
            f"Employee id: {row['id_colaborador']}\n"
            f"Sector: {row['sector']}\n"
            f"Scheduled shift: {row['scheduled_shift']}\n"
            f"Absence type: {row['absence_type']}\n"
            f"Absence hours: {row['absence_hours']}\n"
            f"Coverage priority: {row['coverage_priority']}\n"
            f"Replacement required: {row['replacement_required']}\n"
            f"Notes: {row['notes'] or 'n/a'}"
        )

    lines = [f"Document type: database row from {table_name}"]
    for key in row.keys():
        lines.append(f"{key}: {row[key]}")
    return "\n".join(lines)


def build_documents(rows_by_table: dict[str, list[sqlite3.Row]]) -> list[Document]:
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

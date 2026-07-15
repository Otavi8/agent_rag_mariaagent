from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .runtime import configure_runtime

configure_runtime()

from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware, ToolCallLimitMiddleware
from langchain_openai import ChatOpenAI

from .config import Settings
from .database import describe_schema, run_read_only_query
from .guardrails import GuardrailViolation, mask_output, validate_question
from .memory import (
    ConversationSession,
    build_memory_messages,
    ensure_conversation,
    maybe_refresh_conversation_summary,
    store_turn,
)
from .observability import (
    get_langfuse_callbacks,
    get_tool_trace,
    record_tool_call,
    reset_tool_trace,
    restore_tool_trace,
    timed_agent_request,
)
from .prompts import build_system_prompt
from .tools import build_tools


@dataclass
class AgentReply:
    answer: str
    conversation_id: str
    user_id: str
    store_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


def build_chat_model(settings: Settings):
    provider = settings.llm_provider.lower()

    if provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
        return ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.openai_api_key,
        )

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError as exc:
            raise RuntimeError(
                "To use LLM_PROVIDER=ollama, install the optional dependency: pip install -e .[ollama]"
            ) from exc

        return ChatOllama(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            base_url=settings.ollama_base_url,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")


def build_middleware(settings: Settings) -> list[Any]:
    middleware: list[Any] = [
        ToolCallLimitMiddleware(run_limit=settings.max_tool_calls, exit_behavior="end")
    ]

    if settings.mask_emails:
        middleware.append(
            PIIMiddleware("email", strategy="redact", apply_to_input=True, apply_to_output=True)
        )

    if settings.mask_phones:
        middleware.append(
            PIIMiddleware(
                "phone_number",
                detector=r"\+?\d{1,3}[\s.-]?(?:\(?\d{2}\)?[\s.-]?)?\d{4,5}[\s.-]?\d{4}",
                strategy="mask",
                apply_to_input=True,
                apply_to_output=True,
            )
        )

    if settings.mask_cpfs:
        middleware.append(
            PIIMiddleware(
                "cpf",
                detector=r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b",
                strategy="redact",
                apply_to_input=True,
                apply_to_output=True,
            )
        )

    return middleware


def build_rag_agent(settings: Settings, model=None):
    schema = describe_schema(settings)
    system_prompt = build_system_prompt(
        schema_description=schema,
        require_source_attribution=settings.require_source_attribution,
    )

    return create_agent(
        model=model or build_chat_model(settings),
        tools=build_tools(settings),
        system_prompt=system_prompt,
        middleware=build_middleware(settings),
    )


def extract_answer(result: dict[str, Any]) -> str:
    messages = result.get("messages", [])
    if not messages:
        return "No response was produced by the agent."

    final_message = messages[-1]
    content = getattr(final_message, "content", final_message)

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(part for part in parts if part)

    return str(content)


def can_answer_stock_inventory_directly(question: str) -> bool:
    normalized = question.lower()
    stock_terms = ("estoque", "disponivel", "disponiveis")
    product_terms = ("produto", "produtos", "sku", "peca", "pecas", "itens")
    intent_terms = ("temos", "quais", "listar", "lista", "saber")
    specific_terms = (
        "critico",
        "criticos",
        "ruptura",
        "reposicao",
        "reposicoes",
        "baixo",
        "abaixo",
        "risco",
    )
    return (
        any(term in normalized for term in stock_terms)
        and any(term in normalized for term in product_terms)
        and any(term in normalized for term in intent_terms)
        and not any(term in normalized for term in specific_terms)
    )


def answer_stock_inventory_directly(settings: Settings) -> str:
    limit = max(1, min(settings.sql_max_rows, 50))
    query = f"""
        WITH latest_snapshot AS (
            SELECT MAX(snapshot_date) AS snapshot_date
            FROM daily_stock_snapshot
        )
        SELECT
            s.snapshot_date,
            p.sku,
            p.description AS product_name,
            p.category,
            s.available_qty,
            s.reserved_qty,
            s.reorder_point_qty,
            s.stock_status,
            s.days_of_cover
        FROM daily_stock_snapshot s
        JOIN product_catalog p ON p.sku = s.sku
        WHERE s.snapshot_date = (SELECT snapshot_date FROM latest_snapshot)
          AND s.available_qty > 0
        ORDER BY
            CASE s.stock_status
                WHEN 'critical' THEN 1
                WHEN 'attention' THEN 2
                WHEN 'ok' THEN 3
                ELSE 4
            END,
            s.available_qty ASC,
            p.description ASC
        LIMIT {limit}
    """
    rows = run_read_only_query(settings, query)
    record_tool_call("sql_read_only_query", query, rows)

    if not rows:
        return (
            "Nao encontrei produtos com estoque disponivel no snapshot mais recente. "
            "(Fonte: daily_stock_snapshot e product_catalog)"
        )

    snapshot_date = rows[0].get("snapshot_date")
    lines = [
        f"Encontrei {len(rows)} produto(s) com estoque disponivel no snapshot de {snapshot_date}:"
    ]
    for row in rows:
        lines.append(
            "- "
            f"{row['sku']} - {row['product_name']} ({row['category']}): "
            f"{row['available_qty']} disponivel, {row['reserved_qty']} reservado, "
            f"status {row['stock_status']}, cobertura de {row['days_of_cover']} dia(s)."
        )
    lines.append("(Fonte: daily_stock_snapshot e product_catalog)")
    return "\n".join(lines)


def can_answer_top_selling_items_directly(question: str) -> bool:
    normalized = question.lower()
    subject_terms = ("item", "itens", "produto", "produtos", "sku", "peca", "pecas")
    ranking_terms = (
        "mais vendido",
        "mais vendidos",
        "vendem mais",
        "venderam mais",
        "top vendas",
        "campeoes de venda",
        "campeao de venda",
    )
    return any(term in normalized for term in subject_terms) and any(
        term in normalized for term in ranking_terms
    )


def answer_top_selling_items_directly(settings: Settings) -> str:
    limit = max(1, min(settings.sql_max_rows, 20))
    query = f"""
        SELECT
            (SELECT MIN(sale_date) FROM sales) AS period_start,
            (SELECT MAX(sale_date) FROM sales) AS period_end,
            sku,
            product_description,
            category,
            SUM(quantity_sold) AS total_quantity_sold,
            SUM(net_revenue) AS total_net_revenue,
            COUNT(*) AS sale_count
        FROM sales
        GROUP BY sku, product_description, category
        ORDER BY total_quantity_sold DESC, total_net_revenue DESC, product_description ASC
        LIMIT {limit}
    """
    rows = run_read_only_query(settings, query)
    record_tool_call("sql_read_only_query", query, rows)

    if not rows:
        return "Nao encontrei vendas cadastradas para montar o ranking de itens mais vendidos. (Fonte: sales)"

    period_start = rows[0].get("period_start")
    period_end = rows[0].get("period_end")
    lines = [
        (
            "Os itens mais vendidos por quantidade, considerando o periodo "
            f"de {period_start} a {period_end}, sao:"
        )
    ]
    for index, row in enumerate(rows, start=1):
        total_quantity = row["total_quantity_sold"]
        total_revenue = row["total_net_revenue"]
        lines.append(
            f"{index}. {row['sku']} - {row['product_description']} ({row['category']}): "
            f"{total_quantity} unidade(s), receita liquida de R$ {total_revenue:,.2f}, "
            f"{row['sale_count']} venda(s)."
        )
    lines.append("(Fonte: tabela sales)")
    return "\n".join(lines)


def ask_agent(
    question: str,
    settings: Settings,
    conversation_id: str | None = None,
    user_id: str = "default-user",
    store_id: str | None = None,
    channel: str = "api",
) -> AgentReply:
    cleaned_question = validate_question(question, settings)
    session: ConversationSession = ensure_conversation(
        settings=settings,
        conversation_id=conversation_id,
        user_id=user_id,
        store_id=store_id,
        title=cleaned_question[:80],
    )

    if can_answer_stock_inventory_directly(cleaned_question):
        token = reset_tool_trace()
        try:
            with timed_agent_request(channel):
                answer = answer_stock_inventory_directly(settings)
            tool_calls = get_tool_trace()
        finally:
            restore_tool_trace(token)

        masked_answer = mask_output(answer, settings)
        store_turn(
            settings=settings,
            conversation_id=session.conversation_id,
            user_text=cleaned_question,
            assistant_text=masked_answer,
        )
        return AgentReply(
            answer=masked_answer,
            conversation_id=session.conversation_id,
            user_id=session.user_id,
            store_id=session.store_id,
            tool_calls=tool_calls,
        )

    if can_answer_top_selling_items_directly(cleaned_question):
        token = reset_tool_trace()
        try:
            with timed_agent_request(channel):
                answer = answer_top_selling_items_directly(settings)
            tool_calls = get_tool_trace()
        finally:
            restore_tool_trace(token)

        masked_answer = mask_output(answer, settings)
        store_turn(
            settings=settings,
            conversation_id=session.conversation_id,
            user_text=cleaned_question,
            assistant_text=masked_answer,
        )
        return AgentReply(
            answer=masked_answer,
            conversation_id=session.conversation_id,
            user_id=session.user_id,
            store_id=session.store_id,
            tool_calls=tool_calls,
        )

    model = build_chat_model(settings)
    agent = build_rag_agent(settings, model=model)
    memory_messages = build_memory_messages(
        settings=settings,
        conversation_id=session.conversation_id,
        user_id=session.user_id,
        store_id=session.store_id,
    )
    token = reset_tool_trace()
    try:
        with timed_agent_request(channel):
            result = agent.invoke(
                {
                    "messages": memory_messages
                    + [
                        {
                            "role": "user",
                            "content": cleaned_question,
                        }
                    ]
                },
                config={
                    "callbacks": get_langfuse_callbacks(settings),
                    "metadata": {
                        "conversation_id": session.conversation_id,
                        "user_id": session.user_id,
                        "store_id": session.store_id,
                    },
                },
            )
        tool_calls = get_tool_trace()
    finally:
        restore_tool_trace(token)

    answer = extract_answer(result)

    if not answer.strip():
        raise GuardrailViolation("The agent returned an empty answer.")

    masked_answer = mask_output(answer, settings)
    store_turn(
        settings=settings,
        conversation_id=session.conversation_id,
        user_text=cleaned_question,
        assistant_text=masked_answer,
    )
    maybe_refresh_conversation_summary(
        settings=settings,
        conversation_id=session.conversation_id,
        model=model,
    )

    return AgentReply(
        answer=masked_answer,
        conversation_id=session.conversation_id,
        user_id=session.user_id,
        store_id=session.store_id,
        tool_calls=tool_calls,
    )

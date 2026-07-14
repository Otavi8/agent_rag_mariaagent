from __future__ import annotations

import json

from langchain_core.tools import tool

from .config import Settings
from .database import run_read_only_query
from .guardrails import (
    GuardrailViolation,
    ensure_minimum_context,
    format_sources,
    trim_documents,
    validate_question,
    validate_sql_query,
)
from .observability import record_tool_call
from .vectorstore import build_vector_store


def build_tools(settings: Settings):
    tools = []

    if settings.enable_vector_tool:
        vector_store = build_vector_store(settings)

        @tool
        def semantic_search(query: str) -> str:
            """Search the vector database for semantic context from indexed records."""

            cleaned_query = validate_question(query, settings)
            try:
                documents = vector_store.max_marginal_relevance_search(
                    cleaned_query,
                    k=settings.search_k,
                    fetch_k=settings.search_fetch_k,
                )
                documents = trim_documents(documents, settings)
                try:
                    documents = ensure_minimum_context(documents, settings)
                except GuardrailViolation:
                    if settings.fallback_if_no_context:
                        output = "No relevant semantic context was retrieved from the vector database."
                        record_tool_call("semantic_search", cleaned_query, output)
                        return output
                    raise

                parts = []
                for document in documents:
                    parts.append(document.page_content)

                output = (
                    "Retrieved context:\n"
                    + "\n\n---\n\n".join(parts)
                    + "\n\nSources:\n"
                    + format_sources(documents)
                )
                record_tool_call("semantic_search", cleaned_query, output)
                return output
            except Exception as exc:
                record_tool_call("semantic_search", cleaned_query, str(exc), status="error")
                raise

        tools.append(semantic_search)

    if settings.enable_sql_tool:

        @tool
        def sql_read_only_query(query: str) -> str:
            """Run a read-only SQL query against PostgreSQL. Use only SELECT queries."""

            safe_query = validate_sql_query(query, settings)
            try:
                rows = run_read_only_query(settings, safe_query)
                output = json.dumps(rows, ensure_ascii=True, indent=2, default=str)
                record_tool_call("sql_read_only_query", safe_query, output)
                return output
            except Exception as exc:
                record_tool_call("sql_read_only_query", safe_query, str(exc), status="error")
                raise

        tools.append(sql_read_only_query)

    if not tools:
        raise GuardrailViolation("No tools are enabled. Enable at least one tool in the .env file.")

    return tools

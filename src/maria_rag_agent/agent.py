from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .runtime import configure_runtime

configure_runtime()

from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware, ToolCallLimitMiddleware
from langchain_openai import ChatOpenAI

from .config import Settings
from .database import describe_schema
from .guardrails import GuardrailViolation, mask_output, validate_question
from .memory import (
    ConversationSession,
    build_memory_messages,
    ensure_conversation,
    maybe_refresh_conversation_summary,
    store_turn,
)
from .prompts import build_system_prompt
from .tools import build_tools


@dataclass
class AgentReply:
    answer: str
    conversation_id: str
    user_id: str
    store_id: str | None = None


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


def ask_agent(
    question: str,
    settings: Settings,
    conversation_id: str | None = None,
    user_id: str = "default-user",
    store_id: str | None = None,
) -> AgentReply:
    cleaned_question = validate_question(question, settings)
    session: ConversationSession = ensure_conversation(
        settings=settings,
        conversation_id=conversation_id,
        user_id=user_id,
        store_id=store_id,
        title=cleaned_question[:80],
    )
    model = build_chat_model(settings)
    agent = build_rag_agent(settings, model=model)
    memory_messages = build_memory_messages(
        settings=settings,
        conversation_id=session.conversation_id,
        user_id=session.user_id,
        store_id=session.store_id,
    )
    result = agent.invoke(
        {
            "messages": memory_messages
            + [
                {
                    "role": "user",
                    "content": cleaned_question,
                }
            ]
        }
    )
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
    )

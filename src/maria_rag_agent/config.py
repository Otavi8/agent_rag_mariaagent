from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    quiet_mode: bool = True

    database_url: str = "postgresql://postgres:password@postgres:5432/maria_agent"
    vector_db_dir: Path = Field(default=Path("./storage/chroma"))
    vector_collection_name: str = "maria_rag_collection"

    source_tables: str = "product_catalog,sales,employees,absenteeism_events"
    index_batch_size: int = 100
    auto_reindex_on_empty_index: bool = True

    chunk_size: int = 900
    chunk_overlap: int = 120

    search_k: int = 4
    search_fetch_k: int = 12
    min_retrieved_documents: int = 1
    max_context_chars: int = 6000
    require_source_attribution: bool = True
    fallback_if_no_context: bool = True

    enable_vector_tool: bool = True
    enable_sql_tool: bool = True
    max_tool_calls: int = 6

    enable_conversation_memory: bool = True
    enable_user_memory: bool = True
    memory_recent_messages: int = 6
    memory_summarize_after_messages: int = 8
    memory_summary_max_chars: int = 1800
    user_memory_top_k: int = 3

    min_question_chars: int = 5
    max_question_chars: int = 500
    blocked_input_patterns: str = ""

    allow_only_select_sql: bool = True
    sql_max_rows: int = 20

    mask_emails: bool = True
    mask_phones: bool = True
    mask_cpfs: bool = True

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    llm_provider: str = "openai"
    llm_model: str = "gpt-4.1-mini"
    llm_temperature: float = 0.0

    openai_api_key: str | None = None

    embedding_provider: str = "huggingface"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    embedding_normalize: bool = True

    ollama_base_url: str = "http://localhost:11434"

    evolution_enabled: bool = True
    evolution_base_url: str = "http://evolution-go:8080"
    evolution_api_key: str | None = None
    evolution_internal_webhook_url: str = "http://app:8000/webhooks/evolution"
    evolution_instance_name: str = "maria-whatsapp"
    evolution_instance_id: str | None = None
    evolution_subscribe_events: str = "MESSAGE,CONNECTION,QRCODE"
    evolution_webhook_secret: str | None = None
    evolution_public_webhook_url: str | None = None
    evolution_default_store_id: str | None = None
    evolution_ignore_group_messages: bool = True
    evolution_ignore_newsletter_messages: bool = True
    evolution_reply_to_media_without_text: bool = False

    traefik_enabled: bool = True
    traefik_domain: str = "example.com"
    traefik_app_host: str = "maria.example.com"
    traefik_evolution_host: str = "evolution.example.com"
    traefik_acme_email: str = "admin@example.com"
    traefik_basic_auth_users: str | None = None

    @field_validator("chunk_size")
    @classmethod
    def validate_chunk_size(cls, value: int) -> int:
        if value < 100:
            raise ValueError("CHUNK_SIZE must be >= 100.")
        return value

    @field_validator("chunk_overlap")
    @classmethod
    def validate_chunk_overlap(cls, value: int, info) -> int:
        chunk_size = info.data.get("chunk_size", 0)
        if value < 0:
            raise ValueError("CHUNK_OVERLAP cannot be negative.")
        if chunk_size and value >= chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE.")
        return value

    @field_validator(
        "memory_recent_messages",
        "memory_summarize_after_messages",
        "memory_summary_max_chars",
        "user_memory_top_k",
        "api_port",
    )
    @classmethod
    def validate_positive_memory_values(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Configured positive integer values must be >= 1.")
        return value

    @property
    def vector_db_dir_abs(self) -> Path:
        return (PROJECT_ROOT / self.vector_db_dir).resolve() if not self.vector_db_dir.is_absolute() else self.vector_db_dir

    @property
    def source_table_list(self) -> list[str]:
        return [item.strip() for item in self.source_tables.split(",") if item.strip()]

    @property
    def blocked_patterns(self) -> list[str]:
        return [item.strip() for item in self.blocked_input_patterns.split("||") if item.strip()]

    @property
    def evolution_subscribe_event_list(self) -> list[str]:
        return [item.strip() for item in self.evolution_subscribe_events.split(",") if item.strip()]

    @property
    def database_name(self) -> str:
        path = urlsplit(self.database_url).path.lstrip("/")
        return path or "postgres"

    def as_public_dict(self) -> dict[str, object]:
        data = self.model_dump()
        if data.get("openai_api_key"):
            data["openai_api_key"] = "***"
        if data.get("evolution_api_key"):
            data["evolution_api_key"] = "***"
        if data.get("evolution_webhook_secret"):
            data["evolution_webhook_secret"] = "***"
        if data.get("database_url"):
            data["database_url"] = "***"
        data["vector_db_dir"] = str(self.vector_db_dir_abs)
        data["source_table_list"] = self.source_table_list
        data["blocked_patterns"] = self.blocked_patterns
        data["evolution_subscribe_event_list"] = self.evolution_subscribe_event_list
        data["database_name"] = self.database_name
        return data


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

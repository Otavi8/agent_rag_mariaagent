from __future__ import annotations

from typing import Any

from langchain_core.documents import Document

from .config import Settings


def build_minio_client(settings: Settings) -> Any:
    if not settings.minio_secret_key:
        raise RuntimeError("MINIO_SECRET_KEY precisa estar configurada para ler regras.")

    try:
        from minio import Minio
    except ImportError as exc:
        raise RuntimeError("Instale a dependencia minio para ler regras do MinIO.") from exc

    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _is_allowed_rule_object(object_name: str, settings: Settings) -> bool:
    lowered_name = object_name.lower()
    return any(lowered_name.endswith(extension) for extension in settings.minio_rules_extension_list)


def _read_object_text(client: Minio, bucket_name: str, object_name: str) -> str:
    response = client.get_object(bucket_name, object_name)
    try:
        return response.read().decode("utf-8", errors="replace")
    finally:
        response.close()
        response.release_conn()


def load_rule_documents(settings: Settings) -> list[Document]:
    if not settings.minio_enabled:
        return []

    client = build_minio_client(settings)
    if not client.bucket_exists(settings.minio_rules_bucket):
        return []

    documents: list[Document] = []
    objects = client.list_objects(
        settings.minio_rules_bucket,
        prefix=settings.minio_rules_prefix,
        recursive=True,
    )

    for item in objects:
        object_name = item.object_name
        if not object_name or object_name.endswith("/"):
            continue
        if not _is_allowed_rule_object(object_name, settings):
            continue
        if item.size and item.size > settings.minio_rules_max_bytes:
            continue

        content = _read_object_text(client, settings.minio_rules_bucket, object_name).strip()
        if not content:
            continue

        documents.append(
            Document(
                page_content=(
                    "Tipo de documento: regra operacional\n"
                    f"Arquivo da regra: {object_name}\n"
                    "Origem: MinIO\n\n"
                    f"{content}"
                ),
                metadata={
                    "table": "operational_rules",
                    "record_id": object_name,
                    "source": "minio_rules",
                    "title": object_name.rsplit("/", maxsplit=1)[-1],
                    "bucket": settings.minio_rules_bucket,
                    "object_name": object_name,
                },
            )
        )

    return documents


def load_rule_documents_safely(settings: Settings) -> list[Document]:
    try:
        return load_rule_documents(settings)
    except Exception:
        return []


def ensure_rules_bucket(settings: Settings) -> bool:
    client = build_minio_client(settings)
    if client.bucket_exists(settings.minio_rules_bucket):
        return False
    client.make_bucket(settings.minio_rules_bucket)
    return True


def list_rule_objects(settings: Settings) -> list[dict[str, object]]:
    if not settings.minio_enabled:
        return []

    client = build_minio_client(settings)
    if not client.bucket_exists(settings.minio_rules_bucket):
        return []

    objects = client.list_objects(
        settings.minio_rules_bucket,
        prefix=settings.minio_rules_prefix,
        recursive=True,
    )
    return [
        {
            "bucket": settings.minio_rules_bucket,
            "object_name": item.object_name,
            "size": item.size,
            "last_modified": item.last_modified,
            "indexed_extension": bool(
                item.object_name and _is_allowed_rule_object(item.object_name, settings)
            ),
        }
        for item in objects
        if item.object_name and not item.object_name.endswith("/")
    ]

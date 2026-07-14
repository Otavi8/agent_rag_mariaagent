from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from .runtime import configure_runtime

configure_runtime()

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from .config import Settings
from .database import fetch_rows_for_indexing, init_database
from .documents import build_documents
from .rules import load_rule_documents_safely


def build_embeddings(settings: Settings):
    provider = settings.embedding_provider.lower()

    if provider == "huggingface":
        return HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": settings.embedding_device},
            encode_kwargs={"normalize_embeddings": settings.embedding_normalize},
        )

    if provider == "openai":
        return OpenAIEmbeddings(model=settings.embedding_model)

    if provider == "ollama":
        try:
            from langchain_ollama import OllamaEmbeddings
        except ImportError as exc:
            raise RuntimeError(
                "To use EMBEDDING_PROVIDER=ollama, install the optional dependency: pip install -e .[ollama]"
            ) from exc

        return OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url,
        )

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {settings.embedding_provider}")


def build_text_splitter(settings: Settings) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def build_qdrant_client(settings: Settings) -> QdrantClient:
    kwargs = {"url": settings.qdrant_url}
    if settings.qdrant_api_key:
        kwargs["api_key"] = settings.qdrant_api_key
    return QdrantClient(**kwargs)


def build_vector_store(settings: Settings) -> QdrantVectorStore:
    embeddings = build_embeddings(settings)
    return QdrantVectorStore.from_existing_collection(
        embedding=embeddings,
        collection_name=settings.vector_collection_name,
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        prefer_grpc=settings.qdrant_prefer_grpc,
    )


def reset_vector_store(settings: Settings) -> None:
    client = build_qdrant_client(settings)
    if client.collection_exists(settings.vector_collection_name):
        client.delete_collection(settings.vector_collection_name)


def vector_store_is_ready(settings: Settings) -> bool:
    try:
        client = build_qdrant_client(settings)
        if not client.collection_exists(settings.vector_collection_name):
            return False
        result = client.count(collection_name=settings.vector_collection_name, exact=False)
        return result.count > 0
    except Exception:
        return False


def ensure_vector_store_ready(settings: Settings) -> None:
    if settings.auto_reindex_on_empty_index and not vector_store_is_ready(settings):
        reindex_vector_store(settings)


def reindex_vector_store(settings: Settings) -> dict[str, int]:
    init_database(settings)
    rows_by_table = fetch_rows_for_indexing(settings)
    database_documents = build_documents(rows_by_table)
    rule_documents = load_rule_documents_safely(settings)
    base_documents = [*database_documents, *rule_documents]
    chunks = build_text_splitter(settings).split_documents(base_documents)

    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = index

    ids = []
    for chunk in chunks:
        readable_id = (
            f"{chunk.metadata.get('table')}:{chunk.metadata.get('record_id')}:{chunk.metadata.get('chunk_index')}"
        )
        chunk.metadata["readable_id"] = readable_id
        ids.append(str(uuid5(NAMESPACE_URL, readable_id)))

    reset_vector_store(settings)
    embeddings = build_embeddings(settings)
    vector_size = len(embeddings.embed_query("qdrant vector size probe"))
    client = build_qdrant_client(settings)
    client.create_collection(
        collection_name=settings.vector_collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=settings.vector_collection_name,
        embedding=embeddings,
    )

    for start in range(0, len(chunks), settings.index_batch_size):
        end = start + settings.index_batch_size
        vector_store.add_documents(chunks[start:end], ids=ids[start:end])

    return {
        "base_documents": len(base_documents),
        "database_documents": len(database_documents),
        "rule_documents": len(rule_documents),
        "chunks": len(chunks),
        "tables": len(rows_by_table),
    }

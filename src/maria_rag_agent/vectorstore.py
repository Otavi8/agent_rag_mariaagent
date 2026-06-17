from __future__ import annotations

import shutil

from .runtime import configure_runtime

configure_runtime()

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import PROJECT_ROOT, Settings
from .database import fetch_rows_for_indexing, init_database
from .documents import build_documents


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


def build_vector_store(settings: Settings) -> Chroma:
    embeddings = build_embeddings(settings)
    settings.vector_db_dir_abs.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=settings.vector_collection_name,
        persist_directory=str(settings.vector_db_dir_abs),
        embedding_function=embeddings,
    )


def reset_vector_store(settings: Settings) -> None:
    target = settings.vector_db_dir_abs
    project_root = PROJECT_ROOT.resolve()

    if not target.exists():
        return

    if project_root not in target.resolve().parents and target.resolve() != project_root:
        raise RuntimeError("Refusing to delete a vector store outside the project root.")

    shutil.rmtree(target)


def vector_store_is_ready(settings: Settings) -> bool:
    target = settings.vector_db_dir_abs
    return target.exists() and any(target.iterdir())


def ensure_vector_store_ready(settings: Settings) -> None:
    if settings.auto_reindex_on_empty_index and not vector_store_is_ready(settings):
        reindex_vector_store(settings)


def reindex_vector_store(settings: Settings) -> dict[str, int]:
    init_database(settings)
    rows_by_table = fetch_rows_for_indexing(settings)
    base_documents = build_documents(rows_by_table)
    chunks = build_text_splitter(settings).split_documents(base_documents)

    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = index

    ids = [
        f"{chunk.metadata.get('table')}:{chunk.metadata.get('record_id')}:{chunk.metadata.get('chunk_index')}"
        for chunk in chunks
    ]

    reset_vector_store(settings)
    vector_store = build_vector_store(settings)

    for start in range(0, len(chunks), settings.index_batch_size):
        end = start + settings.index_batch_size
        vector_store.add_documents(chunks[start:end], ids=ids[start:end])

    return {
        "base_documents": len(base_documents),
        "chunks": len(chunks),
        "tables": len(rows_by_table),
    }

import hashlib
import os

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import (
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL,
)


def split_documents(documents: list[Document]) -> list[Document]:
    """Split pages into smaller chunks while preserving source metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        add_start_index=True,
    )

    return splitter.split_documents(documents)


def get_vector_store() -> Chroma:
    """Open the persistent Chroma collection."""
    if not os.getenv("OPENAI_API_KEY", "").strip():
        raise ValueError(
            "OPENAI_API_KEY is missing. Add your key to the project's .env file."
        )

    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
    )

    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )


def make_chunk_id(chunk: Document) -> str:
    """Create a reproducible ID from the chunk's source and content."""
    value = (
        f"{chunk.metadata['source']}\n"
        f"{chunk.metadata['page']}\n"
        f"{chunk.metadata['start_index']}\n"
        f"{chunk.page_content}"
    )

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_index(
    chunks: list[Document],
    rebuild: bool = False,
) -> int:
    """Embed chunks in batches and save them in the local index."""
    if not chunks:
        raise ValueError("No chunks were provided for indexing.")

    vector_store = get_vector_store()

    # Fetch one ID to check whether the collection already contains data.
    existing = vector_store.get(limit=1)

    if existing["ids"] and not rebuild:
        raise ValueError(
            "The index already contains data.\n"
            "To replace the generated index, run: python ingest.py --rebuild\n"
            "Rebuilding makes embedding requests again."
        )

    if rebuild:
        # Only resets this generated collection, not the original PDFs.
        vector_store.reset_collection()

    total_chunks = len(chunks)

    for start in range(0, total_chunks, EMBEDDING_BATCH_SIZE):
        batch = chunks[start : start + EMBEDDING_BATCH_SIZE]
        ids = [make_chunk_id(chunk) for chunk in batch]

        vector_store.add_documents(
            documents=batch,
            ids=ids,
        )

        completed = min(start + len(batch), total_chunks)
        print(f"Indexed {completed}/{total_chunks} chunks", flush=True)

    return total_chunks
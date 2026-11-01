import os

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

# Import config first so the project's .env is loaded.
from src.config import EMBEDDING_MODEL


def get_namespace() -> str:
    namespace = os.getenv(
        "PINECONE_NAMESPACE",
        "ironstore-v1",
    ).strip()

    if not namespace:
        raise ValueError("PINECONE_NAMESPACE must not be empty.")

    return namespace


def get_pinecone_index():
    api_key = os.getenv("PINECONE_API_KEY", "").strip()
    index_name = os.getenv("PINECONE_INDEX_NAME", "").strip()

    if not api_key:
        raise ValueError("PINECONE_API_KEY is missing from .env.")

    if not index_name:
        raise ValueError("PINECONE_INDEX_NAME is missing from .env.")

    client = Pinecone(api_key=api_key)
    description = client.describe_index(index_name)

    if description.dimension != 1536:
        raise ValueError(
            "This migration requires a Pinecone index "
            "with 1536 dimensions."
        )

    if description.metric != "cosine":
        raise ValueError(
            "Use a Pinecone index with the cosine metric."
        )

    if not description.status["ready"]:
        raise ValueError(
            "The Pinecone index is not ready yet. Try again shortly."
        )

    return client.Index(host=description.host)


def get_vector_store() -> PineconeVectorStore:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        raise ValueError("OPENAI_API_KEY is missing.")

    return PineconeVectorStore(
        index=get_pinecone_index(),
        embedding=OpenAIEmbeddings(model=EMBEDDING_MODEL),
        namespace=get_namespace(),
        text_key="text",
    )


def has_documents() -> bool:
    stats = get_pinecone_index().describe_index_stats()
    namespace_stats = stats.namespaces.get(get_namespace())

    return (
        namespace_stats is not None
        and namespace_stats.vector_count > 0
    )
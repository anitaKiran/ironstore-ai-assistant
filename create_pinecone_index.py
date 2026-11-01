import os
from pathlib import Path

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent / ".env")

    api_key = os.getenv("PINECONE_API_KEY", "").strip()
    index_name = os.getenv(
        "PINECONE_INDEX_NAME",
        "ironstore-documents",
    ).strip()

    if not api_key:
        raise SystemExit("Add PINECONE_API_KEY to your .env file.")

    client = Pinecone(api_key=api_key)

    if index_name in client.list_indexes().names():
        print(f"Index '{index_name}' already exists.")
        print("No changes were made.")
        return

    client.create_index(
        name=index_name,
        vector_type="dense",
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1",
        ),
    )

    print(f"Created index: {index_name}")
    print("Dimensions: 1536")
    print("Metric: cosine")
    print("Refresh the Pinecone dashboard and wait for Ready status.")


if __name__ == "__main__":
    main()
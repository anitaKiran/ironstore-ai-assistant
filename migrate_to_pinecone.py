import time

import chromadb

from src.cloud_index import get_namespace, get_pinecone_index
from src.config import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL


def main() -> None:
    if EMBEDDING_MODEL != "text-embedding-3-small":
        raise SystemExit(
            "This migration expects the existing index to use "
            "text-embedding-3-small with 1536 dimensions."
        )

    if not CHROMA_DIR.is_dir():
        raise SystemExit(
            f"Local Chroma folder not found: {CHROMA_DIR}"
        )

    local_client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
    )

    collection = local_client.get_collection(
        name=COLLECTION_NAME,
    )

    total = collection.count()

    if total == 0:
        raise SystemExit("The local Chroma collection is empty.")

    index = get_pinecone_index()
    namespace = get_namespace()

    print(f"Local chunks: {total}")
    print(f"Destination namespace: {namespace}")
    print("Copying existing embeddings; no OpenAI calls are made.\n")

    batch_size = 50

    for offset in range(0, total, batch_size):
        batch = collection.get(
            limit=batch_size,
            offset=offset,
            include=["embeddings", "documents", "metadatas"],
        )

        vectors = []

        for position, record_id in enumerate(batch["ids"]):
            embedding = batch["embeddings"][position]
            text = batch["documents"][position]
            metadata = dict(batch["metadatas"][position] or {})

            if len(embedding) != 1536:
                raise ValueError(
                    f"Unexpected embedding dimension for {record_id}."
                )

            if not text:
                raise ValueError(
                    f"Missing text for chunk {record_id}."
                )

            # LangChain reads this field as the document's page_content.
            metadata["text"] = text

            vectors.append(
                {
                    "id": record_id,
                    "values": embedding.tolist(),
                    "metadata": metadata,
                }
            )

        index.upsert(
            vectors=vectors,
            namespace=namespace,
        )

        completed = min(offset + len(vectors), total)
        print(f"Uploaded {completed}/{total}", flush=True)

    print("\nUpload requests completed.")
    print("Checking Pinecone's reported record count...")

    # Pinecone may take a little time to reflect newly written records.
    for _ in range(30):
        stats = index.describe_index_stats()
        namespace_stats = stats.namespaces.get(namespace)

        remote_count = (
            namespace_stats.vector_count
            if namespace_stats is not None
            else 0
        )

        if remote_count == total:
            print(f"\nVerified: {remote_count} records in Pinecone.")
            print("Migration completed.")
            return

        time.sleep(2)

    print(
        f"\nPinecone currently reports {remote_count} records; "
        f"expected {total}."
    )
    print(
        "Allow time for the index to update and check the namespace "
        "in the Pinecone console before continuing."
    )


if __name__ == "__main__":
    main()
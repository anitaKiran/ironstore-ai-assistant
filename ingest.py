import argparse

from src.config import CHROMA_DIR
from src.document_loader import load_documents
from src.indexing import build_index, get_vector_store, split_documents


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the IronStore document search index."
    )

    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Replace the existing index and generate embeddings again.",
    )

    args = parser.parse_args()

    print("IronStore — Build Document Index")

    # Check before spending time reading all PDFs again.
    vector_store = get_vector_store()

    if vector_store.get(limit=1)["ids"] and not args.rebuild:
        raise SystemExit(
            "\nAn index already exists. No embedding requests were made.\n"
            "To replace it, run: python ingest.py --rebuild"
        )

    print("\n1. Loading PDFs...", flush=True)
    documents, report = load_documents()

    print(f"PDF files found: {report['pdf_files_found']}")
    print(f"PDF files loaded: {report['pdf_files_loaded']}")
    print(f"Pages with text: {report['loaded_pages']}")
    print(f"Pages without text: {report['pages_without_text']}")

    if report["errors"]:
        for error in report["errors"]:
            print(f"- {error['source']}: {error['error']}")

        raise SystemExit(
            "\nResolve document-loading errors before building the index."
        )

    if not documents:
        raise SystemExit("No document text was extracted.")

    print("\n2. Splitting pages into chunks...", flush=True)
    chunks = split_documents(documents)

    print(f"Chunks created: {len(chunks)}")
    print("\nSample chunk metadata:")
    print(chunks[0].metadata)

    print("\n3. Creating embeddings and saving the index...", flush=True)

    try:
        indexed_count = build_index(
            chunks,
            rebuild=args.rebuild,
        )
    except Exception:
        print(
            "\nIndexing did not finish. The index may be incomplete.\n"
            "After resolving the error, run: python ingest.py --rebuild"
        )
        raise

    print(f"\nSuccessfully indexed {indexed_count} chunks.")
    print(f"Index location: {CHROMA_DIR}")

    print("\n4. Testing retrieval...", flush=True)

    question = "How do employees request annual leave?"
    results = vector_store.similarity_search(question, k=3)

    print(f"\nQuestion: {question}")

    for number, document in enumerate(results, start=1):
        print(f"\nResult {number}")
        print(f"Source: {document.metadata['source']}")
        print(f"PDF page: {document.metadata['page']}")
        print(f"Text:\n{document.page_content[:700]}")

    print("\nIndexing and retrieval check completed.")


if __name__ == "__main__":
    main()
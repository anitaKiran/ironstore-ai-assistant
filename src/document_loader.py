import re
from pathlib import Path

from langchain_core.documents import Document
from pypdf import PdfReader

from src.config import DOCUMENTS_DIR


def find_pdf_files(directory: Path = DOCUMENTS_DIR) -> list[Path]:
    """Find PDFs recursively, ignoring operating-system metadata files."""
    if not directory.is_dir():
        raise FileNotFoundError(
            f"Documents folder not found: {directory}\n"
            "Place the extracted documents folder in your project root."
        )

    pdf_files = sorted(
        path
        for path in directory.rglob("*")
        if path.is_file()
        and path.suffix.lower() == ".pdf"
        and not any(part.startswith(".") for part in path.relative_to(directory).parts)
        and "__MACOSX" not in path.parts
    )

    if not pdf_files:
        raise ValueError(f"No PDF files found inside: {directory}")

    return pdf_files


def clean_text(text: str) -> str:
    """Remove extraction artifacts while preserving line breaks."""
    text = text.replace("\x00", "")
    text = text.replace("\x7f", "-")

    # Collapse repeated spaces and tabs, but keep paragraph structure.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def get_department(relative_path: Path) -> str:
    """Identify the department from the document's folder."""
    if relative_path.parts[0] == "product_catalog":
        return "product_catalog"

    if (
        relative_path.parts[0] == "internal_docs_by_area"
        and len(relative_path.parts) >= 3
    ):
        return relative_path.parts[1]

    return "unknown"


def load_documents(
    directory: Path = DOCUMENTS_DIR,
) -> tuple[list[Document], dict]:
    """Load one LangChain Document per PDF page containing extractable text."""
    directory = directory.resolve()
    pdf_files = find_pdf_files(directory)

    documents: list[Document] = []

    report = {
        "pdf_files_found": len(pdf_files),
        "pdf_files_loaded": 0,
        "total_pages": 0,
        "pages_without_text": 0,
        "loaded_pages": 0,
        "errors": [],
    }

    for pdf_path in pdf_files:
        relative_path = pdf_path.relative_to(directory)

        try:
            # Collect a whole file before adding it to the result.
            # If extraction fails, we do not silently retain a partial file.
            file_documents: list[Document] = []
            pages_without_text = 0

            with pdf_path.open("rb") as pdf_file:
                reader = PdfReader(pdf_file)
                page_count = len(reader.pages)

                for page_number, page in enumerate(reader.pages, start=1):
                    text = clean_text(page.extract_text() or "")

                    if not text:
                        pages_without_text += 1
                        continue

                    file_documents.append(
                        Document(
                            page_content=text,
                            metadata={
                                "source": relative_path.as_posix(),
                                "filename": pdf_path.name,
                                "department": get_department(relative_path),
                                "page": page_number,
                            },
                        )
                    )

            documents.extend(file_documents)
            report["pdf_files_loaded"] += 1
            report["total_pages"] += page_count
            report["pages_without_text"] += pages_without_text

        except Exception as exc:
            report["errors"].append(
                {
                    "source": relative_path.as_posix(),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    report["loaded_pages"] = len(documents)

    return documents, report
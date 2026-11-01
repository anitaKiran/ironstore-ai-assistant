import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.assistant import KnowledgeAssistant
from src.config import BASE_DIR, DOCUMENTS_DIR


logger = logging.getLogger(__name__)

FRONTEND_DIR = BASE_DIR / "frontend"


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    chat_history: list[HistoryMessage] = Field(
        default_factory=list,
        max_length=6,
    )


class SourceResponse(BaseModel):
    label: str
    source: str
    filename: str
    page: int
    department: str
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
    search_question: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.assistant = KnowledgeAssistant()
    yield


app = FastAPI(
    title="IronStore Enterprise AI Assistant",
    description="Ask questions using internal company documents.",
    version="0.2.0",
    lifespan=lifespan,
)

app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static",
)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/documents/{file_path:path}", include_in_schema=False)
def open_document(file_path: str):
    root = DOCUMENTS_DIR.resolve()
    target = (root / file_path).resolve()

    # Restrict access to PDF files inside the documents folder.
    if (
        not target.is_relative_to(root)
        or target.suffix.lower() != ".pdf"
        or not target.is_file()
    ):
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return FileResponse(
        target,
        media_type="application/pdf",
    )


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request):
    if not payload.question.strip():
        raise HTTPException(
            status_code=422,
            detail="Please enter a question.",
        )

    history = [
        message.model_dump()
        for message in payload.chat_history
    ]

    try:
        return request.app.state.assistant.ask_question(
            question=payload.question,
            chat_history=history,
        )
    except Exception:
        logger.exception("Chat request failed")

        raise HTTPException(
            status_code=503,
            detail=(
                "The assistant could not complete the request. "
                "Please try again."
            ),
        ) from None
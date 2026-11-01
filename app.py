from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from src.assistant import KnowledgeAssistant


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
    # Load the assistant once when the server starts.
    app.state.assistant = KnowledgeAssistant()
    yield


app = FastAPI(
    title="IronStore Enterprise AI Assistant",
    description="Ask questions using internal company documents.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "ok"}


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
        # Keep provider errors and internal details out of API responses.
        raise HTTPException(
            status_code=503,
            detail="The assistant could not complete the request. Please try again.",
        )
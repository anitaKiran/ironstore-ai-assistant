import os
import re

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from src.indexing import get_vector_store
from src.prompts import ANSWER_SYSTEM_PROMPT, REWRITE_SYSTEM_PROMPT


class KnowledgeAssistant:
    """Reusable assistant for a terminal interface or future API."""

    def __init__(self) -> None:
        model_name = os.getenv("OPENAI_CHAT_MODEL", "").strip()

        if not model_name:
            raise ValueError(
                "Add OPENAI_CHAT_MODEL to your .env file "
                "using a chat model available through your API account."
            )

        self.vector_store = get_vector_store()

        if not self.vector_store.get(limit=1)["ids"]:
            raise ValueError(
                "The document index is empty. Run python ingest.py first."
            )

        model = ChatOpenAI(
            model=model_name,
            timeout=60,
            max_retries=2,
        )

        rewrite_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", REWRITE_SYSTEM_PROMPT),
                MessagesPlaceholder("history"),
                ("human", "{question}"),
            ]
        )

        answer_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", ANSWER_SYSTEM_PROMPT),
                MessagesPlaceholder("history"),
                (
                    "human",
                    "Document passages:\n\n{context}\n\n"
                    "Employee question: {question}",
                ),
            ]
        )

        self.rewrite_chain = rewrite_prompt | model | StrOutputParser()
        self.answer_chain = answer_prompt | model | StrOutputParser()

    @staticmethod
    def prepare_history(chat_history: list[dict]) -> list:
        """Use only the last three user/assistant exchanges."""
        messages = []

        for item in chat_history[-6:]:
            role = item["role"]
            content = item["content"]

            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            else:
                raise ValueError(f"Unsupported history role: {role}")

        return messages

    def ask_question(
        self,
        question: str,
        chat_history: list[dict] | None = None,
    ) -> dict:
        """Return a grounded answer and source metadata."""
        question = question.strip()

        if not question:
            raise ValueError("Please enter a question.")

        history = self.prepare_history(chat_history or [])

        if history:
            search_question = self.rewrite_chain.invoke(
                {
                    "history": history,
                    "question": question,
                }
            ).strip()

            if not search_question:
                search_question = question
        else:
            search_question = question

        retrieved_documents = self.vector_store.similarity_search(
            search_question,
            k=6,
        )

        if not retrieved_documents:
            return {
                "answer": (
                    "I could not find supporting information "
                    "in the available company documents."
                ),
                "sources": [],
                "search_question": search_question,
            }

        context_parts = []
        available_sources = {}

        for number, document in enumerate(retrieved_documents, start=1):
            label = f"S{number}"

            source = {
                "label": label,
                "source": document.metadata["source"],
                "filename": document.metadata["filename"],
                "page": document.metadata["page"],
                "department": document.metadata["department"],
                "excerpt": document.page_content,
            }

            available_sources[label] = source

            context_parts.append(
                f"[{label}]\n"
                f"File: {source['source']}\n"
                f"PDF page: {source['page']}\n"
                f"Passage:\n{document.page_content}"
            )

        answer = self.answer_chain.invoke(
            {
                "history": history,
                "question": question,
                "context": "\n\n---\n\n".join(context_parts),
            }
        )

                # Recognise individual citations [S1] and grouped citations [S1, S2].
        citation_groups = re.findall(
            r"\[(S\d+(?:\s*,\s*S\d+)*)\]",
            answer,
        )

        cited_labels = {
            label
            for group in citation_groups
            for label in re.findall(r"S\d+", group)
        }

        # Check that every source label refers to retrieved evidence.
        unknown_labels = cited_labels - available_sources.keys()

        if unknown_labels:
            return {
                "answer": (
                    "I could not produce an answer with valid source "
                    "references. Please rephrase your question."
                ),
                "sources": [],
                "search_question": search_question,
            }

        sources = [
            source
            for label, source in available_sources.items()
            if label in cited_labels
        ]

        return {
            "answer": answer,
            "sources": sources,
            "search_question": search_question,
        }
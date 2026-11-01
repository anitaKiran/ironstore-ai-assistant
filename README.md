# IronStore Enterprise AI Assistant

A conversational assistant that helps employees find information in
IronStore’s internal company documents.

Built as an individual mini-project using LangChain and
Retrieval-Augmented Generation (RAG).

## Features

- Answer questions about internal policies, procedures, and products.
- Explain procedures and turn documented instructions into checklists.
- Support follow-up questions using recent conversation history.
- Include source references with document names and PDF page numbers.
- Display supporting passages in expandable source cards.
- Open the original source PDFs from the chat interface.
- Acknowledge when the retrieved documents do not provide enough information.
- Provide both a browser interface and a terminal chat.
- Expose the assistant through a FastAPI API.

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python |
| RAG framework | LangChain |
| Answer generation | OpenAI `gpt-4.1-mini` |
| Embeddings | OpenAI `text-embedding-3-small` |
| Hosted vector database | Pinecone |
| Initial local vector database | Chroma |
| PDF extraction | pypdf |
| Backend | FastAPI and Pydantic |
| Frontend | HTML, CSS, JavaScript |
| Deployment target | Vercel |

## How It Works

### Document preparation

1. Extract text from the PDF documents.
2. Preserve the source path, department, and PDF page number.
3. Split extracted pages into overlapping text chunks.
4. Generate embeddings and store them in a local Chroma index.
5. Migrate the existing vectors, text, and metadata to Pinecone.

The migration reuses existing embeddings without generating them again.

### Answering questions

1. Receive the employee’s question and recent conversation history.
2. Rewrite follow-up questions into standalone search questions when needed.
3. Search Pinecone for relevant document chunks.
4. Send the retrieved passages to the chat model.
5. Return an answer with source references.
6. Display the answer and supporting passages in the browser.

The running web app searches Pinecone and does not require the local
Chroma folder.

## Dataset

The supplied synthetic company dataset contains 83 PDFs:

- 20 internal documents across HR, IT, Finance, Sales, Customer Support,
  Legal, and Deliveries.
- 63 product catalogs, including an older catalog reviewed in December 2021.

The PDFs contain 2,308 pages. The initial extraction produced 2,256 pages
with text and 52 pages without extracted text.

The current index contains 2,836 text chunks.

The source documents remain in their original folder structure:

```text
documents/
├── internal_docs_by_area/
│   ├── Customer_support/
│   ├── Deliveries/
│   ├── Finance/
│   ├── HR_policies/
│   ├── IT/
│   ├── Legal_Terms/
│   └── Sales/
└── product_catalog/
```

## Project Structure

```text
ironstore-ai-assistant/
├── documents/
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── document_loader.py
│   ├── indexing.py
│   ├── cloud_index.py
│   ├── assistant.py
│   └── prompts.py
├── app.py
├── chat.py
├── ingest.py
├── create_pinecone_index.py
├── migrate_to_pinecone.py
├── requirements.txt
├── requirements-local.txt
├── .env.example
├── .gitignore
├── .python-version
├── vercel.json
└── README.md
```

`chroma_db/` is generated locally and excluded from Git.

## Run Locally

### 1. Create and activate a virtual environment

From the repository root on Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

For the web app using an already populated Pinecone index:

```powershell
python -m pip install -r requirements.txt
```

For local document indexing and migration tools:

```powershell
python -m pip install -r requirements-local.txt
```

### 3. Configure environment variables

Copy the template:

```powershell
Copy-Item .env.example .env
```

Add your own credentials:

```dotenv
OPENAI_API_KEY=your_openai_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4.1-mini

PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=ironstore-documents
PINECONE_NAMESPACE=ironstore-v1
```

Never commit `.env` or API keys.

### 4. Prepare the index if needed

An API key alone does not contain the document index.

If your configured Pinecone namespace already contains the migrated
documents, skip this step.

For a fresh setup with the supplied PDFs:

```powershell
python create_pinecone_index.py
```

Wait for the Pinecone index to become ready, then run:

```powershell
python ingest.py
python migrate_to_pinecone.py
```

The initial ingestion uses OpenAI embedding credits. Migration copies
the saved embeddings into Pinecone.

If a local Chroma index already exists, skip ingestion and run only the
migration.

The Pinecone index uses dense vectors, 1,536 dimensions, and cosine
similarity.

### 5. Start the web app

```powershell
python -m uvicorn app:app --reload
```

Open:

- Web app: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs
- Health endpoint: http://127.0.0.1:8000/health

### Optional: Terminal Chat

```powershell
python chat.py
```

Commands:

- `/clear` resets the conversation.
- `/exit` closes the terminal assistant.

## API

### POST /chat

Example request:

```json
{
  "question": "How do employees request annual leave?",
  "chat_history": []
}
```

The response includes:

- `answer`: generated answer with citation labels.
- `sources`: cited passages and document metadata.
- `search_question`: the question used for retrieval.

The client supplies conversation history with each request. The server
does not permanently store conversations.

## Example Questions

- How do employees request annual leave?
- Who approves it?
- What should I do if my company laptop is stolen?
- Turn the expense reimbursement procedure into a checklist.
- What information is available in the electronics catalog?

## Manual Evaluation

The application was manually checked for:

- Document-based answers and source references.
- Follow-up question handling.
- Missing-information responses.
- Procedure explanations.
- API responses through Swagger.
- Browser chat and expandable source passages.

Citation labels are validated against retrieved sources. This checks
reference validity, not whether every generated claim is correct.

## Limitations

- Retrieval can miss relevant passages.
- Answers may contain errors and should be checked against cited sources.
- Conflict and outdated-information handling relies on retrieved evidence
  and model instructions; it is not a comprehensive policy-version system.
- Catalog prices and availability are document snapshots, not live data.
- Pages without extractable text are skipped; OCR is not implemented.
- Search is semantic; dedicated SKU or exact-keyword search is not implemented.
- Browser conversation history resets when the page is refreshed.
- Authentication, department-based access control, and rate limiting are
  not implemented. This is a demonstration using synthetic documents.

## Deployment

Deployment to Vercel is the next step.

The deployed app will use Pinecone for document retrieval and OpenAI
for question embeddings and answer generation. API credentials must
be configured as server-side environment variables in Vercel.

The deployment URL will be added after verification.

## Future Improvements

- Authentication and department-based document permissions.
- Hybrid semantic and keyword search.
- Better policy-date and version handling.
- Automated retrieval and answer evaluation.
- Persistent conversations.
- Document updates and incremental indexing.
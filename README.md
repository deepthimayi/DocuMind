# RAG Chatbot — Ask Your Documents

A production-quality **Retrieval-Augmented Generation** web app that lets you upload PDF or text files and ask questions about them. Answers are grounded in your documents with real source citations.

![RAG Chatbot Screenshot](docs/screenshot-placeholder.png)
> _Screenshot placeholder — replace with your own after running locally_

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (React)                         │
│  ┌──────────────┐   ┌────────────────────────────────────────┐  │
│  │  FileUpload  │   │           ChatWindow                   │  │
│  │  component   │   │  MessageBubble × N  + SourcesPanel     │  │
│  └──────┬───────┘   └──────────────┬─────────────────────────┘  │
└─────────┼──────────────────────────┼─────────────────────────────┘
          │ POST /upload             │ POST /chat  (SSE stream)
          ▼                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Python)                     │
│                                                                 │
│  ┌─────────────┐    ┌───────────────┐    ┌──────────────────┐   │
│  │  ingest.py  │    │ retriever.py  │    │    chat.py       │   │
│  │             │    │               │    │                  │   │
│  │ • PDF parse │    │ • Embed query │    │ • Build prompt   │   │
│  │ • Chunking  │    │ • ChromaDB    │    │ • Call Claude    │   │
│  │ • Embed     │    │   ANN search  │    │   (streaming)    │   │
│  │ • Store     │    │ • Top-3 hits  │    │                  │   │
│  └──────┬──────┘    └──────┬────────┘    └──────┬───────────┘   │
└─────────┼─────────────────┼──────────────────────┼──────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────┐   ┌──────────────┐    ┌───────────────────┐
│   ChromaDB      │   │  MiniLM-L6   │    │  Anthropic API    │
│  (local disk)   │   │  Embeddings  │    │  claude-sonnet-4  │
│  per-doc        │   │  (local,     │    │                   │
│  collections    │   │  no API key) │    │                   │
└─────────────────┘   └──────────────┘    └───────────────────┘
```

### Data flow

1. **Upload** — PDF/TXT is parsed with PyMuPDF → split into 500-char chunks with 50-char overlap
2. **Index** — each chunk is embedded with `all-MiniLM-L6-v2` (runs locally) → stored in ChromaDB
3. **Query** — user's question is embedded → cosine-similarity search → top-3 chunks retrieved
4. **Generate** — chunks + question sent to Claude as context → streamed answer returned via SSE
5. **Cite** — source metadata (filename, chunk index, relevance %) shown in collapsible panel

---

## Features

- Upload PDF or plain-text files (max 20 MB)
- Streaming responses via Server-Sent Events
- Collapsible source citations with relevance scores
- Conversation history (last 3 turns sent as context)
- Dark-mode UI with polished Tailwind design
- Error handling at every layer (file type, size, API errors)
- Per-document ChromaDB collections — re-upload replaces cleanly
- Docker Compose for one-command deployment

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | Python 3.11 + FastAPI |
| AI | Claude (claude-sonnet-4-20250514) via Anthropic SDK |
| Embeddings | `all-MiniLM-L6-v2` via sentence-transformers (local) |
| Vector DB | ChromaDB (persistent, local disk) |
| PDF parsing | PyMuPDF (fitz) |

---

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- An **Anthropic API key** — get one at [console.anthropic.com](https://console.anthropic.com/)

### 1 — Clone & set environment variables

```bash
git clone https://github.com/yourname/rag-chatbot.git
cd rag-chatbot

cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 2 — Start the backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

On first startup, `sentence-transformers` will download the MiniLM model (~90 MB). This is cached for subsequent runs.

### 3 — Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### 4 — Use it

1. Drag & drop a PDF or `.txt` file onto the upload area
2. Wait for "Document ready" — the file is chunked and indexed
3. Type a question in the chat box and press Enter
4. Read the streaming answer; click "N sources retrieved" to see citations

---

## Docker Compose (one-command deploy)

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

docker compose up --build
```

- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend API: [http://localhost:8000](http://localhost:8000)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/upload` | Upload a PDF or TXT file |
| `GET` | `/documents` | List uploaded documents |
| `POST` | `/chat` | Ask a question (SSE stream) |
| `DELETE` | `/documents/{doc_id}` | Delete a document |

### POST /chat — request body

```json
{
  "doc_id": "uuid-from-upload",
  "question": "What is the main argument of this paper?",
  "history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

### POST /chat — SSE event types

| Event | Data |
|---|---|
| `sources` | JSON array of `{filename, chunk_index, relevance_score}` |
| `data` | Token string (newlines escaped as `\n`) |
| `done` | `[DONE]` |
| `error` | Error message string |

---

## Configuration

All tunables live in the source files — no hidden config files:

| Variable | Location | Default | Description |
|---|---|---|---|
| `CHUNK_SIZE` | `backend/ingest.py` | `500` | Characters per chunk |
| `CHUNK_OVERLAP` | `backend/ingest.py` | `50` | Overlap between chunks |
| `TOP_K` | `backend/retriever.py` | `3` | Chunks sent to Claude |
| `MAX_TOKENS` | `backend/chat.py` | `1024` | Max response length |
| `CLAUDE_MODEL` | `backend/chat.py` | `claude-sonnet-4-20250514` | Claude model ID |
| `MAX_FILE_SIZE_MB` | `backend/main.py` | `20` | Upload size limit |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |

---

## Project Structure

```
rag-chatbot/
├── backend/
│   ├── main.py          # FastAPI app, routes, CORS
│   ├── ingest.py        # PDF parsing, chunking, embedding, ChromaDB storage
│   ├── retriever.py     # Semantic search against ChromaDB
│   ├── chat.py          # Claude API streaming call
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx               # Root layout, sidebar, state
│   │   └── components/
│   │       ├── ChatWindow.jsx    # Message list, SSE client, input bar
│   │       ├── FileUpload.jsx    # Drag-and-drop upload, status states
│   │       └── MessageBubble.jsx # Message rendering, sources panel
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## License

MIT

import os
import uuid
import logging
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env", override=True)

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ingest import ingest_document, load_document
from retriever import retrieve_chunks
from chat import stream_answer, generate_questions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {"application/pdf", "text/plain"}
ALLOWED_EXTENSIONS = {".pdf", ".txt"}
MAX_FILE_SIZE_MB = 20

app = FastAPI(title="DocuMind API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

@app.get("/", include_in_schema=False)
async def serve_ui():
    return FileResponse(FRONTEND_DIR / "index.html")

# In-memory document registry {doc_id: {filename, chunk_count, ...}}
document_registry: dict[str, dict] = {}


# ── Models ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    doc_id: str
    question: str
    history: list[dict] = []


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int
    suggested_questions: list[str] = []


# ── Helpers ─────────────────────────────────────────────────────────────────

def validate_file(file: UploadFile) -> None:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: PDF, TXT.")


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/upload", response_model=DocumentInfo)
async def upload_document(file: UploadFile = File(...)):
    validate_file(file)

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(413, f"File too large ({size_mb:.1f} MB). Max is {MAX_FILE_SIZE_MB} MB.")

    doc_id = str(uuid.uuid4())
    suffix = Path(file.filename or "upload").suffix.lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)

    try:
        mime = "application/pdf" if suffix == ".pdf" else "text/plain"
        meta = ingest_document(tmp_path, doc_id, mime, original_filename=file.filename)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception as exc:
        logger.exception("Ingestion failed")
        raise HTTPException(500, f"Failed to process document: {exc}")
    finally:
        tmp_path.unlink(missing_ok=True)

    questions: list[str] = []
    try:
        chunk_meta = load_document(doc_id)
        questions = await generate_questions(chunk_meta[:3])
    except Exception:
        logger.warning("Question generation failed", exc_info=True)

    document_registry[doc_id] = {**meta, "suggested_questions": questions}
    return DocumentInfo(doc_id=doc_id, filename=meta["filename"], chunk_count=meta["chunk_count"], suggested_questions=questions)


@app.get("/documents", response_model=list[DocumentInfo])
async def list_documents():
    return [
        DocumentInfo(doc_id=v["doc_id"], filename=v["filename"], chunk_count=v["chunk_count"], suggested_questions=v.get("suggested_questions", []))
        for v in document_registry.values()
    ]


@app.post("/chat")
async def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(400, "Question cannot be empty.")

    if req.doc_id not in document_registry:
        raise HTTPException(404, "Document not found. Please upload it first.")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(500, "ANTHROPIC_API_KEY is not configured on the server.")

    try:
        chunks = retrieve_chunks(req.doc_id, req.question)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        logger.exception("Retrieval failed")
        raise HTTPException(500, f"Retrieval error: {exc}")

    sources = [
        {"filename": c["filename"], "chunk_index": c["chunk_index"], "relevance_score": c["relevance_score"], "text": c["text"]}
        for c in chunks
    ]

    async def event_stream():
        # First, emit source metadata as a special SSE event
        import json
        yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

        try:
            async for token in stream_answer(req.question, chunks, req.history):
                # Escape newlines so SSE framing stays intact
                escaped = token.replace("\n", "\\n")
                yield f"data: {escaped}\n\n"
        except Exception as exc:
            logger.exception("Streaming error")
            yield f"event: error\ndata: {str(exc)}\n\n"

        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    if doc_id not in document_registry:
        raise HTTPException(404, "Document not found.")

    from ingest import delete_document
    try:
        delete_document(doc_id)
    except Exception:
        pass

    del document_registry[doc_id]
    return {"message": "Document deleted."}

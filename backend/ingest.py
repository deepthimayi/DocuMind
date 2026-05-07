import fitz  # PyMuPDF
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
STORE_DIR = Path("./vector_store")


def store_path(doc_id: str) -> Path:
    STORE_DIR.mkdir(exist_ok=True)
    return STORE_DIR / f"{doc_id}.json"


def extract_text(file_path: Path, mime_type: str) -> str:
    if mime_type == "application/pdf" or file_path.suffix.lower() == ".pdf":
        doc = fitz.open(str(file_path))
        pages = [page.get_text() for page in doc]
        doc.close()
        return "\n".join(pages)
    return file_path.read_text(encoding="utf-8", errors="replace")


def chunk_text(text: str) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def ingest_document(file_path: Path, doc_id: str, mime_type: str, original_filename: str | None = None) -> dict:
    display_name = original_filename or file_path.name
    logger.info(f"Ingesting: {display_name}")

    text = extract_text(file_path, mime_type)
    if not text.strip():
        raise ValueError("Document appears to be empty or unreadable.")

    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("No text chunks produced from document.")

    metadata = [
        {"doc_id": doc_id, "chunk_index": i, "filename": display_name, "text": c}
        for i, c in enumerate(chunks)
    ]

    with open(store_path(doc_id), "w", encoding="utf-8") as f:
        json.dump(metadata, f)

    logger.info(f"Stored {len(chunks)} chunks for doc '{doc_id}'")
    return {"doc_id": doc_id, "filename": display_name, "chunk_count": len(chunks)}


def delete_document(doc_id: str) -> None:
    p = store_path(doc_id)
    if p.exists():
        p.unlink()


def load_document(doc_id: str) -> list[dict]:
    p = store_path(doc_id)
    if not p.exists():
        raise ValueError(f"Document '{doc_id}' not found. Please upload it first.")
    with open(p, encoding="utf-8") as f:
        return json.load(f)

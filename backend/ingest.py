import fitz  # PyMuPDF
import numpy as np
import json
import logging
from pathlib import Path
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
STORE_DIR = Path("./vector_store")

_embedder: TextEmbedding | None = None


def get_embedder() -> TextEmbedding:
    global _embedder
    if _embedder is None:
        logger.info("Loading fastembed model...")
        _embedder = TextEmbedding("BAAI/bge-small-en-v1.5")
    return _embedder


def store_path(doc_id: str) -> Path:
    STORE_DIR.mkdir(exist_ok=True)
    return STORE_DIR / f"{doc_id}.npz"


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

    embedder = get_embedder()
    embeddings = np.array(list(embedder.embed(chunks)), dtype=np.float32)

    metadata = [
        {"doc_id": doc_id, "chunk_index": i, "filename": display_name, "text": c}
        for i, c in enumerate(chunks)
    ]

    # Persist: embeddings matrix + metadata as JSON string
    np.savez_compressed(
        store_path(doc_id),
        embeddings=embeddings.astype(np.float32),
        metadata=np.array([json.dumps(m) for m in metadata]),
    )

    logger.info(f"Stored {len(chunks)} chunks for doc '{doc_id}'")
    return {
        "doc_id": doc_id,
        "filename": display_name,
        "chunk_count": len(chunks),
    }


def delete_document(doc_id: str) -> None:
    p = store_path(doc_id)
    if p.exists():
        p.unlink()


def load_document(doc_id: str) -> tuple[np.ndarray, list[dict]]:
    p = store_path(doc_id)
    if not p.exists():
        raise ValueError(f"Document '{doc_id}' not found. Please upload it first.")
    data = np.load(p, allow_pickle=False)
    embeddings = data["embeddings"]
    metadata = [json.loads(m) for m in data["metadata"]]
    return embeddings, metadata

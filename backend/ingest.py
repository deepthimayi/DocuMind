import fitz
import json
import logging
import os
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))


def get_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DATA_DIR / "documind.db"), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            chunk_count INTEGER NOT NULL,
            suggested_questions TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS chunks (
            doc_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            filename TEXT NOT NULL,
            text TEXT NOT NULL
        );
    """)
    return conn


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

    conn = get_db()
    try:
        conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        conn.execute(
            "INSERT INTO documents (doc_id, filename, chunk_count) VALUES (?, ?, ?)",
            (doc_id, display_name, len(chunks)),
        )
        conn.executemany(
            "INSERT INTO chunks (doc_id, chunk_index, filename, text) VALUES (?, ?, ?, ?)",
            [(doc_id, i, display_name, c) for i, c in enumerate(chunks)],
        )
        conn.commit()
    finally:
        conn.close()

    logger.info(f"Stored {len(chunks)} chunks for doc '{doc_id}'")
    return {"doc_id": doc_id, "filename": display_name, "chunk_count": len(chunks)}


def update_document_questions(doc_id: str, questions: list[str]) -> None:
    conn = get_db()
    try:
        conn.execute(
            "UPDATE documents SET suggested_questions = ? WHERE doc_id = ?",
            (json.dumps(questions), doc_id),
        )
        conn.commit()
    finally:
        conn.close()


def load_document(doc_id: str) -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT doc_id, chunk_index, filename, text FROM chunks WHERE doc_id = ? ORDER BY chunk_index",
            (doc_id,),
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        raise ValueError(f"Document '{doc_id}' not found. Please upload it first.")
    return [dict(row) for row in rows]


def load_all_documents() -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT doc_id, filename, chunk_count, suggested_questions FROM documents ORDER BY created_at"
        ).fetchall()
    finally:
        conn.close()
    result = []
    for row in rows:
        d = dict(row)
        d["suggested_questions"] = json.loads(d.get("suggested_questions") or "[]")
        result.append(d)
    return result


def delete_document(doc_id: str) -> None:
    conn = get_db()
    try:
        conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        conn.commit()
    finally:
        conn.close()

import logging
from rank_bm25 import BM25Okapi
from ingest import load_document

logger = logging.getLogger(__name__)

TOP_K = 3


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def retrieve_chunks(doc_id: str, query: str, top_k: int = TOP_K) -> list[dict]:
    metadata = load_document(doc_id)

    corpus = [_tokenize(m["text"]) for m in metadata]
    bm25 = BM25Okapi(corpus)

    scores = bm25.get_scores(_tokenize(query))
    max_score = max(scores) if max(scores) > 0 else 1.0

    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    results = []
    for idx in top_indices:
        m = metadata[idx]
        results.append({
            "text": m["text"],
            "chunk_index": m["chunk_index"],
            "filename": m["filename"],
            "relevance_score": round(float(scores[idx]) / max_score, 4),
        })

    logger.info(f"Retrieved {len(results)} chunks for doc '{doc_id}'")
    return results

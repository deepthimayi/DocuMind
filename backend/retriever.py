import numpy as np
import logging
from ingest import get_embedder, load_document

logger = logging.getLogger(__name__)

TOP_K = 3


def retrieve_chunks(doc_id: str, query: str, top_k: int = TOP_K) -> list[dict]:
    embeddings, metadata = load_document(doc_id)

    embedder = get_embedder()
    query_vec = embedder.encode([query], normalize_embeddings=True)[0].astype(np.float32)

    # Cosine similarity — embeddings are already L2-normalised, so dot product == cosine sim
    scores = embeddings @ query_vec
    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        m = metadata[idx]
        results.append({
            "text": m["text"],
            "chunk_index": m["chunk_index"],
            "filename": m["filename"],
            "relevance_score": round(float(scores[idx]), 4),
        })

    logger.info(f"Retrieved {len(results)} chunks for doc '{doc_id}'")
    return results

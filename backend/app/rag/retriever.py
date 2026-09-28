"""Policy retriever with a graceful keyword-search fallback.

Primary path: FAISS similarity search with Gemini embeddings.
Fallback (no API key / index failure): simple keyword scoring over policy
chunks, so the system still returns *grounded* (real policy text) context.
"""
from __future__ import annotations

import logging
import re
import threading

from app.rag.ingest import build_vector_store, load_policy_documents

logger = logging.getLogger(__name__)

_store = None
_store_lock = threading.Lock()
_index_failed = False


def get_vector_store():
    global _store, _index_failed
    if _store is not None or _index_failed:
        return _store
    with _store_lock:
        if _store is None and not _index_failed:
            _store = build_vector_store()
            if _store is None:
                _index_failed = True
    return _store


def _keyword_search(query: str, docs: list[dict], k: int = 3) -> list[dict]:
    tokens = set(re.findall(r"[a-z]{3,}", query.lower()))
    scored = []
    for d in docs:
        text = d["page_content"].lower()
        score = sum(text.count(t) for t in tokens)
        if score:
            scored.append((score, d))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:k]]


def retrieve_policy(query: str, k: int = 3) -> list[dict]:
    """Return up to k relevant policy chunks: [{"source", "content", "score"?}]."""
    store = get_vector_store()
    if store is not None:
        try:
            results = store.similarity_search_with_relevance_scores(query, k=k)
            return [
                {
                    "source": doc.metadata.get("source", "policy"),
                    "content": doc.page_content,
                    "score": round(float(score), 3),
                }
                for doc, score in results
                if score > 0.1  # drop irrelevant hits to avoid hallucinated grounding
            ]
        except Exception as exc:  # noqa: BLE001
            logger.error("Vector search failed, falling back to keyword search: %s", exc)

    docs = load_policy_documents()
    hits = _keyword_search(query, docs, k=k)
    return [
        {"source": h["metadata"]["source"], "content": h["page_content"], "score": None}
        for h in hits
    ]

"""RAG ingest: build a FAISS vector store from HR policy documents using Gemini embeddings.

If no GEMINI_API_KEY is configured, indexing is skipped and the retriever
degrades gracefully (the system still works for CRUD; policy answers fall
back to a keyword search over raw text).
"""
from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)

CHUNK_SIZE = 900
CHUNK_OVERLAP = 100


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if len(text) <= size:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        # try to break at a newline boundary
        if end < len(text):
            nl = text.rfind("\n", start, end)
            if nl > start + size // 2:
                end = nl
        chunks.append(text[start:end].strip())
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def load_policy_documents() -> list[dict]:
    """Read all policy .txt files and split into chunks with metadata."""
    docs = []
    for path in sorted(settings.policies_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        for i, chunk in enumerate(_chunk_text(text)):
            docs.append(
                {
                    "page_content": chunk,
                    "metadata": {"source": path.name, "chunk": i},
                }
            )
    return docs


def build_vector_store(force: bool = False):
    """Build (or load) the FAISS index. Returns a LangChain VectorStore or None."""
    if not settings.llm_enabled:
        logger.warning("GEMINI_API_KEY not set — skipping FAISS vector store build.")
        return None

    try:
        from langchain_community.vectorstores import FAISS
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            google_api_key=settings.gemini_api_key,
        )
        index_file = settings.faiss_index_dir / "index.faiss"
        if index_file.exists() and not force:
            return FAISS.load_local(
                str(settings.faiss_index_dir), embeddings, allow_dangerous_deserialization=True
            )

        from langchain_core.documents import Document

        docs = [Document(**d) for d in load_policy_documents()]
        if not docs:
            logger.warning("No policy documents found in %s", settings.policies_dir)
            return None
        store = FAISS.from_documents(docs, embeddings)
        store.save_local(str(settings.faiss_index_dir))
        logger.info("Built FAISS index with %d chunks.", len(docs))
        return store
    except Exception as exc:  # noqa: BLE001 — never let RAG failure break the app
        logger.error("Failed to build vector store: %s", exc)
        return None

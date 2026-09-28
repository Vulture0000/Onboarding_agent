"""Policy tools: RAG retrieval + grounded answering (Rule 3).

The full HR policy text is never stuffed into prompts — only retrieved chunks.
If retrieval yields nothing relevant, the tool returns a canonical
"insufficient information" answer instead of hallucinating.
"""
from __future__ import annotations

import logging

from app.agents.llm import llm_complete
from app.rag.retriever import retrieve_policy

logger = logging.getLogger(__name__)

INSUFFICIENT_INFO = (
    "I could not find enough information in the company policy to answer this confidently."
)

ANSWER_PROMPT = """You are the HR Policy Assistant for Acme Corp.
Answer the employee's question using ONLY the policy excerpts below.
- Be concise and factual. Quote specific numbers/limits when present.
- If the excerpts do not contain the answer, respond EXACTLY with: {insufficient}
- Never invent policies.

POLICY EXCERPTS:
{context}

QUESTION: {question}"""


def search_policy(query: str, k: int = 3) -> list[dict]:
    """Retrieve relevant policy chunks (FAISS or keyword fallback)."""
    try:
        return retrieve_policy(query, k=k)
    except Exception as exc:  # noqa: BLE001
        logger.error("Policy retrieval failed: %s", exc)
        return []


def answer_policy_question(question: str, k: int = 3) -> tuple[str, list[dict]]:
    """Return (grounded_answer, sources)."""
    sources = search_policy(question, k=k)
    if not sources:
        return INSUFFICIENT_INFO, []

    context = "\n\n".join(
        f"[Source: {s['source']}]\n{s['content']}" for s in sources
    )
    answer = llm_complete(
        ANSWER_PROMPT.format(context=context, question=question, insufficient=INSUFFICIENT_INFO)
    )
    if not answer:
        # LLM unavailable — return grounded excerpt directly (still no hallucination)
        best = sources[0]
        answer = f"From {best['source']}:\n\n{best['content'][:800]}"
        return answer, sources
    return answer.strip(), sources

"""Policy / RAG Agent: retrieves HR policy via FAISS and gives grounded answers.

Also serves as the policy-context provider for the Leave Agent and Onboarding
Agent through shared graph state (Rule 4). Never hallucinates policy: if
retrieval is insufficient it says so explicitly.
"""
from __future__ import annotations

import logging

from app.db import crud
from app.db.database import SessionLocal
from app.graph.state import OnboardingState
from app.tools import policy_tools

logger = logging.getLogger(__name__)


def policy_agent_node(state: OnboardingState) -> dict:
    db = SessionLocal()
    try:
        # When invoked mid-leave-flow, answer the policy question the Leave
        # Agent put into state; otherwise answer the user's question.
        question = state.get("policy_question") or state.get("user_message") or ""
        if not question:
            return {"current_agent": "policy_agent",
                    "error": "PolicyAgent needs a question."}

        answer, sources = policy_tools.answer_policy_question(question)
        grounded = bool(sources)

        crud.log_agent(
            db, "PolicyAgent", "policy_query",
            employee_id=state.get("employee_id"),
            status="completed" if grounded else "warning",
            detail=f"Q: {question[:120]} | sources: {', '.join(s['source'] for s in sources) or 'none'}",
        )

        messages = list(state.get("messages") or [])
        messages.append({
            "role": "assistant", "agent": "PolicyAgent", "content": answer,
        })
        return {
            "current_agent": "policy_agent",
            "policy_answer": answer,
            "policy_context": sources,
            "messages": messages,
            "result": {**(state.get("result") or {}),
                       "policy_answer": answer, "sources": sources},
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("PolicyAgent failed")
        crud.log_agent(db, "PolicyAgent", "agent_error", status="error", detail=str(exc))
        return {"current_agent": "policy_agent",
                "policy_answer": policy_tools.INSUFFICIENT_INFO,
                "error": f"PolicyAgent failed: {exc}"}
    finally:
        db.close()

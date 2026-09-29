"""Policy query endpoint (RAG chatbot)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas import PolicyAnswer, PolicyQuery
from app.db import crud
from app.db.database import get_db
from app.db.models import User
from app.tools import policy_tools

router = APIRouter(prefix="/api/policy", tags=["policy"])


@router.post("/query", response_model=PolicyAnswer)
def query_policy(payload: PolicyQuery, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """Open to every signed-in role — policies are not sensitive."""
    answer, sources = policy_tools.answer_policy_question(payload.question)
    crud.log_agent(db, "PolicyAgent", "policy_query_api",
                   status="completed" if sources else "warning",
                   detail=f"Q: {payload.question[:120]} | by {user.name}")
    return PolicyAnswer(question=payload.question, answer=answer, sources=sources)

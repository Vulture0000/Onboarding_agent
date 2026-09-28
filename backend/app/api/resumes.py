"""Resume upload endpoint — triggers the full LangGraph resume workflow."""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.schemas import AgentRunResponse, ResumeOut
from app.config import settings
from app.db import crud
from app.db.database import get_db
from app.graph import workflow
from app.tools.resume_tools import extract_text_from_pdf

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


@router.get("", response_model=list[ResumeOut])
def list_resumes(db: Session = Depends(get_db)):
    return crud.list_resumes(db)


@router.post("/upload", response_model=AgentRunResponse)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a PDF resume and run: Resume -> Onboarding -> Calendar agents."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF resumes are supported.")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Uploaded file is empty.")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "Resume exceeds 10 MB limit.")

    # Persist the upload
    stored_name = f"{uuid.uuid4().hex}.pdf"
    stored_path = settings.uploads_dir / stored_name
    stored_path.write_bytes(content)

    try:
        text = extract_text_from_pdf(content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, f"Could not read PDF: {exc}") from exc
    if not text.strip():
        raise HTTPException(422, "No extractable text found in this PDF (is it a scanned image?).")

    resume = crud.create_resume(
        db, filename=file.filename, stored_path=str(stored_path),
        extracted_text=text, extraction_method="pending",
    )
    crud.log_agent(db, "ResumeAgent", "resume_uploaded",
                   detail=f"Received {file.filename} ({len(content)} bytes), extracted {len(text)} chars of text.")

    thread_id = f"resume-{resume.id}-{uuid.uuid4().hex[:8]}"
    try:
        result = workflow.run_workflow(
            {
                "request_type": "resume",
                "resume_file_id": resume.id,
                "resume_data": {"_text": text},
                "result": {"thread_id": thread_id},
                "messages": [],
            },
            thread_id=thread_id,
        )
    except Exception as exc:  # noqa: BLE001
        crud.log_agent(db, "Supervisor", "workflow_error", status="error", detail=str(exc))
        raise HTTPException(500, "The onboarding workflow failed. Check agent activity for details.") from exc

    if result.get("error"):
        raise HTTPException(422, result["error"])
    return AgentRunResponse(**result)

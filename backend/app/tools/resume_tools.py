"""Resume tools: PDF text extraction + structured info extraction.

LLM (Gemini) is used for extraction when available; a deterministic
regex/heuristic fallback keeps the pipeline working offline (Rule 7).
"""
from __future__ import annotations

import io
import logging
import re

from app.agents.llm import llm_json

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are an HR data extraction assistant. Extract structured information
from the resume text below. Return ONLY valid JSON with exactly these keys:

{{
  "name": string,
  "email": string or null,
  "phone": string or null,
  "education": string (highest qualification, one line),
  "skills": [list of technical/professional skills],
  "experience": string (e.g. "Fresher" or "3 years"),
  "projects": [list of short project titles/summaries, max 5],
  "role": string (best-fit job role, e.g. "Software Engineer"),
  "department": string (one of: Engineering, Data, Design, Human Resources, Marketing, Sales, Finance, Operations)
}}

Do NOT make hiring decisions or judgments. Only extract facts present in the text.
If a field is missing, use null (or empty list for lists).

RESUME TEXT:
\"\"\"
{text}
\"\"\""""

SKILL_KEYWORDS = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "Ruby", "PHP",
    "React", "Angular", "Vue", "Node.js", "FastAPI", "Django", "Flask", "Spring",
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Jenkins", "CI/CD",
    "Machine Learning", "Deep Learning", "NLP", "TensorFlow", "PyTorch", "Pandas", "NumPy",
    "Figma", "Sketch", "Adobe XD", "Photoshop", "Illustrator", "UX Research", "Prototyping",
    "Git", "Linux", "REST API", "GraphQL", "Microservices", "Agile", "Scrum",
    "Excel", "Power BI", "Tableau", "Looker", "Statistics",
    "Recruitment", "Payroll", "Employee Relations", "HRIS",
]

DEPARTMENT_HINTS = {
    "Engineering": ["python", "java", "react", "node", "fastapi", "django", "spring", "microservice", "c++", "golang", "software"],
    "Data": ["sql", "pandas", "machine learning", "statistics", "power bi", "tableau", "data analyst", "data science", "numpy"],
    "Design": ["figma", "sketch", "adobe", "ux", "ui design", "prototyping", "designer"],
    "Human Resources": ["recruitment", "payroll", "hris", "human resources", "employee relations"],
    "Marketing": ["seo", "content marketing", "campaign", "social media", "brand"],
    "Finance": ["accounting", "financial", "audit", "gst", "ledger"],
}


def extract_text_from_pdf(content: bytes) -> str:
    """Extract raw text from PDF bytes using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def _fallback_extract(text: str) -> dict:
    """Deterministic regex/heuristic extraction used when the LLM is unavailable."""
    email_m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    phone_m = re.search(r"(?:\+?\d{1,3}[\s-]?)?(?:\(\d{3}\)|\d{5})[\s-]?\d{3,5}[\s-]?\d{4}", text)

    # Name: first non-empty line that looks like a name (letters, spaces, maybe a dot)
    name = None
    for line in text.splitlines():
        line = line.strip()
        if line and re.fullmatch(r"[A-Za-z][A-Za-z.\-' ]{2,40}", line):
            name = re.sub(r"\s+", " ", line).title()
            break

    skills = [s for s in SKILL_KEYWORDS if re.search(re.escape(s), text, re.IGNORECASE)]

    edu_m = re.search(
        r"((?:B\.?E\.?|B\.?Tech|B\.?Sc|M\.?Tech|M\.?Sc|MBA|MCA|BCA|B\.?A\.?|M\.?A\.?|B\.?Des|Ph\.?D)[^\n]{0,60})",
        text,
        re.IGNORECASE,
    )

    exp_years = re.search(r"(\d{1,2})\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience)?", text, re.IGNORECASE)
    experience = f"{exp_years.group(1)} years" if exp_years else (
        "Fresher" if re.search(r"fresher|intern|no experience", text, re.IGNORECASE) else None
    )

    lower = text.lower()
    department = None
    best = 0
    for dept, hints in DEPARTMENT_HINTS.items():
        score = sum(1 for h in hints if h in lower)
        if score > best:
            department, best = dept, score

    role = None
    role_m = re.search(
        r"(software engineer|data analyst|data scientist|devops engineer|frontend developer|backend developer|"
        r"full stack developer|product designer|ui/ux designer|hr executive|hr manager|marketing manager|"
        r"product manager|qa engineer|systems engineer)",
        lower,
    )
    if role_m:
        role = role_m.group(1).title()
    elif department == "Engineering":
        role = "Software Engineer"
    elif department == "Data":
        role = "Data Analyst"
    elif department == "Design":
        role = "Product Designer"
    elif department == "Human Resources":
        role = "HR Executive"

    return {
        "name": name,
        "email": email_m.group(0) if email_m else None,
        "phone": phone_m.group(0) if phone_m else None,
        "education": edu_m.group(1).strip() if edu_m else None,
        "skills": skills[:15],
        "experience": experience,
        "projects": [],
        "role": role,
        "department": department or "Engineering",
    }


def extract_structured_info(text: str) -> tuple[dict, str]:
    """Return (structured_info, method) where method is 'llm' or 'fallback'."""
    if text:
        result = llm_json(EXTRACTION_PROMPT.format(text=text[:12000]))
        if result and result.get("name"):
            # normalize
            result.setdefault("skills", [])
            result.setdefault("projects", [])
            if isinstance(result.get("skills"), str):
                result["skills"] = [s.strip() for s in result["skills"].split(",") if s.strip()]
            return result, "llm"
    return _fallback_extract(text), "fallback"

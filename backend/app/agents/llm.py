"""Shared LLM (Gemini) access for agents.

Rule 7: the system must work even if the LLM is unavailable. Every function
here returns None on failure, and callers implement deterministic fallbacks.
"""
from __future__ import annotations

import json
import logging
import re

from app.config import settings

logger = logging.getLogger(__name__)

_llm = None


def get_llm():
    """Return a ChatGoogleGenerativeAI instance, or None if unavailable."""
    global _llm
    if _llm is not None:
        return _llm
    if not settings.llm_enabled:
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        _llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.1,
            max_tokens=2048,
        )
        return _llm
    except Exception as exc:  # noqa: BLE001
        logger.error("LLM init failed: %s", exc)
        return None


def llm_complete(prompt: str, system: str | None = None) -> str | None:
    """Simple text completion. Returns None when LLM is unavailable."""
    llm = get_llm()
    if llm is None:
        return None
    try:
        messages = []
        if system:
            messages.append(("system", system))
        messages.append(("human", prompt))
        resp = llm.invoke(messages)
        return resp.content
    except Exception as exc:  # noqa: BLE001
        logger.error("LLM call failed: %s", exc)
        return None


def llm_json(prompt: str, system: str | None = None) -> dict | None:
    """LLM completion parsed as JSON. Returns None on failure/invalid JSON."""
    text = llm_complete(prompt, system)
    if not text:
        return None
    try:
        # strip markdown fences if present
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL)
        return json.loads(text)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("LLM JSON parse failed: %s", exc)
        return None


from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps.store import get_current_store_web
from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.db.session import get_db
from app.models.store import Store
from app.schemas.common import Audience, PrincipalType

logger = logging.getLogger(__name__)

try:
    from google import genai
except ImportError:  # pragma: no cover
    genai = None  # type: ignore[assignment]


router = APIRouter(
    prefix="/store/ai",
    tags=["store-ai"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.store, audience=Audience.web))],
)


class PromptRule(BaseModel):
    raw: str = Field(default="", max_length=4000)
    generated: str = Field(default="", max_length=8000)


class PromptsOut(BaseModel):
    prompts: list[PromptRule]


class PromptGenerateIn(BaseModel):
    raw: str = Field(min_length=1, max_length=4000)


class PromptGenerateOut(BaseModel):
    generated: str


class PromptsSaveIn(BaseModel):
    prompts: list[PromptRule] = Field(default_factory=list, max_length=50)


_GENERATE_INSTRUCTION = """\
You are an AI prompt engineer for a restaurant voice ordering system.

The restaurant owner below has written ONE plain-language rule they want the
voice assistant to follow when taking customer orders. Rewrite it as a single
concise imperative instruction (1-3 short sentences or 1-4 short bullet lines)
that will be appended to the assistant's system prompt.

Rules:
- Use imperative voice ("Recommend...", "Warn...", "Ask...").
- Preserve every concrete fact, number, and constraint the owner stated.
- Do NOT add behavior the owner didn't mention. Do NOT contradict core
  ordering-assistant behavior (tool use, order flow, checkout).
- Output only the rewritten instruction, no preamble, no markdown fences.

Owner's rule:
\"\"\"{raw}\"\"\"
"""


@router.get("/prompts", response_model=PromptsOut)
def list_prompts(current_store: Store = Depends(get_current_store_web)) -> PromptsOut:
    items = [PromptRule(**p) for p in (current_store.custom_prompts or []) if isinstance(p, dict)]
    return PromptsOut(prompts=items)


@router.post("/prompts/generate", response_model=PromptGenerateOut)
def generate_prompt(
    payload: PromptGenerateIn,
    _: Store = Depends(get_current_store_web),
) -> PromptGenerateOut:
    if genai is None:
        raise AppError(status_code=503, code="genai_unavailable", detail="Gemini SDK not installed")

    api_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise AppError(status_code=503, code="genai_no_key", detail="Gemini API key not configured")

    prompt = _GENERATE_INSTRUCTION.format(raw=payload.raw.strip())

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
        )
        generated = (response.text or "").strip()
    except Exception as exc:
        logger.warning("Prompt generation failed", exc_info=True)
        raise AppError(status_code=502, code="generation_failed", detail=f"Gemini error: {exc}")

    if not generated:
        raise AppError(status_code=502, code="empty_generation", detail="Gemini returned empty text")

    return PromptGenerateOut(generated=generated)


@router.put("/prompts", response_model=PromptsOut)
def save_prompts(
    payload: PromptsSaveIn,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> PromptsOut:
    # Drop rows where both fields are blank — no point persisting empty rules.
    cleaned = [
        {"raw": p.raw.strip(), "generated": p.generated.strip()}
        for p in payload.prompts
        if p.raw.strip() or p.generated.strip()
    ]
    current_store.custom_prompts = cleaned
    # JSONB mutation via assignment is tracked, but flag_modified is defensive
    # in case a caller mutates in place rather than reassigning.
    flag_modified(current_store, "custom_prompts")
    db.add(current_store)
    db.commit()
    db.refresh(current_store)
    return PromptsOut(prompts=[PromptRule(**p) for p in current_store.custom_prompts])

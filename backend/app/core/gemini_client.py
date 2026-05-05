"""Single entry point for constructing google-genai clients.

Callers don't need to know whether we're on Vertex AI or the Gemini API —
this module reads `settings` and returns a ready-to-use client plus the
model ID appropriate for that surface. Switching surfaces is a config flip
(``GEMINI_USE_VERTEX=true`` and ``GOOGLE_CLOUD_PROJECT``), not a code change.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from google import genai
except ImportError:  # pragma: no cover — google-genai is a hard dependency
    genai = None  # type: ignore[assignment]


@dataclass(frozen=True)
class GenAIClientBundle:
    """A ready-to-use client + the model ID appropriate for the backing surface.

    Keeping the model ID here means call sites don't have to branch on Vertex vs.
    API to pick the right model name (Vertex uses the ``google/`` prefix for
    some models; the Gemini API does not).
    """

    client: "genai.Client"
    background_model: str
    surface: str  # "vertex" or "api"


def make_genai_client() -> GenAIClientBundle:
    """Build a ``genai.Client`` for the configured surface.

    Vertex: requires ``GOOGLE_CLOUD_PROJECT`` + ``GOOGLE_CLOUD_LOCATION`` and
    Application Default Credentials (attached service account on GCE, or
    ``gcloud auth application-default login`` on dev machines).

    Gemini API: requires ``GOOGLE_API_KEY`` / ``GEMINI_API_KEY`` in env.

    Raises ``RuntimeError`` if the surface isn't configured.
    """
    if genai is None:
        raise RuntimeError("google-genai is not installed")

    if settings.gemini_use_vertex:
        project = settings.google_cloud_project.strip()
        location = settings.google_cloud_location.strip() or "us-central1"
        if not project:
            raise RuntimeError(
                "GEMINI_USE_VERTEX is true but GOOGLE_CLOUD_PROJECT is empty"
            )
        client = genai.Client(vertexai=True, project=project, location=location)
        return GenAIClientBundle(
            client=client,
            background_model=settings.gemini_background_model_vertex,
            surface="vertex",
        )

    api_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("No Gemini API key configured (set GOOGLE_API_KEY or GEMINI_API_KEY)")
    client = genai.Client(api_key=api_key)
    return GenAIClientBundle(
        client=client,
        background_model=settings.gemini_background_model_api,
        surface="api",
    )

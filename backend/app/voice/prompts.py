from __future__ import annotations

from typing import Iterable


def build_system_prompt(menu_lines: Iterable[str] | None = None) -> str:
    menu_text = ""
    if menu_lines:
        menu_text = "\n".join(menu_lines)

    prompt = """
You are a voice assistant for a food ordering service.
Keep responses short (1-2 sentences).

Rules:
- Never claim you added/removed items unless a tool confirms it.
- If the user says something unclear, ask a short clarification question.
- When the user is done, ask if they want to checkout.
""".strip()

    if menu_text:
        prompt = f"{prompt}\n\nMenu:\n{menu_text}"

    return prompt

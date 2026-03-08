"""Async conversation monitor that validates the voice bot's behavior.

Runs a strong LLM (e.g. Gemini Pro) in the background after each assistant
turn to check for issues like hallucinated prices, skipped tool calls,
menu violations, etc.  When an issue is found it injects a correction
message into the pipeline so the bot self-corrects on the next turn.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("voice.monitor")

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]

try:
    from pipecat.frames.frames import LLMMessagesAppendFrame
except ImportError:
    LLMMessagesAppendFrame = None  # type: ignore[assignment,misc]


# The monitor's own system prompt — tells it what to look for.
MONITOR_SYSTEM_PROMPT = """\
You are a QA monitor for a voice-based food ordering AI assistant.

You will receive:
1. The MENU the bot is using.
2. The CONVERSATION so far (user messages, assistant messages, tool calls and their results).

Your job is to find **errors in the assistant's LAST response only**. Check for:

- **Wrong prices**: The assistant stated a price that doesn't match the tool result or the menu.
- **Hallucinated items**: The assistant mentioned a menu item that doesn't exist.
- **Skipped tool calls**: The assistant claimed to add/remove an item or gave a total without calling the appropriate tool.
- **Ignored tool results**: The assistant said something that contradicts what the tool returned (e.g. tool returned $14.99 but assistant said $0 or a different amount).
- **Wrong size handling**: The assistant added an item without asking for size when the menu shows size-based pricing (S/M/L).
- **Upselling**: The assistant suggested or recommended items when the customer didn't ask.

If the last assistant response is correct, respond with exactly: OK

If there is an error, respond with a short correction message (1-2 sentences) that the bot should say to the customer. Start with "CORRECTION:" followed by the message. Example:
CORRECTION: I apologize, the Kung Pao Chicken medium is actually $14.99, not $10.99.

Only flag clear, factual errors. Do NOT flag tone, style, or minor wording issues.
"""


@dataclass
class MonitorConfig:
    """Configuration for the conversation monitor."""
    model: str = "gemini-3.1-flash-lite-preview"
    enabled: bool = True
    # Only check turns that involve tool calls or prices (skip casual chat)
    check_all_turns: bool = True


@dataclass
class ConversationMonitor:
    """Async monitor that validates bot responses against tool results and menu data."""

    menu_text: str = ""
    config: MonitorConfig = field(default_factory=MonitorConfig)
    _client: Any = field(default=None, init=False, repr=False)
    _pipeline_task: Any = field(default=None, init=False, repr=False)
    _pending_task: asyncio.Task | None = field(default=None, init=False, repr=False)
    _conversation: list[dict[str, str]] = field(default_factory=list, init=False)

    def attach(self, pipeline_task: Any) -> None:
        """Attach to a pipeline task so corrections can be injected."""
        self._pipeline_task = pipeline_task

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if genai is None:
            logger.warning("google-genai not installed; monitor disabled")
            self.config.enabled = False
            return None
        api_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
        if not api_key:
            logger.warning("No API key for monitor; disabled")
            self.config.enabled = False
            return None
        self._client = genai.Client(api_key=api_key)
        return self._client

    def record_user(self, text: str) -> None:
        """Record a user transcript."""
        self._conversation.append({"role": "user", "text": text})

    def record_assistant(self, text: str) -> None:
        """Record an assistant transcript and trigger async check."""
        self._conversation.append({"role": "assistant", "text": text})
        if self.config.enabled and self._pipeline_task is not None:
            self._schedule_check()

    def record_tool_call(self, name: str, args: dict) -> None:
        """Record a tool call made by the assistant."""
        self._conversation.append({"role": "tool_call", "text": f"{name}({args})"})

    def record_tool_result(self, name: str, result: dict) -> None:
        """Record the result of a tool call."""
        self._conversation.append({"role": "tool_result", "text": f"{name} → {result}"})

    def _schedule_check(self) -> None:
        """Schedule an async check, cancelling any previous pending check."""
        if self._pending_task and not self._pending_task.done():
            self._pending_task.cancel()
        self._pending_task = asyncio.create_task(self._check_last_turn())

    async def _check_last_turn(self) -> None:
        """Call the monitor LLM to validate the last assistant response."""
        try:
            client = self._get_client()
            if client is None:
                return

            conversation_text = self._format_conversation()
            prompt = (
                f"## MENU\n{self.menu_text}\n\n"
                f"## CONVERSATION\n{conversation_text}\n\n"
                "Check the assistant's LAST response for errors."
            )

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.config.model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=MONITOR_SYSTEM_PROMPT,
                    temperature=0.1,
                    max_output_tokens=256,
                ),
            )

            result_text = (response.text or "").strip()
            logger.debug("Monitor result: %s", result_text)

            if result_text.upper().startswith("OK"):
                return

            if result_text.upper().startswith("CORRECTION:"):
                correction = result_text[len("CORRECTION:"):].strip()
                if correction:
                    await self._inject_correction(correction)

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Monitor check failed")

    async def _inject_correction(self, correction: str) -> None:
        """Inject a correction message into the pipeline."""
        if self._pipeline_task is None or LLMMessagesAppendFrame is None:
            return

        logger.info("Monitor injecting correction: %s", correction)
        msg = {
            "role": "user",
            "content": (
                f"[SYSTEM CORRECTION — You made an error in your last response. "
                f"Please correct it now by telling the customer: {correction}]"
            ),
        }
        frame = LLMMessagesAppendFrame(messages=[msg], run_llm=True)
        await self._pipeline_task.queue_frame(frame)

    def _format_conversation(self) -> str:
        """Format the conversation history for the monitor prompt."""
        lines = []
        for entry in self._conversation:
            role = entry["role"]
            text = entry["text"]
            if role == "user":
                lines.append(f"USER: {text}")
            elif role == "assistant":
                lines.append(f"ASSISTANT: {text}")
            elif role == "tool_call":
                lines.append(f"  [TOOL CALL] {text}")
            elif role == "tool_result":
                lines.append(f"  [TOOL RESULT] {text}")
        return "\n".join(lines)

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from app.voice.tool_router import VoiceToolContext, VoiceToolRouter

if TYPE_CHECKING:
    from app.voice.monitor import ConversationMonitor

logger = logging.getLogger("voice.tools")

try:
    from google import genai
except ImportError:
    genai = None  # type: ignore[assignment]


_NOTE_VERIFY_PROMPT = """\
You are a QA checker for a restaurant voice ordering system.

The customer said something and an item was added to the order. Your job is to check if ANY preferences, modifications, or special requests from the customer's speech are missing from the item's note.

Customer said: "{user_transcript}"
Item added: "{item_name}"
Note on item: "{current_note}"

Check for missing preferences like:
- Spice level (extra spicy, mild, no spice)
- Ingredient removals (no onions, no MSG, no nuts)
- Ingredient additions (extra cheese, add avocado)
- Cooking preferences (well done, crispy, steamed)
- Any other modification the customer mentioned for this item

If ALL preferences are captured (or the customer didn't mention any), respond with exactly: OK

If something is missing, respond with ONLY the complete note text that should replace the current note (combine existing note with missing parts). Do NOT include any explanation, just the note text.
Example: extra spicy, no onions, well done"""

GEMINI_VOICE_TOOLS_SCHEMA = [
    {
        "function_declarations": [
            {
                "name": "add_item",
                "description": "Add an item to the current order.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "menu_item_id": {
                            "type": "string",
                            "description": "UUID of the menu item to add.",
                        },
                        "item_name": {
                            "type": "string",
                            "description": "Name of the menu item to add if ID is unknown.",
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "Quantity to add",
                        },
                        "size": {
                            "type": "string",
                            "enum": ["small", "medium", "large"],
                            "description": "Size of the item (small, medium, or large). Only use when the item has size-based pricing.",
                        },
                        "note": {
                            "type": "string",
                            "description": "Special instructions or preferences for this item (e.g. 'extra spicy', 'no onions', 'well done').",
                        },
                    },
                    "required": ["quantity"],
                },
            },
            {
                "name": "remove_item",
                "description": "Remove an item from the current order.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_item_id": {
                            "type": "string",
                            "description": "UUID of the order item to remove.",
                        },
                        "menu_item_id": {
                            "type": "string",
                            "description": "UUID of the menu item to remove from the order.",
                        },
                        "item_name": {
                            "type": "string",
                            "description": "Name of the item to remove if IDs are unknown.",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "update_item",
                "description": "Update an existing item in the order. Use this to change the note, quantity, or size of an item already in the order — much faster than remove + re-add.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_item_id": {
                            "type": "string",
                            "description": "UUID of the order item to update.",
                        },
                        "item_name": {
                            "type": "string",
                            "description": "Name of the item to update if order_item_id is unknown.",
                        },
                        "note": {
                            "type": "string",
                            "description": "New special instructions or preferences for this item.",
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "New quantity for this item.",
                        },
                        "size": {
                            "type": "string",
                            "enum": ["small", "medium", "large"],
                            "description": "New size for this item.",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "get_summary",
                "description": "Get current order summary and totals.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "set_order_note",
                "description": "Set a note on the entire order (e.g. 'no utensils', 'leave at door', 'allergic to peanuts').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "note": {
                            "type": "string",
                            "description": "The note to attach to the order.",
                        },
                    },
                    "required": ["note"],
                },
            },
            {
                "name": "set_fulfillment",
                "description": "Record whether the order is for pickup or delivery. Call this as soon as the customer states their choice. For delivery you MUST include the customer's delivery address.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["pickup", "delivery"],
                            "description": "Either 'pickup' or 'delivery'.",
                        },
                        "delivery_address": {
                            "type": "string",
                            "description": "The customer's delivery address. Required when type is 'delivery'. Leave empty for pickup.",
                        },
                    },
                    "required": ["type"],
                },
            },
            {
                "name": "checkout",
                "description": "Finalize the order. Must include the customer's name for pickup/delivery identification.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_name": {
                            "type": "string",
                            "description": "The customer's name for the order.",
                        },
                    },
                    "required": ["customer_name"],
                },
            },
        ]
    }
]


def _extract_args(params: Any) -> dict:
    """Extract arguments from the tool call parameters, supporting both structured and unstructured formats."""
    if hasattr(params, "arguments"):
        return params.arguments or {}
    if isinstance(params, dict):
        return params
    return {}


def _result_callback(params: Any) -> Callable[[Any], Awaitable[Any]] | None:
    """Extract the result callback from the tool call parameters, if it exists."""
    return getattr(params, "result_callback", None)


async def _verify_and_update_note(
    router: VoiceToolRouter,
    monitor: "ConversationMonitor | None",
    result: dict[str, Any],
    on_order_update: Callable[[dict], Awaitable[None]] | None,
    user_transcript: str = "",
) -> None:
    """Background task: compare user transcript vs added item, update note if needed."""
    logger.info("Note verify: starting, transcript='%s', has_monitor=%s", user_transcript[:100], monitor is not None)
    if genai is None:
        logger.info("Note verify: skipped — genai not installed")
        return
    if not result.get("ok") or not result.get("order"):
        logger.info("Note verify: skipped — result not ok or no order")
        return

    # Use passed transcript first, fall back to monitor history
    if not user_transcript and monitor is not None:
        for entry in reversed(monitor._conversation):
            if entry["role"] == "user":
                user_transcript = entry["text"]
                break
    if not user_transcript:
        logger.info("Note verify: skipped — no user transcript available")
        return

    # Get the last added item from the order
    order_data = result["order"]
    items = order_data.get("items", [])
    if not items:
        return
    last_item = items[-1]
    item_name = last_item.get("name", "")
    current_note = last_item.get("note", "")

    api_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        return

    try:
        client = genai.Client(api_key=api_key)
        prompt = _NOTE_VERIFY_PROMPT.format(
            user_transcript=user_transcript,
            item_name=item_name,
            current_note=current_note or "(none)",
        )
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-3-flash-preview",
            contents=prompt,
        )
        answer = response.text.strip()

        logger.info("Note verify: LLM response='%s' for item='%s'", answer[:200], item_name)
        if answer == "OK" or not answer:
            return

        # LLM returned a better note — update the order item
        new_note = answer
        logger.info("Note verify: updating %s note from '%s' to '%s'", item_name, current_note, new_note)

        order_item_id = last_item.get("order_item_id")
        if order_item_id:
            import uuid
            updated = await asyncio.to_thread(
                router.update_item_note,
                order_item_id=uuid.UUID(order_item_id),
                note=new_note,
            )
            if updated and on_order_update is not None:
                await on_order_update(updated.get("order", {}))

    except Exception:
        logger.warning("Note verify failed", exc_info=True)


def create_voice_tool_handlers(
    context: VoiceToolContext,
    monitor: "ConversationMonitor | None" = None,
    on_order_update: Callable[[dict], Awaitable[None]] | None = None,
) -> dict[str, Callable[[Any], Awaitable[Any]]]:
    """Create async tool handler functions for voice interactions, using the provided context to perform actions."""
    router = VoiceToolRouter(context)

    async def _notify_order(result: dict) -> None:
        """Send order update to the client if the tool result contains order data."""
        if on_order_update is not None and result.get("ok") and result.get("order"):
            await on_order_update(result["order"])

    async def _run_shielded(name: str, params: Any, work: Callable[[], Awaitable[dict]]) -> dict:
        """Run a tool's work in a shielded background task so the DB commit and
        result_callback still complete if pipecat cancels the outer coroutine
        (which happens when a user utterance races with a function-call
        dispatch). The background task re-attempts the callback even post-cancel
        — pipecat may ignore it, but when it accepts, Gemini unsticks from
        'awaiting tool result' and resumes speaking."""
        callback = _result_callback(params)

        async def _do_work() -> dict:
            try:
                result = await work()
            except Exception:
                logger.error("%s background work failed", name, exc_info=True)
                result = {"ok": False, "message": "Internal error."}
            if callback is not None:
                try:
                    await callback(result)
                except Exception:
                    logger.warning("%s result_callback failed (likely post-cancel)", name, exc_info=True)
            return result

        task = asyncio.create_task(_do_work())
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            logger.info("%s handler cancelled by pipecat; background task continues", name)
            raise

    async def add_item(params: Any):
        args = _extract_args(params)
        if monitor is not None:
            monitor.record_tool_call("add_item", args)

        async def _work() -> dict:
            result = await asyncio.to_thread(
                router.add_item,
                menu_item_id=_parse_uuid(args.get("menu_item_id")),
                item_name=(args.get("item_name") or None),
                quantity=int(args.get("quantity", 1) or 1),
                size=(args.get("size") or None),
                note=(args.get("note") or None),
            )
            if monitor is not None:
                monitor.record_tool_result("add_item", result)
            await _notify_order(result)
            _transcript_parts = []
            if monitor is not None:
                for entry in reversed(monitor._conversation):
                    if entry["role"] == "user":
                        _transcript_parts.append(entry["text"])
                        break
            _item_name_arg = args.get("item_name") or ""
            if _item_name_arg and _item_name_arg not in " ".join(_transcript_parts):
                _transcript_parts.append(_item_name_arg)
            _user_transcript = " ".join(_transcript_parts)
            asyncio.create_task(_verify_and_update_note(router, monitor, result, on_order_update, user_transcript=_user_transcript))
            return result

        return await _run_shielded("add_item", params, _work)

    async def remove_item(params: Any):
        args = _extract_args(params)
        if monitor is not None:
            monitor.record_tool_call("remove_item", args)

        async def _work() -> dict:
            result = await asyncio.to_thread(
                router.remove_item,
                order_item_id=_parse_uuid(args.get("order_item_id")),
                menu_item_id=_parse_uuid(args.get("menu_item_id")),
                item_name=(args.get("item_name") or None),
            )
            if monitor is not None:
                monitor.record_tool_result("remove_item", result)
            await _notify_order(result)
            return result

        return await _run_shielded("remove_item", params, _work)

    async def update_item(params: Any):
        args = _extract_args(params)
        if monitor is not None:
            monitor.record_tool_call("update_item", args)

        async def _work() -> dict:
            result = await asyncio.to_thread(
                router.update_item,
                order_item_id=_parse_uuid(args.get("order_item_id")),
                item_name=(args.get("item_name") or None),
                note=(args.get("note") or None),
                quantity=int(args["quantity"]) if args.get("quantity") else None,
                size=(args.get("size") or None),
            )
            if monitor is not None:
                monitor.record_tool_result("update_item", result)
            await _notify_order(result)
            return result

        return await _run_shielded("update_item", params, _work)

    async def get_summary(params: Any):
        if monitor is not None:
            monitor.record_tool_call("get_summary", {})

        async def _work() -> dict:
            result = await asyncio.to_thread(router.get_summary)
            if monitor is not None:
                monitor.record_tool_result("get_summary", result)
            await _notify_order(result)
            return result

        return await _run_shielded("get_summary", params, _work)

    async def checkout(params: Any):
        args = _extract_args(params)
        if monitor is not None:
            monitor.record_tool_call("checkout", args)

        async def _work() -> dict:
            result = await asyncio.to_thread(
                router.checkout,
                customer_name=args.get("customer_name") or None,
            )
            if monitor is not None:
                monitor.record_tool_result("checkout", result)
            await _notify_order(result)
            return result

        return await _run_shielded("checkout", params, _work)

    async def set_order_note(params: Any):
        args = _extract_args(params)
        if monitor is not None:
            monitor.record_tool_call("set_order_note", args)

        async def _work() -> dict:
            result = await asyncio.to_thread(
                router.set_order_note,
                note=args.get("note", ""),
            )
            if monitor is not None:
                monitor.record_tool_result("set_order_note", result)
            await _notify_order(result)
            return result

        return await _run_shielded("set_order_note", params, _work)

    async def set_fulfillment(params: Any):
        args = _extract_args(params)
        if monitor is not None:
            monitor.record_tool_call("set_fulfillment", args)

        async def _work() -> dict:
            result = await asyncio.to_thread(
                router.set_fulfillment,
                type=(args.get("type") or "").strip(),
                delivery_address=(args.get("delivery_address") or None),
            )
            if monitor is not None:
                monitor.record_tool_result("set_fulfillment", result)
            await _notify_order(result)
            return result

        return await _run_shielded("set_fulfillment", params, _work)

    return {
        "add_item": add_item,
        "update_item": update_item,
        "remove_item": remove_item,
        "get_summary": get_summary,
        "set_order_note": set_order_note,
        "set_fulfillment": set_fulfillment,
        "checkout": checkout,
    }


def _parse_uuid(value: Any):
    if not value:
        return None
    try:
        import uuid

        return uuid.UUID(str(value))
    except ValueError:
        return None

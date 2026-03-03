from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.voice.tool_router import VoiceToolContext, VoiceToolRouter

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
                "name": "get_summary",
                "description": "Get current order summary and totals.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "checkout",
                "description": "Finalize the order.",
                "parameters": {"type": "object", "properties": {}},
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


def create_voice_tool_handlers(context: VoiceToolContext) -> dict[str, Callable[[Any], Awaitable[Any]]]:
    """Create async tool handler functions for voice interactions, using the provided context to perform actions."""
    """Parameters:
    - context: The VoiceToolContext containing necessary information for handling tool calls (e.g. database access, user/store/order context)."""
    # The actual implementations of these handlers will depend on the VoiceToolRouter and the specific actions it supports.
    router = VoiceToolRouter(context)

    # Each handler extracts arguments from the params, calls the corresponding method on the router, and then invokes the result callback if it exists.
    async def add_item(params: Any):
        args = _extract_args(params)
        result = router.add_item(
            menu_item_id=_parse_uuid(args.get("menu_item_id")),
            item_name=(args.get("item_name") or None),
            quantity=int(args.get("quantity", 1) or 1),
        )
        callback = _result_callback(params)
        if callback:
            await callback(result)
        return result

    # The remove_item handler supports multiple ways to identify the item to remove (order_item_id, menu_item_id, or item_name) to provide flexibility in how the tool can be called.
    async def remove_item(params: Any):
        args = _extract_args(params)
        result = router.remove_item(
            order_item_id=_parse_uuid(args.get("order_item_id")),
            menu_item_id=_parse_uuid(args.get("menu_item_id")),
            item_name=(args.get("item_name") or None),
        )
        callback = _result_callback(params)
        if callback:
            await callback(result)
        return result

    # The get_summary and checkout handlers are simpler since they don't require parameters, but they still support result callbacks for asynchronous handling of the results.
    async def get_summary(params: Any):
        """Get current order summary and totals."""
        result = router.get_summary()
        callback = _result_callback(params)
        if callback:
            await callback(result)
        return result

    # The checkout handler would typically finalize the order and may involve additional steps such as confirming the order details with the user, handling payment, etc. 
    # For simplicity, this example just calls the checkout method on the router and supports a result callback.
    async def checkout(params: Any):
        result = router.checkout()
        callback = _result_callback(params)
        if callback:
            await callback(result)
        return result

    return {
        "add_item": add_item,
        "remove_item": remove_item,
        "get_summary": get_summary,
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

"""Helpers for converting tool schemas between Gemini and OpenAI formats."""

from __future__ import annotations

import json
from typing import Any, Dict, List


def gemini_tools_to_openai(gemini_schema: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert Gemini functionDeclarations schema to OpenAI tools format."""
    openai_tools: List[Dict[str, Any]] = []

    for group in gemini_schema or []:
        for function_declaration in group.get("functionDeclarations", []) or []:
            parameters = function_declaration.get("parameters") or {
                "type": "object",
                "properties": {},
            }
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": function_declaration.get("name", ""),
                        "description": function_declaration.get("description", ""),
                        "parameters": parameters,
                    },
                }
            )

    return openai_tools


def parse_tool_call_from_message(message: Any) -> List[Dict[str, Any]]:
    """Parse OpenAI tool calls from a message object."""
    tool_calls = getattr(message, "tool_calls", None)
    if not tool_calls:
        return []

    parsed_calls: List[Dict[str, Any]] = []
    for tool_call in tool_calls:
        parsed_calls.append(
            {
                "name": tool_call.function.name,
                "args": json.loads(tool_call.function.arguments),
            }
        )

    return parsed_calls
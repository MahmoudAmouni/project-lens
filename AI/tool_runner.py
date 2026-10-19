"""Run one tool call from the model. Every problem becomes an error message for the model, never a crash."""

import inspect
import json
from dataclasses import dataclass

from AI.llm_client import ToolCall
from AI.tools.registry import TOOLS
from AI.tools.tool_context import ToolContext, ToolError, ToolResult, to_json

REPEATED_CALL = (
    "You already made this exact call; its result is above. Try different words or another tool, "
    "or answer now with submit_answer."
)


@dataclass
class ToolOutcome:
    message: str  # JSON text sent back to the model
    step: str  # human text for "How I found this"
    result: ToolResult | None = None  # None when the call failed


def parse_arguments(call: ToolCall) -> dict:
    try:
        arguments = json.loads(call.arguments or "{}")
    except json.JSONDecodeError as error:
        raise ToolError(f"The arguments are not valid JSON ({error.msg}). Send a JSON object.") from error
    if arguments is None:
        return {}
    if not isinstance(arguments, dict):
        raise ToolError("The arguments must be a JSON object.")
    return arguments


def known_arguments(function, arguments: dict) -> dict:
    """Drop arguments the tool does not have (open models sometimes add extra ones)."""
    accepted = set(inspect.signature(function).parameters) - {"context"}
    return {name: value for name, value in arguments.items() if name in accepted}


def call_key(name: str, arguments: dict) -> tuple[str, str]:
    """Same tool + same arguments (ignoring case and order) = same key."""
    return name, json.dumps(arguments, sort_keys=True, ensure_ascii=False).lower()


def run_tool_call(call: ToolCall, context: ToolContext, seen_calls: set | None = None) -> ToolOutcome:
    """Run one call. `seen_calls` (per question) stops the model from repeating the exact same call."""
    if call.name not in TOOLS:
        names = ", ".join(TOOLS)
        return ToolOutcome(
            message=to_json({"error": f"There is no tool '{call.name}'. Tools: {names}"}),
            step=f"Asked for unknown tool '{call.name}'",
        )
    function, _ = TOOLS[call.name]
    try:
        arguments = known_arguments(function, parse_arguments(call))
        if seen_calls is not None and call.name != "submit_answer":
            if call_key(call.name, arguments) in seen_calls:
                raise ToolError(REPEATED_CALL)
            seen_calls.add(call_key(call.name, arguments))
        result = function(context, **arguments)
    except ToolError as error:
        return ToolOutcome(message=to_json({"error": str(error)}), step=f"{call.name}: {str(error)[:100]}")
    except TypeError as error:
        return ToolOutcome(
            message=to_json({"error": f"Wrong arguments: {error}"}), step=f"{call.name}: wrong arguments"
        )
    except Exception as error:  # a bug in a tool must not stop the answer
        return ToolOutcome(message=to_json({"error": f"The tool failed: {error}"}), step=f"{call.name} failed")
    return ToolOutcome(message="" if result.is_final else to_json(result.data), step=result.step, result=result)

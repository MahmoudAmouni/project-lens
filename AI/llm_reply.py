"""What one model call returns: the text and the tool calls, in one shape for every provider."""

from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON text, parsed by the agent
    extra_content: dict | None = None  # Gemini's thought signature, sent back with the call next round


@dataclass
class LLMReply:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""

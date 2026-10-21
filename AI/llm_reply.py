"""What one model call returns: the text and the tool calls, in one shape for every provider."""

import re
from dataclasses import dataclass, field

# Some models write "functions.submit_answer" or "default_api.query_table": the real name is the last part.
NAME_PREFIX = re.compile(r"^\s*(?:functions|default_api|tools?)\.")


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON text, parsed by the agent
    extra_content: dict | None = None  # Gemini's thought signature, sent back with the call next round

    def __post_init__(self) -> None:
        self.name = NAME_PREFIX.sub("", self.name or "").strip()


@dataclass
class LLMReply:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""

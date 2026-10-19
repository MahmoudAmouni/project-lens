"""A fake LLM that returns scripted replies, so the agent can be tested with no API cost."""

import json

from AI.errors import ToolCallFormatError
from AI.llm_client import LLMReply, ToolCall


def call(name: str, arguments: dict | str | None = None, call_id: str | None = None) -> ToolCall:
    text = arguments if isinstance(arguments, str) else json.dumps(arguments or {})
    return ToolCall(id=call_id or f"call_{name}", name=name, arguments=text)


def tool_reply(*calls: ToolCall) -> LLMReply:
    return LLMReply(content="", tool_calls=list(calls), model="fake-model")


def text_reply(text: str) -> LLMReply:
    return LLMReply(content=text, model="fake-model")


class FakeLLM:
    """Returns the scripted replies in order; repeats the last one when the script runs out.

    A script item can be an LLMReply or an exception to raise.
    """

    def __init__(self, script: list):
        self.script = list(script)
        self.requests: list[dict] = []
        self.preferred: str | None = None

    def prefer(self, model: str | None) -> None:
        self.preferred = model

    def complete(self, messages, tools, tool_choice="auto") -> LLMReply:
        self.requests.append({"messages": list(messages), "tools": tools, "tool_choice": tool_choice})
        item = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(item, Exception):
            raise item
        return item


def broken_call_error() -> ToolCallFormatError:
    return ToolCallFormatError('{"name": "query_table", "arguments": {document: BOQ}')

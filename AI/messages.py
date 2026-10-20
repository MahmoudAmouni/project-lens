"""Building the chat messages the agent sends to the model."""

from AI.llm_client import LLMReply
from AI.prompts import FORCE_ANSWER_PROMPT, SYSTEM_PROMPT

HISTORY_MESSAGES = 6
SUMMARY_EXCERPT_CHARS = 600


def build_messages(question: str, history: list[dict] | None, overview: str = "") -> list[dict]:
    """System prompt (with the list of loaded files) + the last chat messages + the new question."""
    recent = [
        {"role": item["role"], "content": str(item["content"])}
        for item in (history or [])[-HISTORY_MESSAGES:]
        if item.get("role") in ("user", "assistant") and item.get("content")
    ]
    system = SYSTEM_PROMPT + (f"\n\nLoaded files:\n{overview}" if overview else "")
    return [{"role": "system", "content": system}, *recent, {"role": "user", "content": question}]


def assistant_message(reply: LLMReply) -> dict:
    """The model's tool-call turn, in the format Groq expects back (plus Gemini's thought signature, if any)."""
    return {
        "role": "assistant",
        "content": reply.content or None,
        "tool_calls": [
            {"id": call.id, "type": "function", "function": {"name": call.name, "arguments": call.arguments},
             **({"extra_content": call.extra_content} if call.extra_content else {})}
            for call in reply.tool_calls
        ],
    }  # fmt: skip


def summary_messages(messages: list[dict], steps: list[str]) -> list[dict]:
    """A tiny request: the question, what was done, and short excerpts of the last tool results."""
    question = next(m["content"] for m in reversed(messages) if m["role"] == "user")
    excerpts = [m["content"][:SUMMARY_EXCERPT_CHARS] for m in messages if m["role"] == "tool"][-3:]
    notes = "\n".join(["Steps: " + "; ".join(steps), *excerpts])
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{question}\n\nWhat you found so far:\n{notes}\n\n{FORCE_ANSWER_PROMPT}"},
    ]

"""The agent loop: question -> model picks tools -> our code runs them -> repeat -> structured answer."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

from AI.context_budget import REQUEST_TOKEN_BUDGET, fit_to_budget, shorten_old_results
from AI.errors import RequestTooLargeError, ToolCallFormatError
from AI.llm_client import LLMReply
from AI.prompts import (
    BROKEN_TOOL_CALL_PROMPT,
    FORCE_ANSWER_PROMPT,
    SUBMIT_REMINDER_PROMPT,
    SYSTEM_PROMPT,
    TOO_MANY_SEARCHES_PROMPT,
)
from AI.question_notes import question_with_notes
from AI.router import Router
from AI.tool_runner import run_tool_call
from AI.tools.list_documents import document_overview
from AI.tools.registry import SUBMIT_ONLY_SCHEMAS, TOOL_SCHEMAS
from AI.tools.tool_context import DocumentLike, FinalAnswer, ToolContext

MAX_TOOL_ROUNDS = 10
HISTORY_MESSAGES = 6
logger = logging.getLogger("projectlens")
FORCE_SUBMIT = {"type": "function", "function": {"name": "submit_answer"}}
SUMMARY_EXCERPT_CHARS = 600
SEARCHES_BEFORE_REMINDER = 4  # then the model is told once to answer with what it has


@dataclass
class AgentAnswer:
    answer: str
    table: dict | None = None
    sources: list[dict] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    model: str = ""
    style: str = "en"  # the user's writing style: en | ar | ar-lb | arabizi

    @classmethod
    def from_final(cls, final: FinalAnswer, steps: list[str], model: str) -> "AgentAnswer":
        sources = [source.to_dict() for source in final.sources]
        return cls(answer=final.answer, table=final.table, sources=sources, steps=steps, model=model)

    def with_style(self, style: str) -> "AgentAnswer":
        self.style = style
        return self


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
    """The model's tool-call turn, in the format Groq expects back."""
    return {
        "role": "assistant",
        "content": reply.content or None,
        "tool_calls": [
            {"id": call.id, "type": "function", "function": {"name": call.name, "arguments": call.arguments}}
            for call in reply.tool_calls
        ],
    }


def summary_messages(messages: list[dict], steps: list[str]) -> list[dict]:
    """A tiny request: the question, what was done, and short excerpts of the last tool results."""
    question = next(m["content"] for m in reversed(messages) if m["role"] == "user")
    excerpts = [m["content"][:SUMMARY_EXCERPT_CHARS] for m in messages if m["role"] == "tool"][-3:]
    notes = "\n".join(["Steps: " + "; ".join(steps), *excerpts])
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{question}\n\nWhat you found so far:\n{notes}\n\n{FORCE_ANSWER_PROMPT}"},
    ]


class Agent:
    def __init__(self, llm, documents: Sequence[DocumentLike], vector_store=None, router: Router | None = None):
        self.llm = llm
        self.router = router or Router()  # Router() alone = the fail-safe style check, no AI call
        self.context = ToolContext(documents=documents, vector_store=vector_store)
        self.overview = document_overview(documents)
        self.seen_calls: set[tuple[str, str]] = set()
        self.search_reminder_sent = False

    def ask(self, question: str, history: list[dict] | None = None, ui_language: str | None = None) -> AgentAnswer:
        route = self.router.route(question, history, ui_language)
        return self.answer_from_documents(question_with_notes(question, route), history).with_style(route.style)

    def answer_from_documents(self, question: str, history: list[dict] | None) -> AgentAnswer:
        """The agent loop: tools until submit_answer, with guards and a round limit."""
        messages = build_messages(question, history, self.overview)
        steps: list[str] = []
        nudged = False
        self.seen_calls: set[tuple[str, str]] = set()  # to stop exact repeats of a tool call
        self.search_reminder_sent = False
        for _ in range(MAX_TOOL_ROUNDS):
            shorten_old_results(messages)
            fit_to_budget(messages, TOOL_SCHEMAS)
            try:
                reply = self.llm.complete(messages, TOOL_SCHEMAS)
            except RequestTooLargeError:
                fit_to_budget(messages, TOOL_SCHEMAS, REQUEST_TOKEN_BUDGET // 2)
                steps.append("Shortened long results to fit the limit")
                continue
            except ToolCallFormatError as error:
                logger.warning("Broken tool call: %s", error.details)
                messages.append({"role": "user", "content": BROKEN_TOOL_CALL_PROMPT.format(details=error.details)})
                steps.append("Fixed a broken tool call")
                continue
            if not reply.tool_calls:
                if reply.content.strip() and nudged:
                    return AgentAnswer(answer=reply.content.strip(), steps=steps, model=reply.model)
                if reply.content.strip():  # keep its text, but ask once for the structured answer
                    messages.append({"role": "assistant", "content": reply.content})
                messages.append({"role": "user", "content": SUBMIT_REMINDER_PROMPT})
                nudged = True
                continue
            answer = self.run_tools(reply, messages, steps)
            if answer:
                return answer
        return self.force_answer(messages, steps)

    def run_tools(self, reply: LLMReply, messages: list[dict], steps: list[str]) -> AgentAnswer | None:
        """Run every tool call of one reply. Returns the answer when submit_answer succeeded."""
        messages.append(assistant_message(reply))
        for call in reply.tool_calls:
            outcome = run_tool_call(call, self.context, self.seen_calls)
            steps.append(outcome.step)
            if outcome.result is not None and outcome.result.is_final:
                steps.pop()  # "Wrote the answer" is not a useful step to show
                return AgentAnswer.from_final(outcome.result.data["final_answer"], steps, reply.model)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": outcome.message})
        searches = sum(name == "search_documents" for name, _ in self.seen_calls)
        if searches >= SEARCHES_BEFORE_REMINDER and not self.search_reminder_sent:
            messages.append({"role": "user", "content": TOO_MANY_SEARCHES_PROMPT.format(count=searches)})
            self.search_reminder_sent = True
        return None

    def force_answer(self, messages: list[dict], steps: list[str]) -> AgentAnswer:
        """Round limit reached: ask for submit_answer only; if that fails, ask again with a tiny summary."""
        steps.append(f"Stopped after {MAX_TOOL_ROUNDS} rounds")
        short_summary = summary_messages(messages, steps)
        messages.append({"role": "user", "content": FORCE_ANSWER_PROMPT})
        fit_to_budget(messages, SUBMIT_ONLY_SCHEMAS)
        for attempt in (messages, short_summary):
            try:
                reply = self.llm.complete(attempt, SUBMIT_ONLY_SCHEMAS, tool_choice=FORCE_SUBMIT)
            except (ToolCallFormatError, RequestTooLargeError):
                continue
            answer = self.run_tools(reply, attempt, steps) if reply.tool_calls else None
            if answer:
                return answer
            if reply.content.strip():
                return AgentAnswer(answer=reply.content.strip(), steps=steps, model=reply.model)
        checked = "; ".join(step for step in steps[:-1]) or "nothing"
        return AgentAnswer(
            answer=f"I could not find a clear answer in the documents. I checked: {checked}.", steps=steps
        )

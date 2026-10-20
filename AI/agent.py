"""The agent loop: question -> model picks tools -> our code runs them -> repeat -> structured answer."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

from AI.context_budget import REQUEST_TOKEN_BUDGET, fit_to_budget, shorten_old_results
from AI.errors import QuestionStopped, RequestTooLargeError, ToolCallFormatError
from AI.guards.answer_check import check_answer, sources_from_history, sources_from_tool
from AI.guards.number_check import keep_tool_numbers
from AI.language.replies import example_questions, fixed_reply
from AI.llm_client import LLMReply
from AI.messages import assistant_message, build_messages, summary_messages
from AI.prompts import (
    BROKEN_TOOL_CALL_PROMPT,
    FORCE_ANSWER_PROMPT,
    SUBMIT_REMINDER_PROMPT,
    TOO_MANY_SEARCHES_PROMPT,
)
from AI.question_notes import question_with_notes
from AI.router import Router
from AI.tool_runner import run_tool_call
from AI.tools.list_documents import document_overview
from AI.tools.registry import SUBMIT_ONLY_SCHEMAS, TOOL_SCHEMAS
from AI.tools.tool_context import DocumentLike, FinalAnswer, ToolContext

MAX_TOOL_ROUNDS = 10
logger = logging.getLogger("projectlens")
FORCE_SUBMIT = {"type": "function", "function": {"name": "submit_answer"}}
SEARCHES_BEFORE_REMINDER = 4  # then the model is told once to answer with what it has


@dataclass
class AgentAnswer:
    answer: str
    table: dict | None = None
    sources: list[dict] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    model: str = ""
    style: str = "en"  # the user's writing style: en | ar | ar-lb | arabizi
    kind: str = "answer"  # answer | not_found | out_of_scope | greeting
    suggestions: list[str] = field(default_factory=list)  # example questions for greeting / out_of_scope

    @classmethod
    def from_final(cls, final: FinalAnswer, steps: list[str], model: str) -> "AgentAnswer":
        sources = [source.to_dict() for source in final.sources]
        return cls(answer=final.answer, table=final.table, sources=sources, steps=steps, model=model, kind=final.kind)

    def with_style(self, style: str) -> "AgentAnswer":
        self.style = style
        return self


class Agent:
    def __init__(
        self, llm, documents: Sequence[DocumentLike], vector_store=None, router: Router | None = None,
        scope_mode: str = "strict",
    ):  # fmt: skip
        self.llm = llm
        self.scope_mode = scope_mode  # "strict": off-topic questions get a fixed refusal; "relaxed": the agent tries
        self.consulted: list[dict] = []  # document locations the tools returned, for the answer check
        self.tool_texts: list[str] = []  # what the tools returned, for the number check
        self.should_stop = None  # set during one question by ask()
        self.router = router or Router()  # Router() alone = the fail-safe style check, no AI call
        self.context = ToolContext(documents=documents, vector_store=vector_store)
        self.overview = document_overview(documents)
        self.seen_calls: set[tuple[str, str]] = set()
        self.search_reminder_sent = False

    def ask(
        self, question: str, history: list[dict] | None = None, ui_language: str | None = None, should_stop=None
    ) -> AgentAnswer:
        """Answer one question. `should_stop()` returning True (the user pressed Stop) raises QuestionStopped."""
        self.set_stop_check(should_stop)
        try:
            return self.route_and_answer(question, history, ui_language)
        finally:
            self.set_stop_check(None)

    def set_stop_check(self, should_stop) -> None:
        self.should_stop = should_stop
        for llm in (self.llm, self.router.llm):
            if llm is not None:
                llm.should_stop = should_stop  # so long rate-limit waits end at once too

    def check_stop(self) -> None:
        if self.should_stop and self.should_stop():
            raise QuestionStopped("Stopped by the user.")

    def route_and_answer(self, question: str, history: list[dict] | None, ui_language: str | None) -> AgentAnswer:
        route = self.router.route(question, history, ui_language, self.overview)
        self.check_stop()
        if route.intent == "greeting":
            return self.fixed_answer("greeting", route.style, "Greeting: answered without searching")
        if route.intent == "injection" or (route.intent == "off_topic" and self.scope_mode == "strict"):
            return self.fixed_answer("out_of_scope", route.style, "Not about the documents: answered without searching")
        # A follow-up about the last answer may reuse that answer's sources (see the answer check).
        self.consulted = sources_from_history(history) if route.intent == "follow_up" else []
        self.tool_texts = []
        self.context.saved_tables.clear()  # an answer may only attach rows saved for this question (t1, t2...)
        answer = self.answer_from_documents(question_with_notes(question, route), history)
        known = [question, str(history or ""), *self.tool_texts]
        answer = keep_tool_numbers(answer, known, self.context, list(self.context.saved_tables), route.style)
        return check_answer(answer, self.consulted, fixed_reply("not_found", route.style)).with_style(route.style)

    def fixed_answer(self, kind: str, style: str, step: str) -> AgentAnswer:
        """A fixed reply (no AI writing) with example questions that fit the loaded files."""
        examples = example_questions(self.context.documents, style)
        answer = AgentAnswer(answer=fixed_reply(kind, style), steps=[step], kind=kind, suggestions=examples)
        return answer.with_style(style)

    def answer_from_documents(self, question: str, history: list[dict] | None) -> AgentAnswer:
        """The agent loop: tools until submit_answer, with guards and a round limit."""
        messages = build_messages(question, history, self.overview)
        steps: list[str] = []
        nudged = False
        self.seen_calls: set[tuple[str, str]] = set()  # to stop exact repeats of a tool call
        self.search_reminder_sent = False
        for _ in range(MAX_TOOL_ROUNDS):
            self.check_stop()
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
            self.tool_texts.append(outcome.message)
            if outcome.result is not None:
                self.consulted += sources_from_tool(call.name, outcome.result.data)
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

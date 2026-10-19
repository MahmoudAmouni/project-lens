"""The router: one small, fast AI call before the agent. It finds the user's writing style and intent, and
rewrites the question in clear English and Arabic so the documents can be searched in both languages.

Fail-safe: if the call fails or returns something unusable, a script check guesses the style and the question
goes to the agent as a document question. A router problem never blocks the user.
"""

import json
import logging
from dataclasses import dataclass, field

from AI.errors import QuestionStopped
from AI.guards.injection_check import looks_like_injection
from AI.language.style_detect import detect_style, looks_like_greeting
from AI.prompts import ROUTER_PROMPT

logger = logging.getLogger("projectlens")

STYLES = {"en", "ar", "ar-lb", "arabizi"}
ARABIC_SCRIPT = {"ar", "ar-lb"}
INTENTS = {"document_question", "follow_up", "greeting", "off_topic", "injection"}
HISTORY_TURNS = 4
MAX_TERMS = 8
MAX_OVERVIEW_CHARS = 800  # the list of loaded files, so the router knows what the documents cover


@dataclass
class Route:
    style: str  # en | ar | ar-lb | arabizi
    intent: str  # document_question | follow_up | greeting | off_topic | injection
    question_en: str = ""
    question_ar: str = ""
    search_terms: list[str] = field(default_factory=list)
    by_model: bool = False  # False = the fail-safe guess was used

    @property
    def needs_documents(self) -> bool:
        return self.intent in ("document_question", "follow_up")


def fallback_route(question: str, ui_language: str | None) -> Route:
    """No AI: the style from the letters used; an injection, a plain greeting, or else a document question."""
    if looks_like_injection(question):
        intent = "injection"
    elif looks_like_greeting(question):
        intent = "greeting"
    else:
        intent = "document_question"
    return Route(style=detect_style(question, ui_language), intent=intent)


def with_plain_checks(route: Route, fallback: Route) -> Route:
    """An injection or a plain greeting found without AI wins over the model's intent."""
    if fallback.intent in ("injection", "greeting"):
        route.intent = fallback.intent
    return route


def checked_style(model_style: object, guessed: str) -> str:
    """Trust the model inside one script; if it names the wrong script (Arabic vs Latin letters), keep the guess.

    Lebanese words (شو، يلي، أكتر) are a sure sign: the model calling them "ar" does not win over "ar-lb".
    """
    if model_style not in STYLES:
        return guessed
    if (model_style in ARABIC_SCRIPT) != (guessed in ARABIC_SCRIPT) or (guessed, model_style) == ("ar-lb", "ar"):
        return guessed
    return str(model_style)


def parse_route(data: dict, fallback: Route) -> Route:
    terms = data.get("search_terms")
    return Route(
        style=checked_style(data.get("style"), fallback.style),
        intent=data.get("intent") if data.get("intent") in INTENTS else "document_question",
        question_en=str(data.get("question_en") or "").strip(),
        question_ar=str(data.get("question_ar") or "").strip(),
        search_terms=[str(term) for term in terms][:MAX_TERMS] if isinstance(terms, list) else [],
        by_model=True,
    )


def router_message(question: str, history: list[dict], ui_language: str | None, overview: str) -> str:
    recent = [
        {"role": item.get("role"), "text": str(item.get("content", ""))[:300]} for item in history[-HISTORY_TURNS:]
    ]
    data = {"message": question, "screen_language": ui_language or "en", "recent_chat": recent}
    if overview:
        data["loaded_files"] = overview[:MAX_OVERVIEW_CHARS]
    return json.dumps(data, ensure_ascii=False)


class Router:
    def __init__(self, llm=None):
        self.llm = llm  # an LLMClient with complete_json(); None = always use the fail-safe

    def route(
        self, question: str, history: list[dict] | None = None, ui_language: str | None = None, overview: str = ""
    ) -> Route:
        fallback = fallback_route(question, ui_language)
        if self.llm is None or fallback.intent in ("greeting", "injection"):
            return fallback  # plain greetings and injections are certain without AI: instant, and no tokens used
        messages = [
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user", "content": router_message(question, history or [], ui_language, overview)},
        ]
        try:
            route = with_plain_checks(parse_route(self.llm.complete_json(messages), fallback), fallback)
            logger.info("Router: %s, %s", route.intent, route.style)
            return route
        except QuestionStopped:
            raise  # the user pressed Stop: end here, do not fall back
        except Exception as error:  # the router must never block a question
            logger.warning("Router failed, using the fail-safe: %s", error)
            return fallback

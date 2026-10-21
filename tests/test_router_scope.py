"""A router that wrongly says "off_topic" cannot refuse a question that uses the documents' words (no API calls)."""

from pathlib import Path

import pytest

from AI.agent import Agent
from AI.guards.scope_check import document_words, mentions_documents, words_of
from AI.router import Router
from Server.config import load_settings
from Server.ingestion.folder_loader import load_folder
from tests.fake_llm import FakeLLM, call, tool_reply

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"


@pytest.fixture(scope="module")
def documents():
    return load_folder(SAMPLE_DIR).documents


class OffTopicRouterModel:
    """A weak router model: calls everything off-topic, but still rewrites the question in English."""

    def __init__(self, question_en: str = ""):
        self.question_en = question_en

    def complete_json(self, messages):
        return {"style": "en", "intent": "off_topic", "question_en": self.question_en, "question_ar": ""}


def agent_with_off_topic_router(documents, question_en: str = "") -> tuple[Agent, FakeLLM]:
    submit = call("submit_answer", {"answer": "Not in the documents.", "kind": "not_found", "sources": []})
    llm = FakeLLM([tool_reply(submit)])
    return Agent(llm, documents, router=Router(OffTopicRouterModel(question_en))), llm


@pytest.mark.parametrize(
    "question",
    ["shu l items bel civil BOQ yalli aktar men malyon riyal?", "What percentage of the BOQ total is section A?",
     "List the BOQ items with a unit rate above 500"],
)  # fmt: skip
def test_a_question_with_document_words_reaches_the_agent(documents, question):
    agent, llm = agent_with_off_topic_router(documents)
    assert agent.ask(question).kind != "out_of_scope"
    assert llm.requests  # the agent ran


def test_an_arabic_question_matches_through_the_router_english_rewrite(documents):
    agent, llm = agent_with_off_topic_router(documents, "What is the total amount of the BOQ?")
    assert agent.ask("قديش المبلغ الإجمالي لجدول الكميات؟").kind != "out_of_scope"


@pytest.mark.parametrize(
    "question",
    ["Write me a poem about concrete", "What's the weather in Beirut?", "Who will win the World Cup?",
     "ktebli code python", "What is the current market price of rebar in Riyadh?"],
)  # fmt: skip
def test_off_topic_questions_are_still_refused(documents, question):
    agent, llm = agent_with_off_topic_router(documents)
    assert agent.ask(question).kind == "out_of_scope"
    assert llm.requests == []


def test_vocabulary_comes_from_names_columns_and_glossary(documents):
    vocabulary = document_words(documents)
    assert {"boq", "phase", "rate", "equipment", "malyon", "retention"} <= vocabulary
    assert not mentions_documents("one boq", vocabulary)  # one shared word is not enough


def test_arabic_prefixes_are_removed():
    assert {"مقاول", "عقد", "اعمده"} <= words_of("والمقاول بالعقد للأعمدة")


def test_the_weak_router_model_is_no_longer_a_default(monkeypatch):
    monkeypatch.delenv("ROUTER_MODEL", raising=False)
    monkeypatch.setattr("Server.config.load_dotenv", lambda *args, **kwargs: None)
    assert "allam" not in load_settings().router_model

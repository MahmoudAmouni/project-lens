"""A backup model that refuses a request, or Groq names that do not exist, never end the answer (no API calls)."""

import groq
import pytest

from AI.errors import AIUnavailableError
from AI.llm_client import LLMClient
from AI.usage_tracker import UsageTracker
from tests.test_gemini_model import QUESTION, fake_client
from tests.test_llm_client import api_error


def client_with_backups(tmp_path) -> LLMClient:
    return LLMClient(
        api_key="test-key", model="groq-a", usage=UsageTracker(str(tmp_path / "usage.json")),
        gemini_api_key="test-gemini-key", gemini_model="gemini-3.5-flash",
        openrouter_api_key="test-openrouter-key", openrouter_model="nvidia/nemotron-3-ultra-550b-a55b:free",
    )  # fmt: skip


def test_a_backup_refusing_a_request_hands_over_to_the_next_backup(tmp_path):
    llm = client_with_backups(tmp_path)
    llm.prefer("gemini-3.5-flash")
    llm.client, groq_calls = fake_client()
    llm.gemini_client, gemini_calls = fake_client()

    def refuses(**options):
        gemini_calls.sent.append(options)
        raise api_error(groq.BadRequestError, 400, {"error": {"message": "tool_choice is not supported"}})

    gemini_calls.create = refuses
    reply = llm.complete(QUESTION, [])
    assert reply.model == "groq-a" and len(gemini_calls.sent) == 1  # Gemini refused, Groq answered


def test_a_groq_refusal_still_reports_the_error(tmp_path):
    llm = client_with_backups(tmp_path)
    llm.client, groq_calls = fake_client()

    def refuses(**options):
        raise api_error(groq.BadRequestError, 400, {"error": {"message": "context too long"}})

    groq_calls.create = refuses
    with pytest.raises(AIUnavailableError, match="refused the request"):  # the main model's refusal is shown
        llm.complete(QUESTION, [])


def test_unknown_groq_names_fall_back_to_the_backups(tmp_path):
    llm = client_with_backups(tmp_path)
    llm.client, groq_calls = fake_client()
    llm.gemini_client, _ = fake_client()

    def removed(**options):
        raise api_error(groq.NotFoundError, 404, {"error": {"message": "model does not exist"}})

    groq_calls.create = removed
    assert llm.complete(QUESTION, []).model == "gemini-3.5-flash"

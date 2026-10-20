"""Gemini 3 thought signatures go back to Gemini, never to Groq; a refused request is a clear error (no API)."""

from types import SimpleNamespace

import groq
import httpx
import pytest

from AI.errors import AIUnavailableError
from AI.gemini_client import PLACEHOLDER_SIGNATURE, messages_for_model
from AI.llm_client import LLMClient, LLMReply, ToolCall
from AI.messages import assistant_message

SIGNED = {"google": {"thought_signature": "real-signature"}}


def tool_turn(*calls: ToolCall) -> list[dict]:
    return [{"role": "user", "content": "hi"}, assistant_message(LLMReply(content="", tool_calls=list(calls)))]


def test_a_gemini_signature_is_kept_in_the_assistant_turn():
    turn = tool_turn(ToolCall("c1", "list_documents", "{}", SIGNED))[1]
    assert turn["tool_calls"][0]["extra_content"] == SIGNED
    assert "extra_content" not in tool_turn(ToolCall("c2", "list_documents", "{}"))[1]["tool_calls"][0]


def test_gemini_gets_signatures_back_and_a_placeholder_for_groq_calls():
    messages = tool_turn(ToolCall("c1", "list_documents", "{}", SIGNED), ToolCall("c2", "search_documents", "{}"))
    calls = messages_for_model(messages, gemini=True)[1]["tool_calls"]
    assert [call["extra_content"] for call in calls] == [SIGNED, PLACEHOLDER_SIGNATURE]


def test_groq_never_sees_the_gemini_field():
    messages = tool_turn(ToolCall("c1", "list_documents", "{}", SIGNED))
    assert "extra_content" not in messages_for_model(messages, gemini=False)[1]["tool_calls"][0]
    assert "extra_content" in messages[1]["tool_calls"][0]  # the chat itself is not changed


def test_a_refused_request_becomes_a_clear_error_not_a_crash():
    llm = LLMClient(api_key="test-key", model="groq-a")
    response = httpx.Response(400, request=httpx.Request("POST", "https://x.test"))

    def refuse(**options):
        raise groq.BadRequestError("Function call is missing a thought_signature", response=response, body=None)

    completions = SimpleNamespace(create=refuse)
    completions.with_raw_response = completions
    llm.client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    with pytest.raises(AIUnavailableError, match="groq-a refused the request"):
        llm.complete([{"role": "user", "content": "hi"}], [])

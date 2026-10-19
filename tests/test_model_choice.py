"""Picking the AI model and showing how much of its free limit is left (no API calls)."""

import time

from fastapi.testclient import TestClient

from AI.llm_client import LLMClient
from AI.usage_tracker import DAY_SECONDS, UsageTracker
from Server.main import create_app
from tests.fake_llm import FakeLLM, call, tool_reply
from tests.test_api import SAMPLE_DIR

DAILY_LIMIT_ERROR = (
    "Rate limit reached for model `m` on tokens per day (TPD): Limit 200000, Used 199326, Requested 2594."
)
HEADERS = {"x-ratelimit-remaining-requests": "998", "x-ratelimit-limit-requests": "1000",
           "x-ratelimit-remaining-tokens": "7900"}  # fmt: skip


def test_tokens_of_every_reply_are_counted(tmp_path):
    usage = UsageTracker(str(tmp_path / "usage.json"))
    usage.record_reply("m", 1500, HEADERS)
    usage.record_reply("m", 500, HEADERS)
    left = usage.snapshot("m")
    assert left["tokens_used_today"] == 2000 and left["tokens_left_today"] == 198_000
    assert left["requests_left_today"] == 998 and left["tokens_left_this_minute"] == 7900


def test_groq_daily_limit_error_gives_the_exact_numbers(tmp_path):
    usage = UsageTracker(str(tmp_path / "usage.json"))
    usage.record_reply("m", 1000, HEADERS)
    usage.record_limit("m", DAILY_LIMIT_ERROR, wait_seconds=600)
    left = usage.snapshot("m")
    assert left["tokens_used_today"] == 199_326 and left["tokens_left_today"] == 674
    assert 590 <= left["limited_for_seconds"] <= 600


def test_usage_survives_a_restart_and_old_use_expires(tmp_path, monkeypatch):
    path = str(tmp_path / "usage.json")
    UsageTracker(path).record_reply("m", 3000, HEADERS)
    assert UsageTracker(path).snapshot("m")["tokens_used_today"] == 3000
    later = time.time() + DAY_SECONDS + 1
    monkeypatch.setattr("AI.usage_tracker.time.time", lambda: later)
    assert UsageTracker(path).snapshot("m")["tokens_used_today"] == 0


def test_broken_usage_file_starts_the_count_again(tmp_path):
    path = tmp_path / "usage.json"
    path.write_text("not json")
    assert UsageTracker(str(path)).snapshot("m")["tokens_used_today"] == 0


def test_picked_model_goes_first_and_the_others_stay_as_backups():
    client = LLMClient(api_key="test-key", model="a", fallback_model="b,c")
    client.prefer("c")
    assert client.models == ["c", "a", "b"]
    client.prefer("not-a-model")
    assert client.models == ["c", "a", "b"]


def test_models_endpoint_lists_the_models_from_env(tmp_path):
    app = create_app(load_docs_folder=False)
    state = app.state.lens
    state.usage = UsageTracker(str(tmp_path / "usage.json"))
    state.llm = LLMClient(api_key="test-key", model="a", fallback_model="b", usage=state.usage)
    state.usage.record_reply("b", 4000, HEADERS)
    with TestClient(app) as client:
        models = client.get("/api/models").json()["models"]
    assert [model["name"] for model in models] == ["a", "b"]
    assert models[1]["tokens_left_today"] == 196_000


def test_chat_uses_the_picked_model():
    app = create_app(load_docs_folder=False)
    state = app.state.lens
    state.use_search = False
    fake = FakeLLM([tool_reply(call("submit_answer", {"answer": "Hi", "kind": "not_found"}))])
    with TestClient(app) as client:
        client.post("/api/documents/load", json={"folder_path": str(SAMPLE_DIR)})
        state.llm = fake
        client.post("/api/chat", json={"question": "What is the contract value?", "model": "b"})
    assert fake.preferred == "b"

"""Google's real used-up message ("limit: 20 ... retry in 23h1m31s") is a DAILY limit: wait hours, not seconds."""

import groq
import httpx
import pytest

from AI.llm_helpers import duration_seconds, is_daily_limit, retry_after_seconds
from AI.usage_tracker import UsageTracker

USED_UP = (
    "You exceeded your current quota. Quota exceeded for metric: "
    "generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.6-flash\n"
    "Please retry in 23h1m31.016537169s."
)
PER_MINUTE = "Resource exhausted. Please retry in 23.5s."


def rate_limit(message: str) -> groq.RateLimitError:
    response = httpx.Response(429, request=httpx.Request("POST", "https://x.test"))
    return groq.RateLimitError(message, response=response, body=None)


@pytest.mark.parametrize(("text", "seconds"), [("23.5s", 23.5), ("1m30s", 90), ("23h1m31s", 82891), ("2h", 7200)])
def test_durations_in_hours_minutes_and_seconds(text, seconds):
    assert duration_seconds(text) == seconds


def test_a_used_up_free_tier_is_a_daily_limit_of_hours():
    error = rate_limit(USED_UP)
    assert retry_after_seconds(error) > 82_000 and is_daily_limit(error)


def test_a_per_minute_limit_is_not_daily():
    error = rate_limit(PER_MINUTE)
    assert retry_after_seconds(error) == 24.0 and not is_daily_limit(error)


def test_the_counter_learns_google_limit_and_shows_none_left():
    usage = UsageTracker(None)
    usage.count_requests("gemini-3.5-flash", 250)
    usage.record_limit("gemini-3.5-flash", USED_UP, 82891)
    status = usage.snapshot("gemini-3.5-flash")
    assert (status["daily_request_limit"], status["requests_left_today"]) == (20, 0)


def test_an_old_saved_bigger_limit_never_hides_the_setting():
    usage = UsageTracker(None)
    usage.count_requests("gemini-3.5-flash", 250)
    usage.count_requests("gemini-3.5-flash", 20)  # the new setting after a restart
    assert usage.snapshot("gemini-3.5-flash")["daily_request_limit"] == 20

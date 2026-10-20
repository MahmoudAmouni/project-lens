"""The one place that talks to the AI models: Groq, and Google Gemini when its key is set.

Groq's free tier allows about 8,000 tokens per minute per model. On a rate limit we switch to the
other model (it has its own limit); when both are limited we wait as long as Groq asks, then retry.
The user may pick which model goes first; every reply's token use is counted (see usage_tracker.py).
Gemini is used when the user picks it, and as the last resort while every Groq model is rate limited.
"""

import json
import time
from dataclasses import dataclass, field

import groq

from AI.errors import AIRateLimitedError, AIUnavailableError, QuestionStopped, RequestTooLargeError, ToolCallFormatError
from AI.gemini_client import extra_content_of, is_gemini, make_gemini_client, messages_for_model
from AI.llm_helpers import (
    DEFAULT_WAIT_SECONDS,
    key_name,
    model_names,
    rate_limit_message,
    retry_after_seconds,
    tool_use_failure,
)
from AI.usage_tracker import UsageTracker

MAX_TRIES = 3  # for errors other than rate limits (timeouts, Groq server errors)
MAX_TOTAL_WAIT_SECONDS = 90.0  # rate limits are normal on the free tier: wait up to this long in total
REQUEST_TIMEOUT_SECONDS = 60.0
PAUSE_STEP_SECONDS = 0.25


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON text, parsed by the agent
    extra_content: dict | None = None  # Gemini's thought signature, sent back with the call next round


@dataclass
class LLMReply:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""


class LLMClient:
    """Sends chat messages + tool schemas to Groq and returns the reply."""

    def __init__(
        self,
        api_key: str,
        model: str,
        fallback_model: str | None = None,
        reasoning_effort: str = "medium",
        max_wait_seconds: float = MAX_TOTAL_WAIT_SECONDS,
        usage: UsageTracker | None = None,
        gemini_api_key: str = "",
        gemini_model: str = "",
        gemini_daily_requests: int = 0,
    ):
        """`fallback_model` and `gemini_model` may list several models: "openai/gpt-oss-20b,qwen/qwen3.8-27b"."""
        if not api_key:
            raise AIUnavailableError("Add your GROQ_API_KEY to the .env file, then restart.")
        self.client = groq.Groq(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=0)
        self.groq_models = list(dict.fromkeys([model, *model_names(fallback_model)]))  # each has its own limits
        self.gemini_models = model_names(gemini_model) if gemini_api_key else []
        self.gemini_client = make_gemini_client(gemini_api_key, REQUEST_TIMEOUT_SECONDS) if self.gemini_models else None
        self.models = list(self.groq_models)  # the order they are tried in; Gemini joins only when picked
        self.configured_models = [*self.groq_models, *self.gemini_models]  # the choices shown to the user
        self.usage = usage or UsageTracker()
        for name in self.gemini_models:
            self.usage.count_requests(name, gemini_daily_requests)
        self.reasoning_effort = reasoning_effort
        self.limited_until: dict[str, float] = {}  # model -> time its rate limit resets
        self.daily_limit_hit = False
        self.max_wait_seconds = max_wait_seconds  # small for the router: it falls back instead of waiting
        self.should_stop = None  # set per question: a function that returns True once the user pressed Stop

    @property
    def model(self) -> str:
        return self.models[0] if self.models else ""

    def prefer(self, model: str | None) -> None:
        """Try the model the user picked first; the Groq models stay as backups. Unknown names are ignored."""
        if model in self.configured_models:
            self.models = [model, *[name for name in self.groq_models if name != model]]

    def check(self, model: str) -> None:
        """A tiny call, only to read the limits Groq sends back for this model. Gemini sends none: skipped."""
        if is_gemini(model):
            return
        try:
            self._call(model, [{"role": "user", "content": "hi"}], [], "auto", max_tokens=1)
        except groq.RateLimitError as error:
            self.usage.record_limit(model, str(error), retry_after_seconds(error))
        except groq.GroqError:
            pass  # a removed model or a network problem: the screen just shows the last known numbers

    def pick_model(self) -> tuple[str, float]:
        """The first model that is free, else the one whose rate limit resets first, and how long to wait for it.
        Gemini comes last: it is used when every Groq model is limited, so the app keeps answering."""
        now = time.monotonic()
        candidates = self.models + [name for name in self.gemini_models if name not in self.models]
        model = min(candidates, key=lambda m: max(0.0, self.limited_until.get(m, 0) - now))  # ties: first in order
        return model, max(0.0, self.limited_until.get(model, 0) - now)

    def complete(
        self, messages: list[dict], tools: list[dict], tool_choice: str | dict = "auto", json_mode: bool = False
    ) -> LLMReply:
        """One model call, with retries, waits for rate limits and the backup model."""
        deadline = time.monotonic() + self.max_wait_seconds
        attempt = 0
        while attempt < MAX_TRIES:
            if not self.models:
                raise AIUnavailableError("None of the models in .env (MODEL, FALLBACK_MODEL) exist on Groq.")
            model, wait = self.pick_model()
            if time.monotonic() + wait > deadline:
                raise AIRateLimitedError(rate_limit_message(self.daily_limit_hit, wait))
            self.pause(wait)
            attempt += 1
            try:
                return self._call(model, messages, tools, tool_choice, json_mode)
            except groq.RateLimitError as error:
                self.limited_until[model] = time.monotonic() + retry_after_seconds(error)
                self.usage.record_limit(model, str(error), retry_after_seconds(error))
                self.daily_limit_hit = "per day" in str(error) or "PerDay" in str(error)
                attempt -= 1  # a rate limit is not a failure; the deadline above limits the waiting
            except groq.NotFoundError:
                self.models = [name for name in self.models if name != model]  # removed by the provider: skip it
                self.gemini_models = [name for name in self.gemini_models if name != model]
            except groq.AuthenticationError as error:
                raise AIUnavailableError(f"The {key_name(model)} in .env is not valid.") from error
            except groq.BadRequestError as error:
                if "API key not valid" in str(error):  # Gemini answers 400, not 401, for a wrong key
                    raise AIUnavailableError(f"The {key_name(model)} in .env is not valid.") from error
                failed = tool_use_failure(error)
                if failed is not None:
                    raise ToolCallFormatError(failed) from error
                raise AIUnavailableError(f"The model {model} refused the request: {str(error)[:200]}") from error
            except groq.APIStatusError as error:
                if error.status_code == 413:
                    raise RequestTooLargeError("The request is larger than Groq's free tier allows.") from error
                if attempt == MAX_TRIES:
                    raise AIUnavailableError("Groq is having problems right now. Try again soon.") from error
                self.pause(DEFAULT_WAIT_SECONDS)
            except (groq.APITimeoutError, groq.APIConnectionError) as error:
                if attempt == MAX_TRIES:
                    raise AIUnavailableError("Groq could not be reached. Check your internet connection.") from error
                self.pause(DEFAULT_WAIT_SECONDS)
        raise AIRateLimitedError("Groq's free rate limit is reached. Wait a minute and try again.")

    def pause(self, seconds: float) -> None:
        """Wait in small steps, so Stop also ends a long rate-limit wait. Raises QuestionStopped."""
        end = time.monotonic() + seconds
        while True:
            if self.should_stop and self.should_stop():
                raise QuestionStopped("Stopped by the user.")
            left = end - time.monotonic()
            if left <= 0:
                return
            time.sleep(min(PAUSE_STEP_SECONDS, left))

    def complete_json(self, messages: list[dict]) -> dict:
        """A reply that must be one JSON object (no tools). Raises ValueError when it is not."""
        reply = self.complete(messages, tools=[], json_mode=True)
        data = json.loads(reply.content or "{}")
        if not isinstance(data, dict):
            raise ValueError("The model did not return a JSON object.")
        return data

    def _call(
        self, model: str, messages: list[dict], tools: list[dict], tool_choice: str | dict, json_mode: bool = False,
        max_tokens: int | None = None,
    ) -> LLMReply:  # fmt: skip
        options: dict = {"tools": tools, "tool_choice": tool_choice} if tools else {}
        if json_mode:
            options["response_format"] = {"type": "json_object"}
        client = self.gemini_client if model in self.gemini_models else self.client
        if is_gemini(model) and isinstance(tool_choice, dict) and tools:
            options["tool_choice"] = "required"  # Gemini wants "required" to force the one tool given
        if model.startswith("openai/gpt-oss"):
            options["reasoning_effort"] = self.reasoning_effort
        elif model.startswith("qwen/"):
            options["reasoning_format"] = "hidden"  # keep <think> text out of the answer
        if max_tokens:
            options["max_tokens"] = max_tokens
        messages = messages_for_model(messages, gemini=client is self.gemini_client)
        raw = client.chat.completions.with_raw_response.create(
            model=model, messages=messages, temperature=0 if json_mode else 0.1, **options
        )
        response = raw.parse()
        self.usage.record_reply(model, response.usage.total_tokens if response.usage else 0, raw.headers)
        message = response.choices[0].message
        tool_calls = [
            ToolCall(call.id, call.function.name, call.function.arguments or "{}", extra_content_of(call))
            for call in message.tool_calls or []
        ]
        return LLMReply(content=message.content or "", tool_calls=tool_calls, model=model)

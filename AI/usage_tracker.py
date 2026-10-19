"""How much of each model's free Groq limit is left: tokens today, requests today, tokens this minute.

Groq sends "requests left today" and "tokens left this minute" with every reply, but not "tokens left today".
So we count the tokens of every reply (a rolling 24 hours, like Groq), and when Groq's daily-limit error
tells us the exact "Used" and "Limit", we take those numbers instead. Saved to a file, so a restart keeps them.
"""

import json
import logging
import re
import threading
import time
from pathlib import Path

DAY_SECONDS = 24 * 60 * 60
DEFAULT_DAILY_TOKEN_LIMIT = 200_000  # Groq's free tier for the gpt-oss and qwen models; corrected by its errors
DAILY_LIMIT_PATTERN = re.compile(r"tokens per day \(TPD\): Limit (\d+), Used (\d+)")
logger = logging.getLogger("projectlens")


class UsageTracker:
    def __init__(self, path: str | None = None):
        self.path = Path(path) if path else None
        self.lock = threading.Lock()
        self.models: dict[str, dict] = self.read()

    def read(self) -> dict[str, dict]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8")) if self.path and self.path.exists() else {}
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}  # a broken file only means the counts start again

    def save(self) -> None:
        if not self.path:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.models), encoding="utf-8")
        except OSError:
            logger.warning("Could not save the token usage to %s", self.path)

    def entry(self, model: str) -> dict:
        entry = self.models.setdefault(model, {"spent": [], "daily_limit": DEFAULT_DAILY_TOKEN_LIMIT})
        cutoff = time.time() - DAY_SECONDS
        entry["spent"] = [item for item in entry["spent"] if item[0] > cutoff]  # [time, tokens]
        return entry

    def record_reply(self, model: str, tokens: int, headers) -> None:
        """After a successful call: its tokens, and the limits Groq sent back in the headers."""
        with self.lock:
            entry = self.entry(model)
            if tokens:
                entry["spent"].append([time.time(), int(tokens)])
            for key, header in (("requests_left", "x-ratelimit-remaining-requests"),
                                ("requests_limit", "x-ratelimit-limit-requests"),
                                ("minute_tokens_left", "x-ratelimit-remaining-tokens")):  # fmt: skip
                value = headers.get(header) if headers is not None else None
                if value is not None and str(value).isdigit():
                    entry[key] = int(value)
            entry["checked_at"] = time.time()
            self.save()

    def record_limit(self, model: str, message: str, wait_seconds: float) -> None:
        """After a rate-limit error: when it ends, and the exact daily numbers if Groq gave them."""
        with self.lock:
            entry = self.entry(model)
            entry["limited_until"] = time.time() + wait_seconds
            found = DAILY_LIMIT_PATTERN.search(message)
            if found:
                limit, used = int(found.group(1)), int(found.group(2))
                entry["daily_limit"] = limit
                entry["spent"] = [[time.time(), used]]  # Groq's own count replaces ours
            self.save()

    def snapshot(self, model: str) -> dict:
        """What is left for one model, for the screen."""
        with self.lock:
            entry = self.entry(model)
            used = sum(tokens for _, tokens in entry["spent"])
            limit = entry.get("daily_limit", DEFAULT_DAILY_TOKEN_LIMIT)
            wait = max(0.0, entry.get("limited_until", 0) - time.time())
            return {
                "name": model,
                "tokens_used_today": used,
                "daily_token_limit": limit,
                "tokens_left_today": max(0, limit - used),
                "requests_left_today": entry.get("requests_left"),
                "daily_request_limit": entry.get("requests_limit"),
                "tokens_left_this_minute": entry.get("minute_tokens_left"),
                "limited_for_seconds": round(wait),
            }

"""Errors the AI folder raises. The Server turns them into clear API errors."""


class AIUnavailableError(Exception):
    """The API key is missing or wrong, or Groq cannot be reached."""


class AIRateLimitedError(Exception):
    """Groq's rate limit was hit on both the main and the backup model."""


class ToolCallFormatError(Exception):
    """The model wrote a tool call Groq could not parse (bad JSON or schema)."""

    def __init__(self, details: str):
        super().__init__(details)
        self.details = details


class RequestTooLargeError(Exception):
    """One request is bigger than the per-minute token limit; the agent shrinks old results and retries."""

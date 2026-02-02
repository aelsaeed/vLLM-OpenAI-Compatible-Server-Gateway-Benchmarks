from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SafetyResult:
    allowed: bool
    reason: str | None = None
    adjusted_max_tokens: int | None = None


class SafetyChecker:
    def __init__(self, max_tokens_cap: int, denylist_words: list[str]) -> None:
        self._max_tokens_cap = max_tokens_cap
        self._denylist = {word.lower() for word in denylist_words}

    def check(self, payload: dict) -> SafetyResult:
        messages = payload.get("messages", [])
        for message in messages:
            content = str(message.get("content", "")).lower()
            if any(word in content for word in self._denylist):
                return SafetyResult(allowed=False, reason="denylist")
        max_tokens = payload.get("max_tokens")
        if isinstance(max_tokens, int) and max_tokens > self._max_tokens_cap:
            return SafetyResult(
                allowed=True,
                reason="max_tokens_capped",
                adjusted_max_tokens=self._max_tokens_cap,
            )
        return SafetyResult(allowed=True)

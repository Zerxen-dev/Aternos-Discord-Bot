"""Security hardening: input sanitization, rate limiting, and permission verification."""

from __future__ import annotations

import collections
import re
import time
from typing import Optional


class SecurityError(ValueError):
    """Raised when an input fails security validation."""


class CommandRateLimiter:
    """Sliding-window rate limiter per user/guild to prevent command abuse."""

    def __init__(self, max_calls: int = 5, window_seconds: float = 60.0):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._history: dict[int, collections.deque[float]] = collections.defaultdict(collections.deque)

    def is_rate_limited(self, user_id: int) -> tuple[bool, float]:
        """Check if user_id exceeded rate limit.

        Returns (is_limited, retry_after_seconds).
        """
        now = time.monotonic()
        q = self._history[user_id]

        # Evict timestamps outside sliding window
        while q and q[0] <= now - self.window_seconds:
            q.popleft()

        if len(q) >= self.max_calls:
            retry_after = round(self.window_seconds - (now - q[0]), 1)
            return True, max(0.5, retry_after)

        q.append(now)
        return False, 0.0


def sanitize_console_command(cmd: str) -> str:
    """Sanitize console commands before dispatching to Minecraft console.

    Removes forbidden control characters, strips dangerous escape sequences,
    and validates maximum length.
    """
    if not cmd or not cmd.strip():
        raise SecurityError("Command cannot be empty.")

    cleaned = cmd.strip()

    # Disallow control characters (\x00-\x1f, \x7f)
    if any(ord(c) < 32 and c not in ('\t', ' ') for c in cleaned):
        raise SecurityError("Command contains forbidden control characters.")

    # Remove leading slashes
    cleaned = cleaned.lstrip('/')

    # Maximum length check (standard Minecraft command limit)
    if len(cleaned) > 256:
        raise SecurityError("Command exceeds maximum allowed length of 256 characters.")

    # Prevent chained shell / terminal injection strings
    forbidden_tokens = ('&&', '||', ';', '`', '$(', '\n', '\r')
    if any(token in cleaned for token in forbidden_tokens):
        raise SecurityError("Command contains disallowed chaining or control tokens.")

    return cleaned

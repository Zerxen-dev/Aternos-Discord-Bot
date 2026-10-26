from __future__ import annotations

import time
import pytest

from bot.utils.security import CommandRateLimiter, SecurityError, sanitize_console_command


def test_sanitize_console_command_valid():
    assert sanitize_console_command("say Hello World") == "say Hello World"
    assert sanitize_console_command("/gamemode creative Steve") == "gamemode creative Steve"
    assert sanitize_console_command("time set day") == "time set day"


def test_sanitize_console_command_empty():
    with pytest.raises(SecurityError, match="cannot be empty"):
        sanitize_console_command("   ")


def test_sanitize_console_command_length():
    long_cmd = "a" * 300
    with pytest.raises(SecurityError, match="exceeds maximum allowed length"):
        sanitize_console_command(long_cmd)


def test_sanitize_console_command_forbidden_tokens():
    with pytest.raises(SecurityError, match="disallowed chaining or control tokens"):
        sanitize_console_command("say hello && rm -rf")

    with pytest.raises(SecurityError, match="disallowed chaining or control tokens"):
        sanitize_console_command("say hello; stop")

    with pytest.raises(SecurityError, match="disallowed chaining or control tokens"):
        sanitize_console_command("say `whoami`")

    with pytest.raises(SecurityError, match="disallowed chaining or control tokens"):
        sanitize_console_command("say $(id)")

    with pytest.raises(SecurityError, match="disallowed chaining or control tokens"):
        sanitize_console_command("say hello || stop")


def test_sanitize_console_command_control_chars():
    with pytest.raises(SecurityError, match="forbidden control characters"):
        sanitize_console_command("say hello\x00")

    with pytest.raises(SecurityError, match="forbidden control characters"):
        sanitize_console_command("say hello\nstop")


def test_rate_limiter():
    limiter = CommandRateLimiter(max_calls=3, window_seconds=2.0)
    user_id = 99999

    # First 3 calls succeed
    is_limited, _ = limiter.is_rate_limited(user_id)
    assert not is_limited

    is_limited, _ = limiter.is_rate_limited(user_id)
    assert not is_limited

    is_limited, _ = limiter.is_rate_limited(user_id)
    assert not is_limited

    # 4th call should be rate limited
    is_limited, retry_after = limiter.is_rate_limited(user_id)
    assert is_limited
    assert retry_after > 0

    # Another user is not affected
    other_limited, _ = limiter.is_rate_limited(88888)
    assert not other_limited

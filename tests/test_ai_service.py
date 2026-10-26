from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from bot.services.ai_service import AIService


@pytest.mark.asyncio
async def test_rule_based_parse_intents():
    # Players
    res = AIService._rule_based_parse("who is online right now?")
    assert res["intent"] == "players"

    # Start
    res = AIService._rule_based_parse("start the server please")
    assert res["intent"] == "start"

    # Stop
    res = AIService._rule_based_parse("shut down the server")
    assert res["intent"] == "stop"

    # Restart
    res = AIService._rule_based_parse("restart the server")
    assert res["intent"] == "restart"

    # Whitelist
    res = AIService._rule_based_parse("show me the whitelist")
    assert res["intent"] == "whitelist"

    # Info
    res = AIService._rule_based_parse("what is the server ram and ip?")
    assert res["intent"] == "info"

    # Status
    res = AIService._rule_based_parse("is the server running?")
    assert res["intent"] == "status"

    # Unknown
    res = AIService._rule_based_parse("play some jazz music")
    assert res["intent"] == "unknown"


@pytest.mark.asyncio
async def test_interpret_query_heuristic_fallback():
    # Without API key, falls back to rule-based directly
    res = await AIService.interpret_query("is the server alive?")
    assert res["intent"] == "status"


@pytest.mark.asyncio
async def test_interpret_query_gemini_mock():
    mock_response = {
        "intent": "start",
        "explanation": "Starting server",
        "action_label": "Start Server",
    }
    with patch.object(AIService, "_call_gemini", new=AsyncMock(return_value=mock_response)):
        res = await AIService.interpret_query("wake up the machine", api_key="dummy_key", provider="gemini")
        assert res["intent"] == "start"


@pytest.mark.asyncio
async def test_interpret_query_gemini_error_fallback():
    with patch.object(AIService, "_call_gemini", side_effect=Exception("Network error")):
        # On error, gracefully falls back to rule-based parsing
        res = await AIService.interpret_query("start the server", api_key="dummy_key", provider="gemini")
        assert res["intent"] == "start"

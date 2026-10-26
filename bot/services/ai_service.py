"""AI-Powered Natural Language Command parser for conversational server management."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import aiohttp

log = logging.getLogger('AternosBot.ai')


class AIService:
    """Parses natural language requests into structured bot actions."""

    @classmethod
    async def interpret_query(
        cls,
        query: str,
        api_key: Optional[str] = None,
        provider: str = 'gemini',
    ) -> dict[str, Any]:
        """Classify user query into an actionable bot command.

        Attempts LLM query if configured; falls back to deterministic rule-based NLP.
        """
        clean_query = query.strip()
        if api_key:
            try:
                if provider.lower() == 'gemini':
                    return await cls._call_gemini(clean_query, api_key)
                elif provider.lower() == 'openai':
                    return await cls._call_openai(clean_query, api_key)
            except Exception as e:
                log.warning(f'LLM API call failed: {e} — falling back to heuristic parser.')

        return cls._rule_based_parse(clean_query)

    @classmethod
    def _rule_based_parse(cls, query: str) -> dict[str, Any]:
        q = query.lower()

        # 1. Players & who is online
        if any(w in q for w in ('who is online', 'whos online', "who's online", 'online players', 'list players')):
            return {
                'intent': 'players',
                'explanation': 'Checking who is currently playing on the server.',
                'action_label': 'Online Players',
            }

        # 2. Server restart / reboot (checked before start)
        if any(w in q for w in ('restart the server', 'reboot the server', 'restart server', 'reboot server', 'restart', 'reboot')):
            return {
                'intent': 'restart',
                'explanation': 'Triggering Minecraft server reboot.',
                'action_label': 'Restart Server',
            }

        # 3. Server start / boot
        if any(w in q for w in ('start the server', 'turn on the server', 'boot the server', 'start server', 'boot server')):
            return {
                'intent': 'start',
                'explanation': 'Triggering Minecraft server startup routine.',
                'action_label': 'Start Server',
            }

        # 4. Server stop / shutdown
        if any(w in q for w in ('stop the server', 'shut down the server', 'turn off the server', 'shutdown server', 'stop server')):
            return {
                'intent': 'stop',
                'explanation': 'Requesting graceful server shutdown.',
                'action_label': 'Stop Server',
            }

        # 5. Whitelist
        if 'whitelist' in q or 'white list' in q:
            return {
                'intent': 'whitelist',
                'explanation': 'Inspecting whitelisted players.',
                'action_label': 'Whitelist List',
            }

        # 6. Detailed specs & info
        if any(w in q for w in ('ram', 'specs', 'ip', 'address', 'port', 'software', 'edition')):
            return {
                'intent': 'info',
                'explanation': 'Retrieving detailed server specifications and connection information.',
                'action_label': 'Server Info',
            }

        # 7. Status & running check
        if any(w in q for w in ('status', 'running', 'is it up', 'is it running', 'server running', 'server on', 'alive')):
            return {
                'intent': 'status',
                'explanation': 'Checking live server status and player count.',
                'action_label': 'Check Status',
            }

        return {
            'intent': 'unknown',
            'explanation': f"Could not determine a specific action for: '{query}'. Try asking 'is the server running?', 'who is online?', or 'start the server'.",
            'action_label': 'Unrecognized',
        }

    @classmethod
    async def _call_gemini(cls, query: str, api_key: str) -> dict[str, Any]:
        prompt = (
            "You are an assistant for a Minecraft Aternos server Discord bot. "
            "Classify the user's intent into exactly one of: ['status', 'players', 'start', 'stop', 'restart', 'info', 'whitelist', 'unknown']. "
            "Respond ONLY with a JSON object: {\"intent\": \"<intent>\", \"explanation\": \"<short explanation>\", \"action_label\": \"<short label>\"}. "
            f"User query: \"{query}\""
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Gemini API returned status {resp.status}")
                data = await resp.json()
                text = data['candidates'][0]['content']['parts'][0]['text'].strip()
                # Extract JSON if enclosed in markdown code fences
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                return json.loads(text)

    @classmethod
    async def _call_openai(cls, query: str, api_key: str) -> dict[str, Any]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Classify user request for a Minecraft server bot into JSON: "
                        "{\"intent\": \"status\"|\"players\"|\"start\"|\"stop\"|\"restart\"|\"info\"|\"whitelist\"|\"unknown\", "
                        "\"explanation\": \"...\", \"action_label\": \"...\"}"
                    ),
                },
                {"role": "user", "content": query},
            ],
            "temperature": 0.1,
            "max_tokens": 150,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"OpenAI API returned status {resp.status}")
                data = await resp.json()
                content = data['choices'][0]['message']['content'].strip()
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                return json.loads(content)

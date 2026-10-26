# 🤖 AI Assistant (/ask) Integration Guide

The Aternos Discord Bot includes an intelligent natural language interface powered by **Google Gemini** or **OpenAI**. Server members and operators can type requests naturally without memorizing slash command parameters.

---

## Example Queries

- *"Is anyone playing right now?"* ➔ Dispatches `/status` player report.
- *"Start the Minecraft server please"* ➔ Triggers `/start` routine.
- *"Shut down the server"* ➔ Triggers graceful `/stop`.
- *"Reboot the server"* ➔ Triggers `/restart`.
- *"What's the server IP and RAM?"* ➔ Returns server connection and hardware specs.
- *"Show me the whitelist"* ➔ Displays whitelisted players.

---

## Configuration

In your `.env` file, configure your preferred provider and API key:

### Using Google Gemini (Recommended)
1. Get a free API key at [Google AI Studio](https://aistudio.google.com/).
2. Add to `.env`:
   ```env
   AI_PROVIDER=gemini
   AI_API_KEY=AIzaSy...
   ```

### Using OpenAI
1. Get an API key from [OpenAI Platform](https://platform.openai.com/api-keys).
2. Add to `.env`:
   ```env
   AI_PROVIDER=openai
   AI_API_KEY=sk-proj-...
   ```

### Offline / Heuristic Mode (No API Key Required)
If `AI_API_KEY` is left blank, the bot automatically employs a deterministic regex and keyword natural language parser that requires zero external network calls or costs.

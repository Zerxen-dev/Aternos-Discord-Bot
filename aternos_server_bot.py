"""Entry point for the Aternos Discord Bot.

All of the actual logic lives in the `bot` package — this file just wires
it together so `python aternos_server_bot.py` (or `python main.py`, which
execs this file) keeps working the way it always has.
"""

from bot.app import main

if __name__ == '__main__':
    main()

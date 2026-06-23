"""Top-level startup: logging, config, Aternos login, and the resilient run loop."""

from __future__ import annotations

import logging
import sys
import threading
import time
import traceback

import discord

from .aternos_client import AternosManager, AternosError
from .config import ConfigError, load_config
from .core import AternosBot
from .state import BotState

log = logging.getLogger('AternosBot')


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s  %(levelname)-8s  %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )


def _install_exception_hooks() -> None:
    def handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        log.critical('UNCAUGHT EXCEPTION', exc_info=(exc_type, exc_value, exc_tb))

    def handle_thread_exception(args):
        log.critical(f'UNCAUGHT THREAD EXCEPTION in {args.thread}', exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    sys.excepthook = handle_exception
    threading.excepthook = handle_thread_exception


def main() -> None:
    _setup_logging()
    _install_exception_hooks()

    try:
        config = load_config()
    except ConfigError as e:
        log.critical(str(e))
        sys.exit(1)

    aternos = AternosManager(config.aternos_user, config.aternos_pass)
    try:
        aternos.login_blocking(retries=6, base_delay=5.0)
    except AternosError as e:
        log.critical(f'Could not connect to Aternos — giving up: {e}')
        sys.exit(1)

    state = BotState.load(config.state_file)
    bot = AternosBot(config, aternos, state)

    log.info('Starting Discord bot...')
    restart_delay = 5
    while True:
        try:
            bot.run(config.discord_token, log_handler=None, reconnect=True)
            log.warning('bot.run() returned — restarting in 5s ...')
        except discord.LoginFailure:
            log.critical('Invalid Discord token — cannot reconnect. Check DISCORD_TOKEN.')
            sys.exit(1)
        except KeyboardInterrupt:
            log.info('Keyboard interrupt — shutting down.')
            sys.exit(0)
        except Exception as e:
            log.error(f'bot.run() crashed: {e}\n{traceback.format_exc()}')
            log.info(f'Restarting bot in {restart_delay}s ...')
        time.sleep(restart_delay)
        restart_delay = min(restart_delay * 2, 60)

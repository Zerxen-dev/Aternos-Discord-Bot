"""Shared visual constants: embed colours and status -> emoji/colour mappings."""

GREEN = 0x57F287
RED = 0xED4245
BLUE = 0x5865F2
YELLOW = 0xFEE75C
TEAL = 0x1ABC9C
PURPLE = 0x9B59B6

_STATUS_COLORS = {
    'online': GREEN,
    'starting': YELLOW,
    'stopping': YELLOW,
    'loading': YELLOW,
    'preparing': YELLOW,
    'offline': RED,
    'error': RED,
}

_STATUS_EMOJI = {
    'online': '🟢',
    'starting': '🟡',
    'stopping': '🟡',
    'loading': '🟡',
    'preparing': '🟡',
    'offline': '🔴',
    'error': '❌',
}

TRANSITIONAL_STATES = frozenset({'starting', 'loading', 'preparing'})


def status_color(status: str) -> int:
    return _STATUS_COLORS.get(status.lower(), BLUE)


def status_emoji(status: str) -> str:
    return _STATUS_EMOJI.get(status.lower(), '⚪')

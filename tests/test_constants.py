from bot.constants import BLUE, GREEN, RED, status_color, status_emoji


def test_status_color_known_states():
    assert status_color('online') == GREEN
    assert status_color('OFFLINE') == RED


def test_status_color_unknown_state_defaults_to_blue():
    assert status_color('weird') == BLUE


def test_status_emoji_known_and_unknown():
    assert status_emoji('online') == '🟢'
    assert status_emoji('offline') == '🔴'
    assert status_emoji('mystery') == '⚪'

import json

from bot.state import BotState


def test_round_trip(tmp_path):
    path = tmp_path / 'state.json'
    state = BotState(
        autostart_enabled=True,
        autostart_channel_id=123,
        autostart_set_by='alice',
        autostop_enabled=True,
        autostop_minutes=30,
        autostop_channel_id=456,
        autostop_set_by='bob',
    )
    state.save(path)

    assert BotState.load(path) == state


def test_load_missing_file_returns_defaults(tmp_path):
    assert BotState.load(tmp_path / 'missing.json') == BotState()


def test_load_migrates_legacy_format(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'enabled': True, 'channel_id': 999, 'set_by': 'bob'}))

    loaded = BotState.load(path)
    assert loaded.autostart_enabled is True
    assert loaded.autostart_channel_id == 999
    assert loaded.autostart_set_by == 'bob'
    assert loaded.autostop_enabled is False


def test_load_corrupt_file_returns_defaults(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text('{not valid json')

    assert BotState.load(path) == BotState()

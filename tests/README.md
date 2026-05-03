# roomba_rest980 tests

Pure unit tests for entity logic, action methods and the activity state machine.
The tests use `unittest.mock` only — no `pytest-homeassistant-custom-component`
fixture machinery, so they run anywhere a Home Assistant install is importable.

## Running

The simplest way is inside the official Home Assistant container, which already
has Python + HA:

```bash
docker run --rm \
  -v "$PWD":/repo -w /repo \
  ghcr.io/home-assistant/home-assistant:stable \
  bash -c "pip install -q pytest-asyncio && python -m pytest tests/"
```

Or in a venv with HA installed:

```bash
python -m venv .venv && source .venv/bin/activate
pip install homeassistant pytest pytest-asyncio
python -m pytest tests/
```

## Coverage

| File | Covers |
|---|---|
| `test_switch.py` | `RoombaEdgeCleanSwitch`, `RoombaAlwaysFinishSwitch` — `is_on` derivation, `turn_on/off` URLs, refresh-on-success, no-refresh-on-failure |
| `test_select.py` | `RoombaCarpetBoostSelect`, `RoombaCleaningPassesSelect` — `current_option` derivation across all coordinator states, `select_option` URL routing |
| `test_vacuum.py` | `RoombaVacuum` activity state machine (parametrized over cycle/phase/notReady combinations) and all six action methods (`start`, `stop`, `pause`, `return_to_base`, `clean_spot`, `send_command`), including `start`-while-paused → `resume` |

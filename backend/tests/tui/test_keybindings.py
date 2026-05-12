import pytest
from cli.tui.app import TuiApp


@pytest.mark.asyncio
async def test_app_has_bindings():
    app = TuiApp()
    actions = []
    for bindings in app._bindings.key_to_bindings.values():
        for b in bindings:
            actions.append(b.action)
    assert "quit" in actions

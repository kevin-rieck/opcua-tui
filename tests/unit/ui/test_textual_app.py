import asyncio

from opcua_tui.app.messages import AppStarted, ConnectRequested, RootBrowseRequested
from opcua_tui.ui import textual_app
from opcua_tui.ui.screens.browser_screen import BrowserScreen


def test_run_constructs_app_and_calls_run(monkeypatch) -> None:
    called: list[bool] = []

    class DummyApp:
        def run(self) -> None:
            called.append(True)

    monkeypatch.setattr(textual_app, "OpcUaTuiApp", DummyApp)

    textual_app.run()

    assert called == [True]


def test_app_on_mount_dispatches_startup_messages(monkeypatch) -> None:
    dispatched: list[object] = []
    pushed_screens: list[object] = []

    class FakeStore:
        async def dispatch(self, message: object) -> None:
            dispatched.append(message)

    monkeypatch.setattr(textual_app, "build_store", lambda: FakeStore())
    app = textual_app.OpcUaTuiApp()

    async def fake_push_screen(screen: object) -> None:
        pushed_screens.append(screen)

    app.push_screen = fake_push_screen  # type: ignore[method-assign]

    asyncio.run(app.on_mount())

    assert len(pushed_screens) == 1
    assert isinstance(pushed_screens[0], BrowserScreen)
    assert isinstance(dispatched[0], AppStarted)
    assert isinstance(dispatched[1], ConnectRequested)
    assert isinstance(dispatched[2], RootBrowseRequested)

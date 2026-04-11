import asyncio

from opcua_tui.app.messages import ConnectionSucceeded, RootBrowseRequested
from opcua_tui.domain.models import ServerInfo, SessionInfo
from opcua_tui.ui import textual_app
from opcua_tui.ui.screens.browser_screen import BrowserScreen
from opcua_tui.ui.screens.connect_modal_screen import ConnectModalScreen


def test_run_constructs_app_and_calls_run(monkeypatch) -> None:
    called: list[bool] = []

    class DummyApp:
        def run(self) -> None:
            called.append(True)

    monkeypatch.setattr(textual_app, "OpcUaTuiApp", DummyApp)

    textual_app.run()

    assert called == [True]


def test_app_on_mount_opens_connect_modal_without_dispatching_store_messages() -> None:
    pushed_screens: list[tuple[object, object]] = []
    app = textual_app.OpcUaTuiApp()

    async def fake_push_screen(screen: object, callback=None) -> None:
        pushed_screens.append((screen, callback))

    app.push_screen = fake_push_screen  # type: ignore[method-assign]

    asyncio.run(app.on_mount())

    assert len(pushed_screens) == 1
    assert isinstance(pushed_screens[0][0], ConnectModalScreen)
    assert pushed_screens[0][1] is not None


def test_handle_connect_modal_result_pushes_browser_and_dispatches_state_messages() -> None:
    dispatched: list[object] = []
    pushed_screens: list[object] = []
    app = textual_app.OpcUaTuiApp()

    async def fake_dispatch(message: object) -> None:
        dispatched.append(message)

    async def fake_push_screen(screen: object, callback=None) -> None:
        pushed_screens.append(screen)

    app.store.dispatch = fake_dispatch  # type: ignore[method-assign]
    app.push_screen = fake_push_screen  # type: ignore[method-assign]

    session = SessionInfo(
        session_id="s1",
        endpoint="opc.tcp://localhost:4840",
        server=ServerInfo(application_name="Server"),
    )
    asyncio.run(app._handle_connect_modal_result(session))

    assert len(pushed_screens) == 1
    assert isinstance(pushed_screens[0], BrowserScreen)
    assert isinstance(dispatched[0], ConnectionSucceeded)
    assert isinstance(dispatched[1], RootBrowseRequested)

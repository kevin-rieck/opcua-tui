import asyncio

from opcua_tui.app.messages import ConnectFormValidationFailed, ConnectRequested
from opcua_tui.domain.enums import AuthenticationMode, SecurityMode, SecurityPolicy
from opcua_tui.domain.models import (
    AppState,
    ConnectModalState,
    ConnectParams,
    SessionState,
    UiState,
)
from opcua_tui.ui.screens.connect_modal_screen import ConnectModalScreen


class FakeStore:
    def __init__(self, state: AppState) -> None:
        self.state = state
        self.dispatched: list[object] = []
        self.subscribers: list[object] = []

    def subscribe(self, fn) -> None:
        self.subscribers.append(fn)

    async def dispatch(self, message: object) -> None:
        self.dispatched.append(message)


class FakeInput:
    def __init__(self, value: str = "") -> None:
        self.value = value
        self.disabled = False
        self.focused = False

    def focus(self) -> None:
        self.focused = True


class FakeSelect:
    def __init__(self, value: str = "") -> None:
        self.value = value


class FakeButton:
    def __init__(self) -> None:
        self.disabled = False


class FakeStatic:
    def __init__(self) -> None:
        self.text = ""

    def update(self, value: str) -> None:
        self.text = value


def _build_widgets() -> dict[str, object]:
    return {
        "#endpoint": FakeInput(),
        "#security_mode": FakeSelect(),
        "#security_policy": FakeSelect(),
        "#authentication_mode": FakeSelect(),
        "#username": FakeInput(),
        "#password": FakeInput(),
        "#certificate_path": FakeInput(),
        "#private_key_path": FakeInput(),
        "#connect-error": FakeStatic(),
        "#submit": FakeButton(),
    }


def test_connect_modal_on_mount_focuses_endpoint_and_renders_defaults(monkeypatch) -> None:
    state = AppState(
        connect_modal=ConnectModalState(
            is_open=True,
            params=ConnectParams(
                endpoint="opc.tcp://localhost:4840",
                security_mode=SecurityMode.NONE,
                security_policy=SecurityPolicy.NONE,
                authentication_mode=AuthenticationMode.ANONYMOUS,
            ),
        ),
        ui=UiState(status_text="Ready"),
    )
    store = FakeStore(state)
    screen = ConnectModalScreen(store)
    widgets = _build_widgets()

    monkeypatch.setattr(screen, "query_one", lambda selector, _type=None: widgets[selector])

    asyncio.run(screen.on_mount())

    assert len(store.subscribers) == 1
    assert widgets["#endpoint"].focused is True
    assert widgets["#security_mode"].value == SecurityMode.NONE.value
    assert widgets["#security_policy"].value == SecurityPolicy.NONE.value
    assert widgets["#authentication_mode"].value == AuthenticationMode.ANONYMOUS.value
    assert widgets["#username"].disabled is True
    assert widgets["#password"].disabled is True
    assert widgets["#submit"].disabled is False


def test_connect_modal_submit_dispatches_connect_requested(monkeypatch) -> None:
    state = AppState(connect_modal=ConnectModalState(is_open=True))
    store = FakeStore(state)
    screen = ConnectModalScreen(store)
    params = ConnectParams(
        endpoint="opc.tcp://localhost:4840",
        security_mode=SecurityMode.NONE,
        security_policy=SecurityPolicy.NONE,
        authentication_mode=AuthenticationMode.ANONYMOUS,
    )
    monkeypatch.setattr(screen, "_read_form_values", lambda: params)

    asyncio.run(screen._submit_form())

    assert len(store.dispatched) == 1
    assert store.dispatched[0] == ConnectRequested(params=params)


def test_connect_modal_submit_rejects_invalid_endpoint(monkeypatch) -> None:
    state = AppState(connect_modal=ConnectModalState(is_open=True))
    store = FakeStore(state)
    screen = ConnectModalScreen(store)
    monkeypatch.setattr(screen, "_read_form_values", lambda: ConnectParams(endpoint="http://bad"))

    asyncio.run(screen._submit_form())

    assert len(store.dispatched) == 1
    assert store.dispatched[0] == ConnectFormValidationFailed(
        error="Endpoint must start with opc.tcp://"
    )


def test_connect_modal_render_state_enables_certificate_fields_for_certificate_auth(
    monkeypatch,
) -> None:
    state = AppState(
        session=SessionState(status="disconnected"),
        connect_modal=ConnectModalState(
            is_open=True,
            params=ConnectParams(
                endpoint="opc.tcp://localhost:4840",
                authentication_mode=AuthenticationMode.CERTIFICATE,
            ),
            error="boom",
        ),
    )
    store = FakeStore(state)
    screen = ConnectModalScreen(store)
    widgets = _build_widgets()

    monkeypatch.setattr(screen, "query_one", lambda selector, _type=None: widgets[selector])

    screen.render_state(state)

    assert widgets["#username"].disabled is True
    assert widgets["#password"].disabled is True
    assert widgets["#certificate_path"].disabled is False
    assert widgets["#private_key_path"].disabled is False
    assert widgets["#connect-error"].text == "boom"

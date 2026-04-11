import asyncio

from opcua_tui.domain.models import ConnectParams
from opcua_tui.ui.screens.connect_modal_screen import ConnectModalScreen


class FakeOpcUa:
    async def connect(self, _params: ConnectParams):
        raise NotImplementedError


class FakeInput:
    def __init__(self, value: str = "") -> None:
        self.value = value
        self.disabled = False
        self.focused = False

    def focus(self) -> None:
        self.focused = True


class FakeButton:
    def __init__(self, label: str = "Connect") -> None:
        self.disabled = False
        self.label = label


class FakeStatic:
    def __init__(self) -> None:
        self.text = ""

    def update(self, value: str) -> None:
        self.text = value


def _build_widgets(endpoint: str = "") -> dict[str, object]:
    return {
        "#endpoint": FakeInput(value=endpoint),
        "#connect-error": FakeStatic(),
        "#submit": FakeButton(),
        "#cancel": FakeButton(label="Cancel"),
    }


def test_connect_modal_on_mount_focuses_endpoint_and_renders_defaults(monkeypatch) -> None:
    screen = ConnectModalScreen(
        opcua=FakeOpcUa(),
        initial_params=ConnectParams(endpoint="opc.tcp://localhost:4840"),
    )
    widgets = _build_widgets()
    monkeypatch.setattr(screen, "query_one", lambda selector, _type=None: widgets[selector])

    asyncio.run(screen.on_mount())

    assert screen.endpoint == "opc.tcp://localhost:4840"
    assert widgets["#endpoint"].focused is True
    assert widgets["#submit"].disabled is False


def test_connect_modal_submit_starts_connect_for_valid_endpoint(monkeypatch) -> None:
    screen = ConnectModalScreen(
        opcua=FakeOpcUa(),
        initial_params=ConnectParams(endpoint="opc.tcp://localhost:4840"),
    )
    widgets = _build_widgets(endpoint="opc.tcp://localhost:4840")
    started: list[object] = []
    monkeypatch.setattr(screen, "query_one", lambda selector, _type=None: widgets[selector])

    def fake_run_worker(coro, *, exclusive=False, group=None):
        started.append((coro, exclusive, group))
        coro.close()
        return None

    monkeypatch.setattr(screen, "run_worker", fake_run_worker)

    asyncio.run(screen._submit_form())

    assert screen.is_submitting is True
    assert len(started) == 1
    assert started[0][1] is True
    assert started[0][2] == "connect"


def test_connect_modal_submit_rejects_invalid_endpoint(monkeypatch) -> None:
    screen = ConnectModalScreen(
        opcua=FakeOpcUa(),
        initial_params=ConnectParams(endpoint="opc.tcp://localhost:4840"),
    )
    widgets = _build_widgets(endpoint="http://bad")
    monkeypatch.setattr(screen, "query_one", lambda selector, _type=None: widgets[selector])

    asyncio.run(screen._submit_form())

    assert screen.is_submitting is False
    assert screen.error_text == "Endpoint must start with opc.tcp://"

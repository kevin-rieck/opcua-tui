import asyncio

from opcua_tui.domain.enums import AuthenticationMode, SecurityMode, SecurityPolicy
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


class FakeSelect:
    def __init__(self, value) -> None:
        self.value = value
        self.disabled = False


class FakeContainer:
    def __init__(self) -> None:
        self.display = True


def _build_widgets(endpoint: str = "") -> dict[str, object]:
    return {
        "#endpoint": FakeInput(value=endpoint),
        "#security-mode": FakeSelect(SecurityMode.NONE),
        "#security-policy": FakeSelect(SecurityPolicy.NONE),
        "#auth-mode": FakeSelect(AuthenticationMode.ANONYMOUS),
        "#username-field": FakeContainer(),
        "#username": FakeInput(),
        "#password-field": FakeContainer(),
        "#password": FakeInput(),
        "#certificate-path": FakeInput(),
        "#private-key-path": FakeInput(),
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


def test_connect_modal_rejects_security_mode_and_policy_mismatch(monkeypatch) -> None:
    screen = ConnectModalScreen(
        opcua=FakeOpcUa(),
        initial_params=ConnectParams(endpoint="opc.tcp://localhost:4840"),
    )
    widgets = _build_widgets(endpoint="opc.tcp://localhost:4840")
    widgets["#security-mode"].value = SecurityMode.SIGN
    widgets["#security-policy"].value = SecurityPolicy.NONE
    monkeypatch.setattr(screen, "query_one", lambda selector, _type=None: widgets[selector])

    asyncio.run(screen._submit_form())

    assert screen.is_submitting is False
    assert "Security policy is required" in screen.error_text


def test_connect_modal_requires_credentials_for_username_auth(monkeypatch) -> None:
    screen = ConnectModalScreen(
        opcua=FakeOpcUa(),
        initial_params=ConnectParams(endpoint="opc.tcp://localhost:4840"),
    )
    widgets = _build_widgets(endpoint="opc.tcp://localhost:4840")
    widgets["#auth-mode"].value = AuthenticationMode.USERNAME_PASSWORD
    widgets["#username"].value = ""
    widgets["#password"].value = ""
    monkeypatch.setattr(screen, "query_one", lambda selector, _type=None: widgets[selector])
    monkeypatch.setattr(
        screen,
        "run_worker",
        lambda coro, **_kwargs: (coro.close(), None)[1],
    )

    asyncio.run(screen._submit_form())
    assert "Username is required" in screen.error_text

    widgets["#auth-mode"].value = AuthenticationMode.USERNAME_PASSWORD
    widgets["#username"].value = "operator"
    widgets["#endpoint"].value = "opc.tcp://localhost:4840"
    asyncio.run(screen._submit_form())
    assert "Password is required" in screen.error_text


def test_connect_modal_formats_trust_error_with_actionable_hints() -> None:
    screen = ConnectModalScreen(
        opcua=FakeOpcUa(),
        initial_params=ConnectParams(endpoint="opc.tcp://localhost:4840"),
    )

    text = screen._format_connection_error(
        message="BadCertificateUntrusted",
        error_ref="abc12345",
        params=ConnectParams(
            endpoint="opc.tcp://localhost:4840",
            security_mode=SecurityMode.SIGN,
            security_policy=SecurityPolicy.BASIC256SHA256,
        ),
    )

    assert "Server certificate is not trusted." in text
    assert "PKI path: ~/.opcua-tui/pki" in text
    assert "Reference: abc12345" in text


def test_connect_modal_formats_auth_error_with_actionable_hints() -> None:
    screen = ConnectModalScreen(
        opcua=FakeOpcUa(),
        initial_params=ConnectParams(endpoint="opc.tcp://localhost:4840"),
    )

    text = screen._format_connection_error(
        message="BadUserAccessDenied",
        error_ref="def67890",
        params=ConnectParams(
            endpoint="opc.tcp://localhost:4840",
            authentication_mode=AuthenticationMode.USERNAME_PASSWORD,
            username="operator",
            password="secret",
        ),
    )

    assert "Authentication failed." in text
    assert "Verify username and password" in text
    assert "Reference: def67890" in text


def test_connect_modal_sanitizes_endpoint_credentials_in_error_details() -> None:
    screen = ConnectModalScreen(
        opcua=FakeOpcUa(),
        initial_params=ConnectParams(endpoint="opc.tcp://localhost:4840"),
    )

    raw = "failed to connect opc.tcp://user:pass@localhost:4840"
    sanitized = screen._sanitize_error_message(raw, "opc.tcp://user:pass@localhost:4840")

    assert "user:pass@" not in sanitized
    assert "opc.tcp://***@localhost:4840" in sanitized

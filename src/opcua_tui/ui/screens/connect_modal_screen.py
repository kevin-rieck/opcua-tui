from __future__ import annotations

import logging
import uuid

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from opcua_tui.application.ports.opcua_client import OpcUaClientPort
from opcua_tui.domain.endpoint import sanitize_endpoint
from opcua_tui.domain.enums import AuthenticationMode, SecurityMode, SecurityPolicy
from opcua_tui.domain.models import ConnectParams, SessionInfo


logger = logging.getLogger(__name__)


class ConnectModalScreen(ModalScreen[SessionInfo | None]):
    endpoint: reactive[str] = reactive("")
    security_mode: reactive[SecurityMode] = reactive(SecurityMode.NONE)
    security_policy: reactive[SecurityPolicy] = reactive(SecurityPolicy.NONE)
    authentication_mode: reactive[AuthenticationMode] = reactive(AuthenticationMode.ANONYMOUS)
    username: reactive[str] = reactive("")
    password: reactive[str] = reactive("")
    certificate_path: reactive[str] = reactive("")
    private_key_path: reactive[str] = reactive("")
    is_submitting: reactive[bool] = reactive(False)
    error_text: reactive[str] = reactive("")

    CSS = """
    ConnectModalScreen {
        align: center middle;
    }

    #connect-dialog {
        layout: vertical;
        width: 52;
        max-width: 70vw;
        height: 30;
        max-height: 85vh;
        background: $surface;
        border: round $accent;
    }

    #connect-body {
        layout: vertical;
        padding: 1 2;
        height: 1fr;
        overflow-y: auto;
    }

    #connect-copy {
        height: auto;
        margin-bottom: 1;
    }

    #connect-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #connect-subtitle {
        color: $text-muted;
    }

    #connect-error {
        color: $error;
        min-height: 1;
        margin-top: 1;
    }

    .connect-section {
        layout: vertical;
        height: auto;
        margin-top: 1;
    }

    .connect-field {
        layout: vertical;
        height: auto;
        margin-bottom: 1;
    }

    .connect-label {
        margin-bottom: 1;
    }

    .connect-input {
        width: 1fr;
        height: 3;
    }

    Select {
        width: 1fr;
        height: 3;
    }

    .connect-optional {
        color: $text-muted;
    }

    .connect-note {
        color: $warning;
        margin-top: 1;
    }

    #connect-footer {
        height: auto;
    }

    Horizontal#connect-actions {
        align-horizontal: right;
        height: auto;
        padding: 1 2;
        border-top: solid $accent-darken-1;
    }

    Horizontal#connect-actions > Button {
        height: auto;
    }

    Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "submit", "Connect"),
    ]

    def __init__(
        self,
        *,
        opcua: OpcUaClientPort,
        initial_params: ConnectParams,
    ) -> None:
        super().__init__()
        self._opcua = opcua
        self._initial_params = initial_params
        self._suppress_form_events = False
        self._dismissed = False

    def compose(self) -> ComposeResult:
        with Container(id="connect-dialog"):
            with Vertical(id="connect-body"):
                with Vertical(id="connect-copy"):
                    yield Static("Connect to OPC UA Server", id="connect-title")
                    yield Static(
                        "Choose endpoint security and authentication.",
                        id="connect-subtitle",
                    )
                with Vertical(classes="connect-section"):
                    with Vertical(classes="connect-field"):
                        yield Label("Endpoint", classes="connect-label")
                        yield Input(
                            placeholder="opc.tcp://localhost:4840",
                            id="endpoint",
                            classes="connect-input",
                        )
                    with Vertical(classes="connect-field"):
                        yield Label("Security Mode", classes="connect-label")
                        yield Select[SecurityMode](
                            [
                                ("None", SecurityMode.NONE),
                                ("Sign", SecurityMode.SIGN),
                                ("SignAndEncrypt", SecurityMode.SIGN_AND_ENCRYPT),
                            ],
                            id="security-mode",
                            value=SecurityMode.NONE,
                            allow_blank=False,
                        )
                    with Vertical(classes="connect-field"):
                        yield Label("Security Policy", classes="connect-label")
                        yield Select[SecurityPolicy](
                            [
                                ("None", SecurityPolicy.NONE),
                                ("Basic256Sha256", SecurityPolicy.BASIC256SHA256),
                                (
                                    "Aes128Sha256RsaOaep",
                                    SecurityPolicy.AES128_SHA256_RSAOAEP,
                                ),
                                (
                                    "Aes256Sha256RsaPss",
                                    SecurityPolicy.AES256_SHA256_RSAPSS,
                                ),
                                ("Basic256", SecurityPolicy.BASIC256),
                                ("Basic128Rsa15", SecurityPolicy.BASIC128RSA15),
                            ],
                            id="security-policy",
                            value=SecurityPolicy.NONE,
                            allow_blank=False,
                        )
                    with Vertical(classes="connect-field"):
                        yield Label("Auth Mode", classes="connect-label")
                        yield Select[AuthenticationMode](
                            [
                                ("Anonymous", AuthenticationMode.ANONYMOUS),
                                (
                                    "Username/Password",
                                    AuthenticationMode.USERNAME_PASSWORD,
                                ),
                            ],
                            id="auth-mode",
                            value=AuthenticationMode.ANONYMOUS,
                            allow_blank=False,
                        )
                    with Vertical(classes="connect-field", id="username-field"):
                        yield Label("Username", classes="connect-label")
                        yield Input(id="username", classes="connect-input")
                    with Vertical(classes="connect-field", id="password-field"):
                        yield Label("Password", classes="connect-label")
                        yield Input(id="password", password=True, classes="connect-input")
                    with Vertical(classes="connect-field"):
                        yield Label("Client Certificate Path", classes="connect-label")
                        yield Input(
                            placeholder="(optional) auto-generate under ~/.opcua-tui/pki",
                            id="certificate-path",
                            classes="connect-input",
                        )
                    with Vertical(classes="connect-field"):
                        yield Label("Client Private Key Path", classes="connect-label")
                        yield Input(
                            placeholder="(optional) auto-generate under ~/.opcua-tui/pki",
                            id="private-key-path",
                            classes="connect-input",
                        )
                    yield Static(
                        "Username/password is available in v1. "
                        "Certificate identity auth is not yet supported.",
                        classes="connect-optional",
                    )
                with Vertical(id="connect-footer"):
                    yield Static("", id="connect-error")
            with Horizontal(id="connect-actions"):
                yield Button("Cancel", id="cancel")
                yield Button("Connect", id="submit", variant="primary")

    async def on_mount(self) -> None:
        self.endpoint = self._initial_params.endpoint
        self.security_mode = self._initial_params.security_mode
        self.security_policy = self._initial_params.security_policy
        self.authentication_mode = self._initial_params.authentication_mode
        self.username = self._initial_params.username
        self.password = self._initial_params.password
        self.certificate_path = self._initial_params.certificate_path
        self.private_key_path = self._initial_params.private_key_path
        self._refresh_view()
        self.query_one("#endpoint", Input).focus()

    def watch_endpoint(self, _endpoint: str) -> None:
        self._refresh_view()

    def watch_is_submitting(self, _is_submitting: bool) -> None:
        self._refresh_view()

    def watch_error_text(self, _error_text: str) -> None:
        self._refresh_view()

    def _refresh_view(self) -> None:
        endpoint_input = self.query_one("#endpoint", Input)
        security_mode_select = self.query_one("#security-mode", Select)
        security_policy_select = self.query_one("#security-policy", Select)
        auth_mode_select = self.query_one("#auth-mode", Select)
        username_field = self.query_one("#username-field", Vertical)
        username_input = self.query_one("#username", Input)
        password_field = self.query_one("#password-field", Vertical)
        password_input = self.query_one("#password", Input)
        cert_path_input = self.query_one("#certificate-path", Input)
        key_path_input = self.query_one("#private-key-path", Input)
        error_widget = self.query_one("#connect-error", Static)
        submit_button = self.query_one("#submit", Button)
        cancel_button = self.query_one("#cancel", Button)

        self._suppress_form_events = True
        try:
            if endpoint_input.value != self.endpoint:
                endpoint_input.value = self.endpoint
            if security_mode_select.value != self.security_mode:
                security_mode_select.value = self.security_mode
            if security_policy_select.value != self.security_policy:
                security_policy_select.value = self.security_policy
            if auth_mode_select.value != self.authentication_mode:
                auth_mode_select.value = self.authentication_mode
            if username_input.value != self.username:
                username_input.value = self.username
            if password_input.value != self.password:
                password_input.value = self.password
            if cert_path_input.value != self.certificate_path:
                cert_path_input.value = self.certificate_path
            if key_path_input.value != self.private_key_path:
                key_path_input.value = self.private_key_path
        finally:
            self._suppress_form_events = False

        show_username_password = self.authentication_mode == AuthenticationMode.USERNAME_PASSWORD
        username_field.display = show_username_password
        password_field.display = show_username_password

        endpoint_input.disabled = self.is_submitting
        security_mode_select.disabled = self.is_submitting
        security_policy_select.disabled = self.is_submitting
        auth_mode_select.disabled = self.is_submitting
        username_input.disabled = self.is_submitting
        password_input.disabled = self.is_submitting
        cert_path_input.disabled = self.is_submitting
        key_path_input.disabled = self.is_submitting
        cancel_button.disabled = self.is_submitting
        submit_button.disabled = self.is_submitting or not self.endpoint.strip()
        submit_button.label = "Connecting..." if self.is_submitting else "Connect"
        error_widget.update(self.error_text)

    async def on_input_changed(self, _event: Input.Changed) -> None:
        if self._suppress_form_events:
            return
        self.endpoint = self.query_one("#endpoint", Input).value
        self.username = self.query_one("#username", Input).value
        self.password = self.query_one("#password", Input).value
        self.certificate_path = self.query_one("#certificate-path", Input).value
        self.private_key_path = self.query_one("#private-key-path", Input).value

    async def on_select_changed(self, _event: Select.Changed) -> None:
        if self._suppress_form_events:
            return
        self.security_mode = self.query_one("#security-mode", Select).value
        self.security_policy = self.query_one("#security-policy", Select).value
        self.authentication_mode = self.query_one("#auth-mode", Select).value

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            await self.action_cancel()
            return
        if event.button.id == "submit":
            await self._submit_form()

    async def action_cancel(self) -> None:
        if self.is_submitting:
            return
        self.dismiss(None)

    async def action_submit(self) -> None:
        await self._submit_form()

    async def _submit_form(self) -> None:
        params = self._read_form_values()
        validation_error = self._validate_params(params)
        if validation_error is not None:
            self.error_text = validation_error
            return

        self.error_text = ""
        self.is_submitting = True
        self.run_worker(self._connect(params), exclusive=True, group="connect")

    async def _connect(self, params: ConnectParams) -> None:
        try:
            session = await self._opcua.connect(params)
        except Exception as exc:
            error_ref = uuid.uuid4().hex[:8]
            safe_endpoint = sanitize_endpoint(params.endpoint)
            logger.exception(
                "OPC UA connect failed",
                extra={"endpoint": safe_endpoint, "error_ref": error_ref},
            )
            self.error_text = self._format_connection_error(
                message=self._sanitize_error_message(str(exc), params.endpoint),
                error_ref=error_ref,
                params=params,
            )
            self.is_submitting = False
            return

        self.is_submitting = False
        if not self._dismissed:
            self._dismissed = True
            self.dismiss(session)

    def _validate_params(self, params: ConnectParams) -> str | None:
        endpoint = params.endpoint.strip()
        if not endpoint:
            return "Endpoint is required"
        if not endpoint.startswith("opc.tcp://"):
            return "Endpoint must start with opc.tcp://"
        if (
            params.security_mode == SecurityMode.NONE
            and params.security_policy != SecurityPolicy.NONE
        ):
            return "Security policy must be None when security mode is None"
        if (
            params.security_mode != SecurityMode.NONE
            and params.security_policy == SecurityPolicy.NONE
        ):
            return "Security policy is required when security mode is Sign or SignAndEncrypt"
        if params.authentication_mode == AuthenticationMode.USERNAME_PASSWORD:
            if not params.username.strip():
                return "Username is required for username/password authentication"
            if not params.password:
                return "Password is required for username/password authentication"
        if params.authentication_mode == AuthenticationMode.CERTIFICATE:
            return "Certificate authentication is not supported in v1"
        cert_path = params.certificate_path.strip()
        key_path = params.private_key_path.strip()
        if cert_path and not key_path:
            return "Private key path is required when certificate path is provided"
        if key_path and not cert_path:
            return "Certificate path is required when private key path is provided"
        return None

    def _read_form_values(self) -> ConnectParams:
        return ConnectParams(
            endpoint=self.query_one("#endpoint", Input).value.strip(),
            security_mode=self.query_one("#security-mode", Select).value,
            security_policy=self.query_one("#security-policy", Select).value,
            authentication_mode=self.query_one("#auth-mode", Select).value,
            username=self.query_one("#username", Input).value.strip(),
            password=self.query_one("#password", Input).value,
            certificate_path=self.query_one("#certificate-path", Input).value.strip(),
            private_key_path=self.query_one("#private-key-path", Input).value.strip(),
        )

    def _format_connection_error(
        self,
        *,
        message: str,
        error_ref: str,
        params: ConnectParams,
    ) -> str:
        lower = message.lower()
        title = "Connection failed."
        hints: list[str] = []

        if "badcertificateuntrusted" in lower:
            title = "Server certificate is not trusted."
            hints.append("Trust the server certificate in your local PKI trust store, then retry.")
            hints.append(f"PKI path: {self._default_pki_root()}")
        elif any(token in lower for token in ("badsecuritycheck", "badcertificate", "security")):
            title = "Secure channel setup failed."
            hints.append("Verify server and client certificates are trusted on both sides.")
            hints.append("Confirm security mode/policy match one of the server endpoint offers.")
        elif any(token in lower for token in ("baduseraccessdenied", "identity token", "user")):
            title = "Authentication failed."
            hints.append("Verify username and password for the selected endpoint.")
            hints.append("Some servers require secure mode for username/password logins.")
        elif any(token in lower for token in ("timed out", "timeout", "refused", "winerror 10061")):
            title = "Server is unreachable."
            hints.append("Check endpoint host/port and ensure the OPC UA server is running.")
            hints.append(
                "Confirm endpoint starts with opc.tcp:// and is reachable from this machine."
            )
        elif "endpoint" in lower and any(
            token in lower for token in ("policy", "security", "mode")
        ):
            title = "Requested security settings are not offered by this endpoint."
            hints.append("Select a different mode/policy combination and retry.")

        if params.security_mode != SecurityMode.NONE:
            hints.append(
                "Secure mode is enabled: ensure client cert/key exist or allow auto-generation."
            )

        lines = [title, f"Details: {message}"]
        if hints:
            lines.append("Possible fixes:")
            lines.extend(f"- {hint}" for hint in hints)
        lines.append(f"Reference: {error_ref}")
        return "\n".join(lines)

    def _default_pki_root(self) -> str:
        return "~/.opcua-tui/pki"

    def _sanitize_error_message(self, message: str, endpoint: str) -> str:
        safe_endpoint = sanitize_endpoint(endpoint)
        return message.replace(endpoint, safe_endpoint)

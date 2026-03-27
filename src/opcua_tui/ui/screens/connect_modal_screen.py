from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from opcua_tui.app.messages import (
    ConnectFormUpdated,
    ConnectFormValidationFailed,
    ConnectModalClosed,
    ConnectRequested,
)
from opcua_tui.app.store import Store
from opcua_tui.domain.enums import AuthenticationMode, SecurityMode, SecurityPolicy
from opcua_tui.domain.models import AppState, ConnectParams, SessionInfo


class ConnectModalScreen(ModalScreen[SessionInfo | None]):
    CSS = """
    ConnectModalScreen {
        align: center middle;
    }

    #connect-dialog {
        width: 72;
        max-width: 90vw;
        height: auto;
        max-height: 90vh;
        background: $surface;
        border: round $accent;
    }

    #connect-body {
        padding: 1 2 0 2;
        height: auto;
        max-height: 1fr;
        overflow-y: auto;
    }

    #connect-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #connect-error {
        color: $error;
        min-height: 1;
        margin: 1 0;
    }

    .connect-row {
        height: auto;
        margin-bottom: 1;
    }

    .connect-field {
        width: 18;
        padding-top: 1;
    }

    #connect-actions {
        align-horizontal: right;
        height: auto;
        padding: 1 2;
        border-top: solid $accent-darken-1;
    }

    Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "submit", "Connect"),
    ]

    def __init__(self, store: Store) -> None:
        super().__init__()
        self.store = store
        self._suppress_form_events = False
        self._dismissed = False

    def compose(self) -> ComposeResult:
        with Container(id="connect-dialog"):
            with VerticalScroll(id="connect-body"):
                yield Static("Connect to OPC UA Server", id="connect-title")
                with Horizontal(classes="connect-row"):
                    yield Label("Endpoint", classes="connect-field")
                    yield Input(placeholder="opc.tcp://localhost:4840", id="endpoint")
                with Horizontal(classes="connect-row"):
                    yield Label("Security Mode", classes="connect-field")
                    yield Select(
                        options=[
                            ("None", SecurityMode.NONE.value),
                            ("Sign", SecurityMode.SIGN.value),
                            ("Sign and Encrypt", SecurityMode.SIGN_AND_ENCRYPT.value),
                        ],
                        id="security_mode",
                    )
                with Horizontal(classes="connect-row"):
                    yield Label("Security Policy", classes="connect-field")
                    yield Select(
                        options=[
                            ("None", SecurityPolicy.NONE.value),
                            ("Basic128Rsa15", SecurityPolicy.BASIC128RSA15.value),
                            ("Basic256", SecurityPolicy.BASIC256.value),
                            ("Basic256Sha256", SecurityPolicy.BASIC256SHA256.value),
                            ("Aes128Sha256RsaOaep", SecurityPolicy.AES128_SHA256_RSAOAEP.value),
                            ("Aes256Sha256RsaPss", SecurityPolicy.AES256_SHA256_RSAPSS.value),
                        ],
                        id="security_policy",
                    )
                with Horizontal(classes="connect-row"):
                    yield Label("Authentication", classes="connect-field")
                    yield Select(
                        options=[
                            ("Anonymous", AuthenticationMode.ANONYMOUS.value),
                            ("Username / Password", AuthenticationMode.USERNAME_PASSWORD.value),
                            ("Certificate", AuthenticationMode.CERTIFICATE.value),
                        ],
                        id="authentication_mode",
                    )
                with Horizontal(classes="connect-row"):
                    yield Label("Username", classes="connect-field")
                    yield Input(id="username")
                with Horizontal(classes="connect-row"):
                    yield Label("Password", classes="connect-field")
                    yield Input(password=True, id="password")
                with Horizontal(classes="connect-row"):
                    yield Label("Certificate Path", classes="connect-field")
                    yield Input(id="certificate_path")
                with Horizontal(classes="connect-row"):
                    yield Label("Private Key Path", classes="connect-field")
                    yield Input(id="private_key_path")
                yield Static("", id="connect-error")
                with Container(id="connect-actions"):
                    yield Button("Cancel", id="cancel")
                    yield Button("Connect", id="submit", variant="primary")

    async def on_mount(self) -> None:
        self.store.subscribe(self.on_state_changed)
        self.render_state(self.store.state)
        self.query_one("#endpoint", Input).focus()

    def on_state_changed(self, state: AppState) -> None:
        self.render_state(state)
        if (
            state.session.status == "connected"
            and state.session.session is not None
            and not self._dismissed
        ):
            self._dismissed = True
            self.dismiss(state.session.session)

    def render_state(self, state: AppState) -> None:
        endpoint_input = self.query_one("#endpoint", Input)
        security_mode = self.query_one("#security_mode", Select)
        security_policy = self.query_one("#security_policy", Select)
        authentication_mode = self.query_one("#authentication_mode", Select)
        username_input = self.query_one("#username", Input)
        password_input = self.query_one("#password", Input)
        certificate_path_input = self.query_one("#certificate_path", Input)
        private_key_path_input = self.query_one("#private_key_path", Input)
        error_widget = self.query_one("#connect-error", Static)
        submit_button = self.query_one("#submit", Button)

        params = state.connect_modal.params
        self._suppress_form_events = True
        try:
            if endpoint_input.value != params.endpoint:
                endpoint_input.value = params.endpoint
            if security_mode.value != params.security_mode.value:
                security_mode.value = params.security_mode.value
            if security_policy.value != params.security_policy.value:
                security_policy.value = params.security_policy.value
            if authentication_mode.value != params.authentication_mode.value:
                authentication_mode.value = params.authentication_mode.value
            if username_input.value != params.username:
                username_input.value = params.username
            if password_input.value != params.password:
                password_input.value = params.password
            if certificate_path_input.value != params.certificate_path:
                certificate_path_input.value = params.certificate_path
            if private_key_path_input.value != params.private_key_path:
                private_key_path_input.value = params.private_key_path
        finally:
            self._suppress_form_events = False

        auth_mode = params.authentication_mode
        username_input.disabled = auth_mode != AuthenticationMode.USERNAME_PASSWORD
        password_input.disabled = auth_mode != AuthenticationMode.USERNAME_PASSWORD
        certificate_path_input.disabled = auth_mode != AuthenticationMode.CERTIFICATE
        private_key_path_input.disabled = auth_mode != AuthenticationMode.CERTIFICATE
        submit_button.disabled = state.connect_modal.is_submitting or not params.endpoint.strip()
        error_widget.update(state.connect_modal.error or "")

    async def on_input_changed(self, _event: Input.Changed) -> None:
        if self._suppress_form_events:
            return
        await self.store.dispatch(ConnectFormUpdated(params=self._read_form_values()))

    async def on_select_changed(self, _event: Select.Changed) -> None:
        if self._suppress_form_events:
            return
        await self.store.dispatch(ConnectFormUpdated(params=self._read_form_values()))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            await self.action_cancel()
            return
        if event.button.id == "submit":
            await self._submit_form()

    async def action_cancel(self) -> None:
        if self.store.state.connect_modal.is_submitting:
            return
        await self.store.dispatch(ConnectModalClosed())
        self.dismiss(None)

    async def action_submit(self) -> None:
        await self._submit_form()

    async def _submit_form(self) -> None:
        params = self._read_form_values()
        validation_error = self._validate_params(params)
        if validation_error is not None:
            await self.store.dispatch(ConnectFormValidationFailed(error=validation_error))
            return

        await self.store.dispatch(ConnectRequested(params=params))

    def _validate_params(self, params: ConnectParams) -> str | None:
        endpoint = params.endpoint.strip()
        if not endpoint:
            return "Endpoint is required"
        if not endpoint.startswith("opc.tcp://"):
            return "Endpoint must start with opc.tcp://"
        return None

    def _read_form_values(self) -> ConnectParams:
        return ConnectParams(
            endpoint=self.query_one("#endpoint", Input).value.strip(),
            security_mode=SecurityMode(self.query_one("#security_mode", Select).value),
            security_policy=SecurityPolicy(self.query_one("#security_policy", Select).value),
            authentication_mode=AuthenticationMode(
                self.query_one("#authentication_mode", Select).value
            ),
            username=self.query_one("#username", Input).value,
            password=self.query_one("#password", Input).value,
            certificate_path=self.query_one("#certificate_path", Input).value,
            private_key_path=self.query_one("#private_key_path", Input).value,
        )

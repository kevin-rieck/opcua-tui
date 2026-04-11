from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

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
        layout: vertical;
        width: 52;
        max-width: 70vw;
        height: auto;
        background: $surface;
        border: round $accent;
    }

    #connect-body {
        layout: vertical;
        padding: 1 2;
        height: auto;
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

    def __init__(self, store: Store) -> None:
        super().__init__()
        self.store = store
        self._suppress_form_events = False
        self._dismissed = False

    def compose(self) -> ComposeResult:
        with Container(id="connect-dialog"):
            with Vertical(id="connect-body"):
                with Vertical(id="connect-copy"):
                    yield Static("Connect to OPC UA Server", id="connect-title")
                    yield Static(
                        "Insecure mode only for now.",
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
                    yield Static("Anonymous connection only for now.", classes="connect-note")
                with Vertical(id="connect-footer"):
                    yield Static("", id="connect-error")
            with Horizontal(id="connect-actions"):
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
        error_widget = self.query_one("#connect-error", Static)
        submit_button = self.query_one("#submit", Button)

        params = state.connect_modal.params
        self._suppress_form_events = True
        try:
            if endpoint_input.value != params.endpoint:
                endpoint_input.value = params.endpoint
        finally:
            self._suppress_form_events = False

        submit_button.disabled = state.connect_modal.is_submitting or not params.endpoint.strip()
        error_widget.update(state.connect_modal.error or "")

    async def on_input_changed(self, _event: Input.Changed) -> None:
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
            security_mode=SecurityMode.NONE,
            security_policy=SecurityPolicy.NONE,
            authentication_mode=AuthenticationMode.ANONYMOUS,
            username="",
            password="",
            certificate_path="",
            private_key_path="",
        )

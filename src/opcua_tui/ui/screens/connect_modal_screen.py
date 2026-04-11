from __future__ import annotations

import logging
import uuid

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from opcua_tui.application.ports.opcua_client import OpcUaClientPort
from opcua_tui.domain.enums import AuthenticationMode, SecurityMode, SecurityPolicy
from opcua_tui.domain.models import ConnectParams, SessionInfo


logger = logging.getLogger(__name__)


class ConnectModalScreen(ModalScreen[SessionInfo | None]):
    endpoint: reactive[str] = reactive("")
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
        self.endpoint = self._initial_params.endpoint
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
        error_widget = self.query_one("#connect-error", Static)
        submit_button = self.query_one("#submit", Button)
        cancel_button = self.query_one("#cancel", Button)

        self._suppress_form_events = True
        try:
            if endpoint_input.value != self.endpoint:
                endpoint_input.value = self.endpoint
        finally:
            self._suppress_form_events = False

        endpoint_input.disabled = self.is_submitting
        cancel_button.disabled = self.is_submitting
        submit_button.disabled = self.is_submitting or not self.endpoint.strip()
        submit_button.label = "Connecting..." if self.is_submitting else "Connect"
        error_widget.update(self.error_text)

    async def on_input_changed(self, _event: Input.Changed) -> None:
        if self._suppress_form_events:
            return
        self.endpoint = self.query_one("#endpoint", Input).value

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
            logger.exception(
                "OPC UA connect failed",
                extra={"endpoint": params.endpoint, "error_ref": error_ref},
            )
            self.error_text = f"{exc} (ref: {error_ref})"
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

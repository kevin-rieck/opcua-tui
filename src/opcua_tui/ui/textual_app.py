from __future__ import annotations

import asyncio
import logging
import os

from textual.app import App
from textual.binding import Binding

from opcua_tui.app.bootstrap import build_store
from opcua_tui.app.messages import ConnectionSucceeded, RootBrowseRequested
from opcua_tui.application.ports.opcua_client import OpcUaClientPort
from opcua_tui.domain.enums import AuthenticationMode, SecurityMode, SecurityPolicy
from opcua_tui.domain.models import ConnectParams, SessionInfo
from opcua_tui.infrastructure.opcua.stub_client import StubOpcUaClientAdapter
from opcua_tui.ui.screens.browser_screen import BrowserScreen
from opcua_tui.ui.screens.connect_modal_screen import ConnectModalScreen
from opcua_tui.ui.theme import OPC_MODERN_THEME

logger = logging.getLogger(__name__)


class OpcUaTuiApp(App[None]):
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]

    CSS = """
    Screen {
        layout: vertical;
        background: $background;
        color: $text;
    }

    Horizontal {
        height: 1fr;
    }

    Header {
        background: $panel;
        color: $text;
    }

    Footer {
        background: $footer-background;
        color: $footer-foreground;
    }
    """

    def __init__(self, *, opcua: OpcUaClientPort | None = None) -> None:
        super().__init__()
        self.opcua = opcua or StubOpcUaClientAdapter()
        self.store = build_store(opcua=self.opcua)
        self._browser_pushed = False

    async def on_mount(self) -> None:
        self.register_theme(OPC_MODERN_THEME)
        self.theme = OPC_MODERN_THEME.name
        await self.push_screen(
            ConnectModalScreen(
                opcua=self.opcua,
                initial_params=self._default_connect_params(),
            ),
            callback=self._on_connect_modal_closed,
        )

    def _default_connect_params(self) -> ConnectParams:
        return ConnectParams(
            endpoint=os.getenv("OPCUA_TUI_ENDPOINT", "opc.tcp://localhost:4840"),
            security_mode=SecurityMode.NONE,
            security_policy=SecurityPolicy.NONE,
            authentication_mode=AuthenticationMode.ANONYMOUS,
        )

    def _on_connect_modal_closed(self, result: SessionInfo | None) -> None:
        asyncio.create_task(self._handle_connect_modal_result(result))

    async def _handle_connect_modal_result(self, result: SessionInfo | None) -> None:
        if result is None:
            self.exit()
            return
        if self._browser_pushed:
            return
        self._browser_pushed = True
        await self.store.dispatch(ConnectionSucceeded(session=result))
        await self.push_screen(BrowserScreen(self.store))
        await self.store.dispatch(RootBrowseRequested())

    async def connect_and_open_browser(self, endpoint: str) -> None:
        params = ConnectParams(
            endpoint=endpoint,
            security_mode=SecurityMode.NONE,
            security_policy=SecurityPolicy.NONE,
            authentication_mode=AuthenticationMode.ANONYMOUS,
        )
        session = await self.opcua.connect(params)
        await self._handle_connect_modal_result(session)

    async def _disconnect_client(self) -> None:
        try:
            await self.opcua.disconnect()
        except Exception:
            logger.exception("Disconnect during app shutdown failed")

    async def action_quit(self) -> None:
        await self._disconnect_client()
        self.exit()

    async def _on_exit_app(self) -> None:
        await self._disconnect_client()
        await super()._on_exit_app()


def run() -> None:
    OpcUaTuiApp().run()

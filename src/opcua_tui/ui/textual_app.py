from __future__ import annotations

import asyncio
import os

from textual.app import App

from opcua_tui.app.bootstrap import build_store
from opcua_tui.app.messages import AppStarted, ConnectModalOpened, RootBrowseRequested
from opcua_tui.domain.enums import AuthenticationMode, SecurityMode, SecurityPolicy
from opcua_tui.domain.models import ConnectParams, SessionInfo
from opcua_tui.ui.screens.browser_screen import BrowserScreen
from opcua_tui.ui.screens.connect_modal_screen import ConnectModalScreen


class OpcUaTuiApp(App[None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    Horizontal {
        height: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.store = build_store()
        self._browser_pushed = False

    async def on_mount(self) -> None:
        await self.store.dispatch(AppStarted())
        await self.store.dispatch(ConnectModalOpened(params=self._default_connect_params()))
        await self.push_screen(
            ConnectModalScreen(self.store), callback=self._on_connect_modal_closed
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
        await self.push_screen(BrowserScreen(self.store))
        await self.store.dispatch(RootBrowseRequested())


def run() -> None:
    OpcUaTuiApp().run()

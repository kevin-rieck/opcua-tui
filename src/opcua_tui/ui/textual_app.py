from __future__ import annotations

import os

from textual.app import App

from opcua_tui.app.bootstrap import build_store
from opcua_tui.app.messages import AppStarted, ConnectRequested, RootBrowseRequested
from opcua_tui.domain.models import ConnectParams
from opcua_tui.ui.screens.browser_screen import BrowserScreen


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

    async def on_mount(self) -> None:
        endpoint = os.getenv("OPCUA_TUI_ENDPOINT", "opc.tcp://localhost:4840")
        await self.push_screen(BrowserScreen(self.store))
        await self.store.dispatch(AppStarted())
        await self.store.dispatch(ConnectRequested(ConnectParams(endpoint=endpoint)))
        await self.store.dispatch(RootBrowseRequested())


def run() -> None:
    OpcUaTuiApp().run()

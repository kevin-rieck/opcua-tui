from __future__ import annotations

import asyncio

from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header

from opcua_tui.app.messages import (
    NodeCollapsed,
    NodeExpanded,
    NodeExpandRequested,
    NodeSelected,
    NodeSubscribeRequested,
    NodeUnsubscribeRequested,
    NodeWriteRequested,
)
from opcua_tui.app.store import Store
from opcua_tui.domain.models import AppState
from opcua_tui.ui.screens.log_viewer_screen import LogViewerScreen
from opcua_tui.ui.widgets.address_tree import AddressTree
from opcua_tui.ui.widgets.node_details import NodeDetails
from opcua_tui.ui.widgets.status_bar import StatusBar
from opcua_tui.ui.widgets.subscription_panel import SubscriptionPanel
from opcua_tui.ui.widgets.watchlist_panel import WatchlistPanel
from opcua_tui.ui.widgets.write_value_panel import WriteValuePanel


class BrowserScreen(Screen):
    DEFAULT_CSS = """
    BrowserScreen > Horizontal {
        width: 1fr;
        height: 1fr;
    }

    #inspector-pane {
        width: 2fr;
        min-width: 30;
    }
    """

    BINDINGS = [
        ("ctrl+w", "focus_write_input", "Write Value"),
        ("ctrl+s", "toggle_subscription", "Sub Toggle"),
        ("ctrl+l", "show_logs", "Logs"),
    ]

    def __init__(self, store: Store) -> None:
        super().__init__()
        self.store = store
        self._last_rendered_state: AppState | None = None
        self._suppress_tree_events = False

    def compose(self):
        yield Header()
        with Horizontal():
            yield AddressTree(id="tree")
            with Vertical(id="inspector-pane"):
                yield NodeDetails(id="details")
                yield SubscriptionPanel(id="subscription-panel")
                yield WriteValuePanel(id="write-panel")
            yield WatchlistPanel(id="watchlist-panel")
        yield StatusBar(id="status")
        yield Footer()

    async def on_mount(self) -> None:
        self.store.subscribe(self.on_state_changed)
        self.render_state(self.store.state)

    def on_state_changed(self, state: AppState) -> None:
        self.call_from_thread(self.render_state, state) if False else self.render_state(state)

    def render_state(self, state: AppState) -> None:
        tree = self.query_one(AddressTree)
        details = self.query_one(NodeDetails)
        subscription_panel = self.query_one(SubscriptionPanel)
        write_panel = self.query_one(WriteValuePanel)
        watchlist = self.query_one(WatchlistPanel)
        status = self.query_one(StatusBar)
        last_browser = self._last_rendered_state.browser if self._last_rendered_state else None
        tree_changed = (
            self._last_rendered_state is None
            or state.browser.roots != last_browser.roots
            or state.browser.children_by_parent != last_browser.children_by_parent
            or state.browser.expanded != last_browser.expanded
            or set(state.subscriptions.items_by_node_id.keys())
            != set(self._last_rendered_state.subscriptions.items_by_node_id.keys())
        )
        selection_changed = (
            self._last_rendered_state is None
            or state.browser.selected_node_id != last_browser.selected_node_id
        )

        if tree_changed:
            self._suppress_tree_events = True
            try:
                subscribed_node_ids = set(state.subscriptions.items_by_node_id.keys())
                tree.replace_with_state(
                    roots=state.browser.roots,
                    children_by_parent=state.browser.children_by_parent,
                    expanded=state.browser.expanded,
                    subscribed_node_ids=subscribed_node_ids,
                )
            finally:
                self._suppress_tree_events = False

        if selection_changed and state.browser.selected_node_id:
            widget_node = tree.find_node_by_id(state.browser.selected_node_id)
            current = getattr(tree, "cursor_node", None)
            current_id = getattr(getattr(current, "data", None), "node_id", None)
            if widget_node is not None and current_id != state.browser.selected_node_id:
                self._suppress_tree_events = True
                try:
                    tree.select_node(widget_node)
                finally:
                    self._suppress_tree_events = False

        details.render_from_state(state.inspector)
        subscription_panel.render_from_state(state.inspector, state.subscriptions)
        write_panel.render_from_state(state.inspector)
        watchlist.render_from_state(state.subscriptions)
        if (
            self._last_rendered_state is not None
            and self._last_rendered_state.inspector.writing
            and not state.inspector.writing
            and not state.inspector.write_error
        ):
            write_panel.clear_input()
        status.render_status(
            state.ui.status_text,
            activities=list(state.ui.activities.values()),
        )
        self._last_rendered_state = state

    def action_focus_write_input(self) -> None:
        self.query_one(WriteValuePanel).focus_input()

    def action_show_logs(self) -> None:
        self.app.push_screen(LogViewerScreen())

    async def action_toggle_subscription(self) -> None:
        node_id = self._focused_tree_node_id()
        if not node_id:
            return

        inspector = self.store.state.inspector
        if inspector.loading or inspector.writing:
            return
        if inspector.attributes and inspector.attributes.node_class != "Variable":
            return

        subscriptions = self.store.state.subscriptions
        if node_id in subscriptions.subscribing or node_id in subscriptions.unsubscribing:
            return

        item = subscriptions.items_by_node_id.get(node_id)
        if item and item.active:
            await self.store.dispatch(NodeUnsubscribeRequested(node_id=node_id))
            return

        display_name = (
            inspector.attributes.display_name
            if inspector.attributes and inspector.attributes.display_name
            else node_id
        )
        await self.store.dispatch(
            NodeSubscribeRequested(node_id=node_id, display_name=display_name)
        )

    def _focused_tree_node_id(self) -> str | None:
        tree = self.query_one(AddressTree)
        cursor_node = getattr(tree, "cursor_node", None)
        data = getattr(cursor_node, "data", None)
        node_id = getattr(data, "node_id", None)
        if node_id in {"__root__", "__placeholder__"}:
            return None
        if isinstance(node_id, str):
            return node_id
        return self.store.state.browser.selected_node_id

    async def on_tree_node_selected(self, event) -> None:
        if self._suppress_tree_events:
            return
        data = event.node.data
        if not data or data.node_id in {"__root__", "__placeholder__"}:
            return
        if data.node_id == self.store.state.browser.selected_node_id:
            return
        await self.store.dispatch(NodeSelected(node_id=data.node_id))

    async def on_tree_node_expanded(self, event) -> None:
        if self._suppress_tree_events:
            return
        data = event.node.data
        if not data or data.node_id in {"__root__", "__placeholder__"}:
            return

        await self.store.dispatch(NodeExpanded(node_id=data.node_id))

        state = self.store.state
        already_loaded = data.node_id in state.browser.children_by_parent
        already_loading = data.node_id in state.browser.loading
        if data.has_children and not already_loaded and not already_loading:
            asyncio.create_task(self.store.dispatch(NodeExpandRequested(node_id=data.node_id)))
            # Yield once so the scheduled dispatch can start without blocking this handler.
            await asyncio.sleep(0)

    async def on_tree_node_collapsed(self, event) -> None:
        if self._suppress_tree_events:
            return
        data = event.node.data
        if not data or data.node_id in {"__root__", "__placeholder__"}:
            return
        await self.store.dispatch(NodeCollapsed(node_id=data.node_id))

    async def on_write_value_panel_submit_requested(
        self, message: WriteValuePanel.SubmitRequested
    ) -> None:
        value_text = message.value_text.strip()
        if not value_text:
            return

        inspector = self.store.state.inspector
        node_id = inspector.node_id
        if not node_id or inspector.loading or inspector.writing:
            return

        variant_hint = None
        if inspector.value and inspector.value.variant_type:
            variant_hint = inspector.value.variant_type
        elif inspector.attributes and inspector.attributes.data_type:
            variant_hint = inspector.attributes.data_type

        await self.store.dispatch(
            NodeWriteRequested(
                node_id=node_id,
                value_text=value_text,
                variant_hint=variant_hint,
            )
        )

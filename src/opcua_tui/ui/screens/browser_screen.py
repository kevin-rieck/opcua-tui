from __future__ import annotations

from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Header

from opcua_tui.app.messages import NodeCollapsed, NodeExpanded, NodeExpandRequested, NodeSelected
from opcua_tui.app.store import Store
from opcua_tui.domain.models import AppState
from opcua_tui.ui.widgets.address_tree import AddressTree
from opcua_tui.ui.widgets.node_details import NodeDetails
from opcua_tui.ui.widgets.status_bar import StatusBar


class BrowserScreen(Screen):
    BINDINGS = [
        ("q", "quit", "Quit"),
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
            yield NodeDetails(id="details")
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
        status = self.query_one(StatusBar)
        last_browser = self._last_rendered_state.browser if self._last_rendered_state else None
        tree_changed = (
            self._last_rendered_state is None
            or state.browser.roots != last_browser.roots
            or state.browser.children_by_parent != last_browser.children_by_parent
            or state.browser.expanded != last_browser.expanded
        )
        selection_changed = (
            self._last_rendered_state is None
            or state.browser.selected_node_id != last_browser.selected_node_id
        )

        if tree_changed:
            self._suppress_tree_events = True
            try:
                tree.replace_with_state(
                    roots=state.browser.roots,
                    children_by_parent=state.browser.children_by_parent,
                    expanded=state.browser.expanded,
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
        status.render_status(state.ui.status_text)
        self._last_rendered_state = state

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
            await self.store.dispatch(NodeExpandRequested(node_id=data.node_id))

    async def on_tree_node_collapsed(self, event) -> None:
        if self._suppress_tree_events:
            return
        data = event.node.data
        if not data or data.node_id in {"__root__", "__placeholder__"}:
            return
        await self.store.dispatch(NodeCollapsed(node_id=data.node_id))

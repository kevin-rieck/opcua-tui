import asyncio
from types import SimpleNamespace

from opcua_tui.app.messages import (
    NodeCollapsed,
    NodeExpanded,
    NodeExpandRequested,
    NodeSelected,
    NodeWriteRequested,
)
from opcua_tui.domain.models import AppState, InspectorState, NodeRef, UiState
from opcua_tui.ui.screens.browser_screen import BrowserScreen
from opcua_tui.ui.widgets.write_value_panel import WriteValuePanel


class FakeStore:
    def __init__(self, state: AppState) -> None:
        self.state = state
        self.dispatched: list[object] = []
        self.subscribers: list[object] = []

    def subscribe(self, fn) -> None:
        self.subscribers.append(fn)

    async def dispatch(self, message: object) -> None:
        self.dispatched.append(message)


class FakeTree:
    def __init__(self) -> None:
        self.replace_args = None
        self.selected = None
        self.replace_calls = 0

    def replace_with_state(self, roots, children_by_parent, expanded) -> None:
        self.replace_calls += 1
        self.replace_args = (roots, children_by_parent, expanded)

    def find_node_by_id(self, node_id: str):
        if node_id == "n1":
            return SimpleNamespace(id="widget-node")
        return None

    def select_node(self, node) -> None:
        self.selected = node


class FakeDetails:
    def __init__(self) -> None:
        self.rendered = None

    def render_from_state(self, inspector_state) -> None:
        self.rendered = inspector_state


class FakeStatus:
    def __init__(self) -> None:
        self.text = None

    def render_status(self, text: str) -> None:
        self.text = text


class FakeWritePanel:
    def __init__(self) -> None:
        self.rendered = None
        self.focused = False
        self.cleared = False

    def render_from_state(self, inspector_state) -> None:
        self.rendered = inspector_state

    def focus_input(self) -> None:
        self.focused = True

    def clear_input(self) -> None:
        self.cleared = True


def test_browser_screen_on_mount_subscribes_and_renders_initial_state(monkeypatch) -> None:
    state = AppState()
    store = FakeStore(state=state)
    screen = BrowserScreen(store)
    called: list[AppState] = []
    monkeypatch.setattr(screen, "render_state", lambda s: called.append(s))

    asyncio.run(screen.on_mount())

    assert len(store.subscribers) == 1
    assert called == [state]


def test_browser_screen_render_state_updates_widgets(monkeypatch) -> None:
    state = AppState(
        inspector=InspectorState(node_id="n1"),
        ui=UiState(status_text="ok"),
    )
    state.browser.roots = [NodeRef(node_id="n1", display_name="N1", node_class="Object")]
    state.browser.selected_node_id = "n1"
    store = FakeStore(state=state)
    screen = BrowserScreen(store)
    tree = FakeTree()
    details = FakeDetails()
    status = FakeStatus()
    write_panel = FakeWritePanel()

    def fake_query_one(widget_type):
        name = widget_type.__name__
        if name == "AddressTree":
            return tree
        if name == "NodeDetails":
            return details
        if name == "WriteValuePanel":
            return write_panel
        return status

    monkeypatch.setattr(screen, "query_one", fake_query_one)

    screen.render_state(state)

    assert tree.replace_args is not None
    assert tree.selected is not None
    assert details.rendered is state.inspector
    assert write_panel.rendered is state.inspector
    assert status.text == "ok"


def test_browser_screen_render_state_skips_tree_when_browser_state_unchanged(monkeypatch) -> None:
    state = AppState(
        inspector=InspectorState(node_id="n1"),
        ui=UiState(status_text="ok"),
    )
    state.browser.roots = [NodeRef(node_id="n1", display_name="N1", node_class="Object")]
    store = FakeStore(state=state)
    screen = BrowserScreen(store)
    tree = FakeTree()
    details = FakeDetails()
    status = FakeStatus()
    write_panel = FakeWritePanel()

    def fake_query_one(widget_type):
        name = widget_type.__name__
        if name == "AddressTree":
            return tree
        if name == "NodeDetails":
            return details
        if name == "WriteValuePanel":
            return write_panel
        return status

    monkeypatch.setattr(screen, "query_one", fake_query_one)

    screen.render_state(state)
    next_state = AppState(
        session=state.session,
        browser=state.browser,
        inspector=InspectorState(node_id="n1", loading=True),
        ui=UiState(status_text="inspecting"),
    )
    screen.render_state(next_state)

    assert tree.replace_calls == 1
    assert details.rendered is next_state.inspector
    assert write_panel.rendered is next_state.inspector
    assert status.text == "inspecting"


def test_browser_screen_render_state_clears_write_input_after_success(monkeypatch) -> None:
    previous = AppState(inspector=InspectorState(node_id="n1", writing=True))
    current = AppState(inspector=InspectorState(node_id="n1", writing=False))
    store = FakeStore(state=current)
    screen = BrowserScreen(store)
    tree = FakeTree()
    details = FakeDetails()
    status = FakeStatus()
    write_panel = FakeWritePanel()

    def fake_query_one(widget_type):
        name = widget_type.__name__
        if name == "AddressTree":
            return tree
        if name == "NodeDetails":
            return details
        if name == "WriteValuePanel":
            return write_panel
        return status

    monkeypatch.setattr(screen, "query_one", fake_query_one)
    screen._last_rendered_state = previous

    screen.render_state(current)

    assert write_panel.cleared is True


def test_browser_screen_node_selected_dispatches_public_message() -> None:
    state = AppState()
    store = FakeStore(state=state)
    screen = BrowserScreen(store)
    event = SimpleNamespace(node=SimpleNamespace(data=SimpleNamespace(node_id="n1")))

    asyncio.run(screen.on_tree_node_selected(event))

    assert len(store.dispatched) == 1
    assert isinstance(store.dispatched[0], NodeSelected)


def test_browser_screen_ignores_tree_events_while_rendering() -> None:
    state = AppState()
    store = FakeStore(state=state)
    screen = BrowserScreen(store)
    screen._suppress_tree_events = True
    event = SimpleNamespace(
        node=SimpleNamespace(data=SimpleNamespace(node_id="n1", has_children=True))
    )

    asyncio.run(screen.on_tree_node_selected(event))
    asyncio.run(screen.on_tree_node_expanded(event))
    asyncio.run(screen.on_tree_node_collapsed(event))

    assert store.dispatched == []


def test_browser_screen_node_selected_ignores_placeholder_and_root() -> None:
    state = AppState()
    store = FakeStore(state=state)
    screen = BrowserScreen(store)

    event_root = SimpleNamespace(node=SimpleNamespace(data=SimpleNamespace(node_id="__root__")))
    event_placeholder = SimpleNamespace(
        node=SimpleNamespace(data=SimpleNamespace(node_id="__placeholder__"))
    )

    asyncio.run(screen.on_tree_node_selected(event_root))
    asyncio.run(screen.on_tree_node_selected(event_placeholder))

    assert store.dispatched == []


def test_browser_screen_node_expanded_dispatches_only_when_load_needed() -> None:
    state = AppState()
    store = FakeStore(state=state)
    screen = BrowserScreen(store)

    should_load = SimpleNamespace(
        node=SimpleNamespace(data=SimpleNamespace(node_id="n1", has_children=True))
    )
    already_loaded = SimpleNamespace(
        node=SimpleNamespace(data=SimpleNamespace(node_id="n2", has_children=True))
    )
    state.browser.children_by_parent["n2"] = []

    asyncio.run(screen.on_tree_node_expanded(should_load))
    asyncio.run(screen.on_tree_node_expanded(already_loaded))

    assert len(store.dispatched) == 3
    assert isinstance(store.dispatched[0], NodeExpanded)
    assert isinstance(store.dispatched[1], NodeExpandRequested)
    assert isinstance(store.dispatched[2], NodeExpanded)


def test_browser_screen_node_collapsed_dispatches_public_message() -> None:
    state = AppState()
    store = FakeStore(state=state)
    screen = BrowserScreen(store)
    event = SimpleNamespace(node=SimpleNamespace(data=SimpleNamespace(node_id="n1")))

    asyncio.run(screen.on_tree_node_collapsed(event))

    assert len(store.dispatched) == 1
    assert isinstance(store.dispatched[0], NodeCollapsed)


def test_browser_screen_write_submit_dispatches_public_message() -> None:
    state = AppState(inspector=InspectorState(node_id="n1"))
    store = FakeStore(state=state)
    screen = BrowserScreen(store)
    message = WriteValuePanel.SubmitRequested(value_text="42")

    asyncio.run(screen.on_write_value_panel_submit_requested(message))

    assert len(store.dispatched) == 1
    assert isinstance(store.dispatched[0], NodeWriteRequested)
    assert store.dispatched[0].node_id == "n1"
    assert store.dispatched[0].value_text == "42"


def test_browser_screen_write_submit_ignores_invalid_state() -> None:
    state = AppState(inspector=InspectorState(node_id=None))
    store = FakeStore(state=state)
    screen = BrowserScreen(store)
    message = WriteValuePanel.SubmitRequested(value_text=" ")

    asyncio.run(screen.on_write_value_panel_submit_requested(message))

    assert store.dispatched == []


def test_browser_screen_focus_write_input_action(monkeypatch) -> None:
    state = AppState()
    store = FakeStore(state=state)
    screen = BrowserScreen(store)
    panel = FakeWritePanel()
    monkeypatch.setattr(screen, "query_one", lambda _t: panel)

    screen.action_focus_write_input()

    assert panel.focused is True

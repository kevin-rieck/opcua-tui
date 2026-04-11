from opcua_tui.app.messages import (
    ChildrenLoadFailed,
    ChildrenLoadStarted,
    ChildrenLoadSucceeded,
    ConnectFormUpdated,
    ConnectFormValidationFailed,
    ConnectModalClosed,
    ConnectModalOpened,
    ConnectRequested,
    ConnectionFailed,
    ConnectionStarted,
    ConnectionSucceeded,
    NodeAttributesLoaded,
    NodeCollapsed,
    NodeExpanded,
    NodeInspectionFailed,
    NodeInspectionStarted,
    NodeSelected,
    NodeWriteFailed,
    NodeWriteStarted,
    NodeWriteSucceeded,
    NodeValueLoaded,
    RootBrowseFailed,
    RootBrowseStarted,
    RootBrowseSucceeded,
)
from opcua_tui.app.reducer import reduce
from opcua_tui.domain.models import (
    AppState,
    ConnectParams,
    ConnectModalState,
    DataValueView,
    NodeAttributes,
    NodeRef,
    ServerInfo,
    SessionInfo,
)


def test_reduce_connect_modal_messages() -> None:
    state = AppState()
    params = ConnectParams(endpoint="opc.tcp://localhost:4840")

    opened = reduce(state, ConnectModalOpened(params=params))
    assert opened.connect_modal.is_open is True
    assert opened.connect_modal.params == params
    assert opened.connect_modal.is_submitting is False

    updated = reduce(
        opened, ConnectFormUpdated(params=ConnectParams(endpoint="opc.tcp://demo:4840"))
    )
    assert updated.connect_modal.params.endpoint == "opc.tcp://demo:4840"
    assert updated.connect_modal.error is None

    invalid = reduce(updated, ConnectFormValidationFailed(error="Endpoint is required"))
    assert invalid.connect_modal.error == "Endpoint is required"
    assert invalid.connect_modal.is_submitting is False

    closed = reduce(invalid, ConnectModalClosed())
    assert closed.connect_modal.is_open is False
    assert closed.connect_modal.error is None


def test_reduce_connection_messages() -> None:
    state = AppState(
        connect_modal=ConnectModalState(
            is_open=True,
            params=ConnectParams(endpoint="opc.tcp://localhost:4840"),
        )
    )
    params = ConnectParams(endpoint="opc.tcp://localhost:4840")
    session = SessionInfo(
        session_id="s1",
        endpoint=params.endpoint,
        server=ServerInfo(application_name="Server"),
    )

    after_connect_requested = reduce(state, ConnectRequested(params=params))
    assert state.session.status == "disconnected"
    assert after_connect_requested.session.status == "connecting"
    assert after_connect_requested.session.params == params
    assert after_connect_requested.connect_modal.is_submitting is True

    after_connection_started = reduce(state, ConnectionStarted(endpoint=params.endpoint))
    assert after_connection_started.session.status == "connecting"
    assert "Connecting to" in after_connection_started.ui.status_text
    assert after_connection_started.connect_modal.is_submitting is True

    after_connection_succeeded = reduce(state, ConnectionSucceeded(session=session))
    assert after_connection_succeeded.session.status == "connected"
    assert after_connection_succeeded.session.session == session
    assert after_connection_succeeded.connect_modal.is_open is False
    assert after_connection_succeeded.connect_modal.is_submitting is False
    assert after_connection_succeeded.browser.roots == []
    assert after_connection_succeeded.inspector.node_id is None

    after_connection_failed = reduce(
        state, ConnectionFailed(endpoint=params.endpoint, error="boom")
    )
    assert after_connection_failed.session.status == "error"
    assert after_connection_failed.session.error == "boom"
    assert after_connection_failed.connect_modal.is_open is True
    assert after_connection_failed.connect_modal.is_submitting is False
    assert after_connection_failed.connect_modal.error == "boom"


def test_reduce_root_browse_messages() -> None:
    state = AppState()
    roots = [
        NodeRef(node_id="i=85", display_name="Objects", node_class="Object", has_children=True)
    ]

    after_started = reduce(state, RootBrowseStarted())
    assert "__root__" in after_started.browser.loading

    after_succeeded = reduce(after_started, RootBrowseSucceeded(nodes=roots))
    assert "__root__" not in after_succeeded.browser.loading
    assert after_succeeded.browser.roots == roots

    after_failed = reduce(after_started, RootBrowseFailed(error="denied"))
    assert "__root__" not in after_failed.browser.loading
    assert "Failed to load root nodes" in after_failed.ui.status_text


def test_reduce_children_load_messages() -> None:
    state = AppState()
    node_id = "i=85"
    children = [
        NodeRef(
            node_id="ns=2;s=Machine", display_name="Machine", node_class="Object", has_children=True
        )
    ]

    after_started = reduce(state, ChildrenLoadStarted(node_id=node_id))
    assert node_id in after_started.browser.loading

    after_succeeded = reduce(
        after_started,
        ChildrenLoadSucceeded(parent_node_id=node_id, children=children),
    )
    assert node_id not in after_succeeded.browser.loading
    assert after_succeeded.browser.children_by_parent[node_id] == children
    assert node_id not in after_succeeded.browser.expanded

    after_failed = reduce(
        after_started,
        ChildrenLoadFailed(parent_node_id=node_id, error="network"),
    )
    assert node_id not in after_failed.browser.loading
    assert "Failed to load children" in after_failed.ui.status_text


def test_reduce_children_load_success_does_not_reexpand_collapsed_node() -> None:
    state = AppState()
    node_id = "i=85"
    state.browser.expanded.add(node_id)
    state.browser.loading.add(node_id)

    collapsed = reduce(state, NodeCollapsed(node_id=node_id))
    assert node_id not in collapsed.browser.expanded

    children = [NodeRef(node_id="ns=2;s=Machine", display_name="Machine", node_class="Object")]
    after_succeeded = reduce(
        collapsed,
        ChildrenLoadSucceeded(parent_node_id=node_id, children=children),
    )

    assert node_id not in after_succeeded.browser.expanded


def test_reduce_node_expand_and_collapse_messages() -> None:
    state = AppState()
    node_id = "i=85"

    after_expanded = reduce(state, NodeExpanded(node_id=node_id))
    assert node_id in after_expanded.browser.expanded

    after_collapsed = reduce(after_expanded, NodeCollapsed(node_id=node_id))
    assert node_id not in after_collapsed.browser.expanded


def test_reduce_node_selection_and_inspection_messages() -> None:
    state = AppState()
    node_id = "ns=2;s=Temperature"
    attrs = NodeAttributes(
        node_id=node_id,
        display_name="Temperature",
        browse_name="Temperature",
        node_class="Variable",
    )
    value = DataValueView(node_id=node_id, value=42.3, variant_type="float", status_code="Good")

    after_selected = reduce(state, NodeSelected(node_id=node_id))
    assert after_selected.browser.selected_node_id == node_id
    assert after_selected.inspector.node_id == node_id
    assert after_selected.inspector.loading is True

    after_inspection_started = reduce(state, NodeInspectionStarted(node_id=node_id))
    assert after_inspection_started.inspector.node_id == node_id
    assert after_inspection_started.inspector.loading is True

    after_attrs_loaded = reduce(after_selected, NodeAttributesLoaded(attributes=attrs))
    assert after_attrs_loaded.inspector.attributes == attrs

    after_value_loaded = reduce(after_attrs_loaded, NodeValueLoaded(value=value))
    assert after_value_loaded.inspector.value == value
    assert after_value_loaded.inspector.loading is False

    after_failed = reduce(after_selected, NodeInspectionFailed(node_id=node_id, error="bad read"))
    assert after_failed.inspector.loading is False
    assert after_failed.inspector.error == "bad read"


def test_reduce_node_write_messages() -> None:
    node_id = "ns=2;s=Temperature"
    state = AppState()
    state.inspector.node_id = node_id

    after_write_started = reduce(state, NodeWriteStarted(node_id=node_id))
    assert after_write_started.inspector.writing is True
    assert after_write_started.inspector.write_error is None

    after_write_failed = reduce(
        after_write_started, NodeWriteFailed(node_id=node_id, error="denied")
    )
    assert after_write_failed.inspector.writing is False
    assert after_write_failed.inspector.write_error == "denied"
    assert "Write failed" in after_write_failed.ui.status_text

    after_write_succeeded = reduce(after_write_failed, NodeWriteSucceeded(node_id=node_id))
    assert after_write_succeeded.inspector.writing is False
    assert after_write_succeeded.inspector.write_error is None
    assert "Wrote value" in after_write_succeeded.ui.status_text


def test_reduce_unknown_message_keeps_state_by_value() -> None:
    state = AppState()
    next_state = reduce(state, object())

    assert next_state is not state
    assert next_state.ui.status_text == state.ui.status_text
    assert next_state.browser.roots == state.browser.roots


def test_reduce_failure_status_includes_error_ref_when_present() -> None:
    state = AppState()
    next_state = reduce(state, RootBrowseFailed(error="denied", error_ref="abc12345"))

    assert "ref: abc12345" in next_state.ui.status_text


def test_reduce_connection_success_clears_stale_browser_and_inspector_state() -> None:
    state = AppState(
        connect_modal=ConnectModalState(
            is_open=True,
            params=ConnectParams(endpoint="opc.tcp://localhost:4840"),
        )
    )
    state.browser.roots = [NodeRef(node_id="i=85", display_name="Objects", node_class="Object")]
    state.browser.children_by_parent["i=85"] = []
    state.browser.expanded.add("i=85")
    state.browser.selected_node_id = "i=85"
    state.inspector.node_id = "i=85"
    state.inspector.loading = True

    session = SessionInfo(
        session_id="s1",
        endpoint="opc.tcp://localhost:4840",
        server=ServerInfo(application_name="Server"),
    )
    next_state = reduce(state, ConnectionSucceeded(session=session))

    assert next_state.browser.roots == []
    assert next_state.browser.children_by_parent == {}
    assert next_state.browser.expanded == set()
    assert next_state.browser.selected_node_id is None
    assert next_state.inspector.node_id is None
    assert next_state.inspector.loading is False

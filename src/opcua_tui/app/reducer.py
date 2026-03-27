from __future__ import annotations

from copy import deepcopy

from opcua_tui.app.messages import (
    ChildrenLoadFailed,
    ChildrenLoadStarted,
    ChildrenLoadSucceeded,
    ConnectRequested,
    ConnectionFailed,
    ConnectionStarted,
    ConnectionSucceeded,
    NodeAttributesLoaded,
    NodeCollapsed,
    NodeExpanded,
    NodeExpandRequested,
    NodeInspectionFailed,
    NodeInspectionStarted,
    NodeSelected,
    NodeValueLoaded,
    RootBrowseFailed,
    RootBrowseStarted,
    RootBrowseSucceeded,
)
from opcua_tui.domain.models import AppState


def _format_error_with_ref(error: str, error_ref: str | None) -> str:
    if not error_ref:
        return error
    return f"{error} (ref: {error_ref})"


def reduce(state: AppState, message: object) -> AppState:
    next_state = deepcopy(state)

    match message:
        case ConnectRequested(params=params):
            next_state.session.params = params
            next_state.session.status = "connecting"
            next_state.session.error = None
            next_state.ui.status_text = f"Connecting to {params.endpoint}"

        case ConnectionStarted(endpoint=endpoint):
            next_state.session.status = "connecting"
            next_state.ui.status_text = f"Connecting to {endpoint}"

        case ConnectionSucceeded(session=session):
            next_state.session.status = "connected"
            next_state.session.session = session
            next_state.session.error = None
            next_state.ui.status_text = f"Connected to {session.endpoint}"

        case ConnectionFailed(endpoint=endpoint, error=error, error_ref=error_ref):
            next_state.session.status = "error"
            next_state.session.error = error
            next_state.ui.status_text = (
                f"Connection failed for {endpoint}: {_format_error_with_ref(error, error_ref)}"
            )

        case RootBrowseStarted():
            next_state.browser.loading.add("__root__")
            next_state.ui.status_text = "Loading root nodes"

        case RootBrowseSucceeded(nodes=nodes):
            next_state.browser.loading.discard("__root__")
            next_state.browser.roots = nodes
            next_state.ui.status_text = f"Loaded {len(nodes)} root nodes"

        case RootBrowseFailed(error=error, error_ref=error_ref):
            next_state.browser.loading.discard("__root__")
            next_state.ui.status_text = (
                f"Failed to load root nodes: {_format_error_with_ref(error, error_ref)}"
            )

        case NodeExpandRequested(node_id=node_id):
            next_state.browser.expanded.add(node_id)

        case NodeExpanded(node_id=node_id):
            next_state.browser.expanded.add(node_id)

        case NodeCollapsed(node_id=node_id):
            next_state.browser.expanded.discard(node_id)

        case ChildrenLoadStarted(node_id=node_id):
            next_state.browser.loading.add(node_id)
            next_state.ui.status_text = f"Loading children for {node_id}"

        case ChildrenLoadSucceeded(parent_node_id=parent_node_id, children=children):
            next_state.browser.loading.discard(parent_node_id)
            next_state.browser.children_by_parent[parent_node_id] = children
            next_state.ui.status_text = f"Loaded {len(children)} children for {parent_node_id}"

        case ChildrenLoadFailed(parent_node_id=parent_node_id, error=error, error_ref=error_ref):
            next_state.browser.loading.discard(parent_node_id)
            next_state.browser.expanded.discard(parent_node_id)
            next_state.ui.status_text = (
                f"Failed to load children for {parent_node_id}: "
                f"{_format_error_with_ref(error, error_ref)}"
            )

        case NodeSelected(node_id=node_id):
            next_state.browser.selected_node_id = node_id
            next_state.inspector.node_id = node_id
            next_state.inspector.loading = True
            next_state.inspector.error = None
            next_state.ui.status_text = f"Selected {node_id}"

        case NodeInspectionStarted(node_id=node_id):
            next_state.inspector.node_id = node_id
            next_state.inspector.loading = True
            next_state.inspector.error = None
            next_state.ui.status_text = f"Inspecting {node_id}"

        case NodeAttributesLoaded(attributes=attributes):
            next_state.inspector.attributes = attributes

        case NodeValueLoaded(value=value):
            next_state.inspector.value = value
            next_state.inspector.loading = False
            next_state.inspector.error = None
            next_state.ui.status_text = f"Loaded value for {value.node_id}"

        case NodeInspectionFailed(node_id=node_id, error=error, error_ref=error_ref):
            next_state.inspector.loading = False
            next_state.inspector.error = error
            next_state.ui.status_text = (
                f"Inspection failed for {node_id}: {_format_error_with_ref(error, error_ref)}"
            )

    return next_state

from __future__ import annotations

from copy import deepcopy

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
    NodeExpandRequested,
    NodeInspectionFailed,
    NodeInspectionStarted,
    NodeSubscribeFailed,
    NodeSubscribeStarted,
    NodeSubscribeSucceeded,
    NodeSubscriptionValueReceived,
    NodeSelected,
    NodeUnsubscribeFailed,
    NodeUnsubscribeStarted,
    NodeUnsubscribeSucceeded,
    NodeWriteFailed,
    NodeWriteStarted,
    NodeWriteSucceeded,
    NodeValueLoaded,
    RootBrowseFailed,
    RootBrowseStarted,
    RootBrowseSucceeded,
)
from opcua_tui.domain.endpoint import sanitize_endpoint
from opcua_tui.domain.models import (
    AppState,
    BrowserState,
    InspectorState,
    SubscriptionItemState,
    SubscriptionsState,
)


def _format_error_with_ref(error: str, error_ref: str | None) -> str:
    if not error_ref:
        return error
    return f"{error} (ref: {error_ref})"


def reduce(state: AppState, message: object) -> AppState:
    next_state = deepcopy(state)

    match message:
        case ConnectModalOpened(params=params):
            next_state.connect_modal.is_open = True
            next_state.connect_modal.params = params
            next_state.connect_modal.is_submitting = False
            next_state.connect_modal.error = None
            next_state.ui.status_text = "Ready to connect"

        case ConnectModalClosed():
            next_state.connect_modal.is_open = False
            next_state.connect_modal.is_submitting = False
            next_state.connect_modal.error = None

        case ConnectFormUpdated(params=params):
            next_state.connect_modal.params = params
            next_state.connect_modal.error = None

        case ConnectFormValidationFailed(error=error):
            next_state.connect_modal.is_submitting = False
            next_state.connect_modal.error = error
            next_state.ui.status_text = error

        case ConnectRequested(params=params):
            next_state.session.params = params
            next_state.session.status = "connecting"
            next_state.session.session = None
            next_state.session.error = None
            next_state.connect_modal.is_open = True
            next_state.connect_modal.params = params
            next_state.connect_modal.is_submitting = True
            next_state.connect_modal.error = None
            next_state.ui.status_text = f"Connecting to {sanitize_endpoint(params.endpoint)}"

        case ConnectionStarted(endpoint=endpoint):
            next_state.session.status = "connecting"
            next_state.connect_modal.is_submitting = True
            next_state.ui.status_text = f"Connecting to {endpoint}"

        case ConnectionSucceeded(session=session):
            next_state.session.status = "connected"
            next_state.session.session = session
            next_state.session.error = None
            next_state.browser = BrowserState()
            next_state.inspector = InspectorState()
            next_state.subscriptions = SubscriptionsState()
            next_state.connect_modal.is_open = False
            next_state.connect_modal.is_submitting = False
            next_state.connect_modal.error = None
            next_state.ui.status_text = f"Connected to {sanitize_endpoint(session.endpoint)}"

        case ConnectionFailed(endpoint=endpoint, error=error, error_ref=error_ref):
            next_state.session.status = "error"
            next_state.session.session = None
            next_state.session.error = error
            next_state.connect_modal.is_open = True
            next_state.connect_modal.is_submitting = False
            next_state.connect_modal.error = _format_error_with_ref(error, error_ref)
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
            next_state.inspector.writing = False
            next_state.inspector.attributes = None
            next_state.inspector.value = None
            next_state.inspector.error = None
            next_state.inspector.write_error = None
            next_state.ui.status_text = f"Selected {node_id}"

        case NodeInspectionStarted(node_id=node_id):
            next_state.inspector.node_id = node_id
            next_state.inspector.loading = True
            next_state.inspector.writing = False
            next_state.inspector.attributes = None
            next_state.inspector.value = None
            next_state.inspector.error = None
            next_state.inspector.write_error = None
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

        case NodeWriteStarted(node_id=node_id):
            next_state.inspector.writing = True
            next_state.inspector.write_error = None
            next_state.ui.status_text = f"Writing value for {node_id}"

        case NodeWriteSucceeded(node_id=node_id):
            next_state.inspector.writing = False
            next_state.inspector.write_error = None
            next_state.ui.status_text = f"Wrote value for {node_id}"

        case NodeWriteFailed(node_id=node_id, error=error, error_ref=error_ref):
            next_state.inspector.writing = False
            next_state.inspector.write_error = _format_error_with_ref(error, error_ref)
            next_state.ui.status_text = (
                f"Write failed for {node_id}: {_format_error_with_ref(error, error_ref)}"
            )

        case NodeSubscribeStarted(node_id=node_id):
            next_state.subscriptions.subscribing.add(node_id)
            item = next_state.subscriptions.items_by_node_id.get(node_id)
            if item is not None:
                item.error = None
            next_state.ui.status_text = f"Subscribing to {node_id}"

        case NodeSubscribeSucceeded(node_id=node_id, display_name=display_name):
            next_state.subscriptions.subscribing.discard(node_id)
            item = next_state.subscriptions.items_by_node_id.get(node_id)
            if item is None:
                item = SubscriptionItemState(node_id=node_id, display_name=display_name)
            item.display_name = display_name
            item.active = True
            item.error = None
            next_state.subscriptions.items_by_node_id[node_id] = item
            next_state.ui.status_text = f"Subscribed to {node_id}"

        case NodeSubscribeFailed(node_id=node_id, error=error, error_ref=error_ref):
            next_state.subscriptions.subscribing.discard(node_id)
            item = next_state.subscriptions.items_by_node_id.get(node_id)
            if item is not None:
                item.error = _format_error_with_ref(error, error_ref)
                item.active = False
            next_state.ui.status_text = (
                f"Subscribe failed for {node_id}: {_format_error_with_ref(error, error_ref)}"
            )

        case NodeUnsubscribeStarted(node_id=node_id):
            next_state.subscriptions.unsubscribing.add(node_id)
            next_state.ui.status_text = f"Unsubscribing from {node_id}"

        case NodeUnsubscribeSucceeded(node_id=node_id):
            next_state.subscriptions.subscribing.discard(node_id)
            next_state.subscriptions.unsubscribing.discard(node_id)
            next_state.subscriptions.items_by_node_id.pop(node_id, None)
            next_state.ui.status_text = f"Unsubscribed from {node_id}"

        case NodeUnsubscribeFailed(node_id=node_id, error=error, error_ref=error_ref):
            next_state.subscriptions.unsubscribing.discard(node_id)
            item = next_state.subscriptions.items_by_node_id.get(node_id)
            if item is not None:
                item.error = _format_error_with_ref(error, error_ref)
            next_state.ui.status_text = (
                f"Unsubscribe failed for {node_id}: {_format_error_with_ref(error, error_ref)}"
            )

        case NodeSubscriptionValueReceived(update=update):
            item = next_state.subscriptions.items_by_node_id.get(update.node_id)
            if item is None:
                item = SubscriptionItemState(
                    node_id=update.node_id,
                    display_name=update.node_id,
                )
            item.active = True
            item.last_value = update.rendered_value
            item.variant_type = update.variant_type
            item.status_code = update.status_code
            item.source_timestamp = update.source_timestamp
            item.update_count += 1
            item.error = None
            next_state.subscriptions.items_by_node_id[update.node_id] = item

    return next_state

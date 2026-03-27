from dataclasses import FrozenInstanceError

import pytest

from opcua_tui.app.messages import (
    AppStarted,
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
    Message,
    NodeAttributesLoaded,
    NodeCollapsed,
    NodeExpanded,
    NodeExpandRequested,
    NodeInspectionFailed,
    NodeInspectionStarted,
    NodeSelected,
    NodeValueLoaded,
    RootBrowseFailed,
    RootBrowseRequested,
    RootBrowseStarted,
    RootBrowseSucceeded,
)
from opcua_tui.domain.models import (
    ConnectParams,
    DataValueView,
    NodeAttributes,
    NodeRef,
    ServerInfo,
    SessionInfo,
)


def test_all_messages_inherit_base_message() -> None:
    node = NodeRef(node_id="n1", display_name="N1", node_class="Object")
    attrs = NodeAttributes(node_id="n1", display_name="N1", browse_name="N1", node_class="Object")
    value = DataValueView(node_id="n1", value=1, variant_type="int", status_code="Good")
    session = SessionInfo(
        session_id="s1",
        endpoint="opc.tcp://localhost:4840",
        server=ServerInfo(application_name="Server"),
    )
    instances = [
        AppStarted(),
        ConnectModalOpened(params=ConnectParams(endpoint="opc.tcp://localhost:4840")),
        ConnectModalClosed(),
        ConnectFormUpdated(params=ConnectParams(endpoint="opc.tcp://localhost:4840")),
        ConnectFormValidationFailed(error="Endpoint is required"),
        ConnectRequested(params=ConnectParams(endpoint="opc.tcp://localhost:4840")),
        ConnectionStarted(endpoint="opc.tcp://localhost:4840"),
        ConnectionSucceeded(session=session),
        ConnectionFailed(endpoint="opc.tcp://localhost:4840", error="x"),
        RootBrowseRequested(),
        RootBrowseStarted(),
        RootBrowseSucceeded(nodes=[node]),
        RootBrowseFailed(error="x"),
        NodeExpanded(node_id="n1"),
        NodeCollapsed(node_id="n1"),
        NodeExpandRequested(node_id="n1"),
        ChildrenLoadStarted(node_id="n1"),
        ChildrenLoadSucceeded(parent_node_id="n1", children=[node]),
        ChildrenLoadFailed(parent_node_id="n1", error="x"),
        NodeSelected(node_id="n1"),
        NodeInspectionStarted(node_id="n1"),
        NodeAttributesLoaded(attributes=attrs),
        NodeValueLoaded(value=value),
        NodeInspectionFailed(node_id="n1", error="x"),
    ]

    assert all(isinstance(item, Message) for item in instances)


def test_message_dataclasses_compare_by_value() -> None:
    left = ConnectRequested(params=ConnectParams(endpoint="opc.tcp://localhost:4840"))
    right = ConnectRequested(params=ConnectParams(endpoint="opc.tcp://localhost:4840"))
    assert left == right


def test_messages_are_immutable() -> None:
    message = ConnectionFailed(endpoint="opc.tcp://localhost:4840", error="initial")
    with pytest.raises(FrozenInstanceError):
        message.error = "updated"

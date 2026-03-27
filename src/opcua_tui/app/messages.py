from __future__ import annotations

from dataclasses import dataclass

from opcua_tui.domain.models import (
    ConnectParams,
    DataValueView,
    NodeAttributes,
    NodeRef,
    SessionInfo,
)


class Message:
    pass


@dataclass(slots=True, frozen=True)
class AppStarted(Message):
    pass


@dataclass(slots=True, frozen=True)
class ConnectModalOpened(Message):
    params: ConnectParams


@dataclass(slots=True, frozen=True)
class ConnectModalClosed(Message):
    pass


@dataclass(slots=True, frozen=True)
class ConnectFormUpdated(Message):
    params: ConnectParams


@dataclass(slots=True, frozen=True)
class ConnectFormValidationFailed(Message):
    error: str


@dataclass(slots=True, frozen=True)
class ConnectRequested(Message):
    params: ConnectParams


@dataclass(slots=True, frozen=True)
class ConnectionStarted(Message):
    endpoint: str


@dataclass(slots=True, frozen=True)
class ConnectionSucceeded(Message):
    session: SessionInfo


@dataclass(slots=True, frozen=True)
class ConnectionFailed(Message):
    endpoint: str
    error: str
    error_ref: str | None = None


@dataclass(slots=True, frozen=True)
class RootBrowseRequested(Message):
    pass


@dataclass(slots=True, frozen=True)
class RootBrowseStarted(Message):
    pass


@dataclass(slots=True, frozen=True)
class RootBrowseSucceeded(Message):
    nodes: list[NodeRef]


@dataclass(slots=True, frozen=True)
class RootBrowseFailed(Message):
    error: str
    error_ref: str | None = None


@dataclass(slots=True, frozen=True)
class NodeExpandRequested(Message):
    node_id: str


@dataclass(slots=True, frozen=True)
class NodeExpanded(Message):
    node_id: str


@dataclass(slots=True, frozen=True)
class NodeCollapsed(Message):
    node_id: str


@dataclass(slots=True, frozen=True)
class ChildrenLoadStarted(Message):
    node_id: str


@dataclass(slots=True, frozen=True)
class ChildrenLoadSucceeded(Message):
    parent_node_id: str
    children: list[NodeRef]


@dataclass(slots=True, frozen=True)
class ChildrenLoadFailed(Message):
    parent_node_id: str
    error: str
    error_ref: str | None = None


@dataclass(slots=True, frozen=True)
class NodeSelected(Message):
    node_id: str


@dataclass(slots=True, frozen=True)
class NodeInspectionStarted(Message):
    node_id: str


@dataclass(slots=True, frozen=True)
class NodeAttributesLoaded(Message):
    attributes: NodeAttributes


@dataclass(slots=True, frozen=True)
class NodeValueLoaded(Message):
    value: DataValueView


@dataclass(slots=True, frozen=True)
class NodeInspectionFailed(Message):
    node_id: str
    error: str
    error_ref: str | None = None

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class ConnectParams:
    endpoint: str


@dataclass(slots=True, frozen=True)
class ServerInfo:
    application_name: str


@dataclass(slots=True, frozen=True)
class SessionInfo:
    session_id: str
    endpoint: str
    server: ServerInfo


@dataclass(slots=True, frozen=True)
class NodeRef:
    node_id: str
    display_name: str
    node_class: str
    has_children: bool = False


@dataclass(slots=True, frozen=True)
class NodeAttributes:
    node_id: str
    display_name: str
    browse_name: str
    node_class: str
    description: str | None = None
    data_type: str | None = None
    access_level: str | None = None


@dataclass(slots=True, frozen=True)
class DataValueView:
    node_id: str
    value: Any
    variant_type: str | None
    status_code: str


@dataclass(slots=True)
class SessionState:
    status: str = "disconnected"
    params: ConnectParams | None = None
    session: SessionInfo | None = None
    error: str | None = None


@dataclass(slots=True)
class BrowserState:
    roots: list[NodeRef] = field(default_factory=list)
    children_by_parent: dict[str, list[NodeRef]] = field(default_factory=dict)
    expanded: set[str] = field(default_factory=set)
    loading: set[str] = field(default_factory=set)
    selected_node_id: str | None = None


@dataclass(slots=True)
class InspectorState:
    loading: bool = False
    node_id: str | None = None
    attributes: NodeAttributes | None = None
    value: DataValueView | None = None
    error: str | None = None


@dataclass(slots=True)
class UiState:
    status_text: str = "Ready"


@dataclass(slots=True)
class AppState:
    session: SessionState = field(default_factory=SessionState)
    browser: BrowserState = field(default_factory=BrowserState)
    inspector: InspectorState = field(default_factory=InspectorState)
    ui: UiState = field(default_factory=UiState)

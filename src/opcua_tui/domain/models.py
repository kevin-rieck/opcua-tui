from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from opcua_tui.domain.enums import AuthenticationMode, SecurityMode, SecurityPolicy


@dataclass(slots=True, frozen=True)
class ConnectParams:
    endpoint: str
    security_mode: SecurityMode = SecurityMode.NONE
    security_policy: SecurityPolicy = SecurityPolicy.NONE
    authentication_mode: AuthenticationMode = AuthenticationMode.ANONYMOUS
    username: str = ""
    password: str = ""
    certificate_path: str = ""
    private_key_path: str = ""


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


@dataclass(slots=True, frozen=True)
class SubscriptionValueUpdate:
    node_id: str
    value: Any
    rendered_value: str
    variant_type: str | None
    status_code: str
    source_timestamp: datetime | None = None
    server_timestamp: datetime | None = None


@dataclass(slots=True)
class SubscriptionItemState:
    node_id: str
    display_name: str
    active: bool = False
    last_value: str | None = None
    variant_type: str | None = None
    status_code: str | None = None
    source_timestamp: datetime | None = None
    update_count: int = 0
    error: str | None = None


@dataclass(slots=True)
class SubscriptionsState:
    items_by_node_id: dict[str, SubscriptionItemState] = field(default_factory=dict)
    subscribing: set[str] = field(default_factory=set)
    unsubscribing: set[str] = field(default_factory=set)


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
    writing: bool = False
    node_id: str | None = None
    attributes: NodeAttributes | None = None
    value: DataValueView | None = None
    error: str | None = None
    write_error: str | None = None


@dataclass(slots=True)
class UiState:
    status_text: str = "Ready"


@dataclass(slots=True)
class ConnectModalState:
    is_open: bool = False
    params: ConnectParams = field(default_factory=lambda: ConnectParams(endpoint=""))
    is_submitting: bool = False
    error: str | None = None


@dataclass(slots=True)
class AppState:
    session: SessionState = field(default_factory=SessionState)
    browser: BrowserState = field(default_factory=BrowserState)
    inspector: InspectorState = field(default_factory=InspectorState)
    subscriptions: SubscriptionsState = field(default_factory=SubscriptionsState)
    ui: UiState = field(default_factory=UiState)
    connect_modal: ConnectModalState = field(default_factory=ConnectModalState)

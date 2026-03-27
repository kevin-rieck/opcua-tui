from __future__ import annotations

from typing import Protocol

from opcua_tui.domain.models import (
    ConnectParams,
    DataValueView,
    NodeAttributes,
    NodeRef,
    SessionInfo,
)


class OpcUaClientPort(Protocol):
    async def connect(self, params: ConnectParams) -> SessionInfo: ...
    async def disconnect(self) -> None: ...
    async def browse_children(self, node_id: str | None) -> list[NodeRef]: ...
    async def read_attributes(self, node_id: str) -> NodeAttributes: ...
    async def read_value(self, node_id: str) -> DataValueView: ...

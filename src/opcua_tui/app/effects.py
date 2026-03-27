from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable

from opcua_tui.app.messages import (
    ChildrenLoadFailed,
    ChildrenLoadStarted,
    ChildrenLoadSucceeded,
    ConnectRequested,
    ConnectionFailed,
    ConnectionStarted,
    ConnectionSucceeded,
    NodeAttributesLoaded,
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
from opcua_tui.application.ports.opcua_client import OpcUaClientPort

Dispatch = Callable[[object], Awaitable[None]]
logger = logging.getLogger(__name__)


class Effects:
    def __init__(self, dispatch: Dispatch, opcua: OpcUaClientPort) -> None:
        self.dispatch = dispatch
        self.opcua = opcua

    def _log_operation_failure(self, operation: str, **context: object) -> str:
        error_ref = uuid.uuid4().hex[:8]
        logger.exception(
            "OPC UA operation failed",
            extra={"operation": operation, "error_ref": error_ref, **context},
        )
        return error_ref

    async def handle(self, message: object) -> None:
        match message:
            case ConnectRequested(params=params):
                await self.dispatch(ConnectionStarted(endpoint=params.endpoint))
                try:
                    session = await self.opcua.connect(params)
                    await self.dispatch(ConnectionSucceeded(session=session))
                except Exception as exc:
                    error_ref = self._log_operation_failure("connect", endpoint=params.endpoint)
                    await self.dispatch(
                        ConnectionFailed(
                            endpoint=params.endpoint, error=str(exc), error_ref=error_ref
                        )
                    )

            case RootBrowseRequested():
                await self.dispatch(RootBrowseStarted())
                try:
                    roots = await self.opcua.browse_children(None)
                    await self.dispatch(RootBrowseSucceeded(nodes=roots))
                except Exception as exc:
                    error_ref = self._log_operation_failure("browse_root")
                    await self.dispatch(RootBrowseFailed(error=str(exc), error_ref=error_ref))

            case NodeExpandRequested(node_id=node_id):
                await self.dispatch(ChildrenLoadStarted(node_id=node_id))
                try:
                    children = await self.opcua.browse_children(node_id)
                    await self.dispatch(
                        ChildrenLoadSucceeded(parent_node_id=node_id, children=children)
                    )
                except Exception as exc:
                    error_ref = self._log_operation_failure("browse_children", node_id=node_id)
                    await self.dispatch(
                        ChildrenLoadFailed(
                            parent_node_id=node_id,
                            error=str(exc),
                            error_ref=error_ref,
                        )
                    )

            case NodeSelected(node_id=node_id):
                await self.dispatch(NodeInspectionStarted(node_id=node_id))
                try:
                    attrs_task = asyncio.create_task(self.opcua.read_attributes(node_id))
                    value_task = asyncio.create_task(self.opcua.read_value(node_id))
                    attrs, value = await asyncio.gather(attrs_task, value_task)
                    await self.dispatch(NodeAttributesLoaded(attributes=attrs))
                    await self.dispatch(NodeValueLoaded(value=value))
                except Exception as exc:
                    error_ref = self._log_operation_failure("inspect_node", node_id=node_id)
                    await self.dispatch(
                        NodeInspectionFailed(node_id=node_id, error=str(exc), error_ref=error_ref)
                    )

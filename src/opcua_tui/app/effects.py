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
    NodeSubscribeFailed,
    NodeSubscribeRequested,
    NodeSubscribeStarted,
    NodeSubscribeSucceeded,
    NodeSubscriptionValueReceived,
    NodeSelected,
    NodeUnsubscribeFailed,
    NodeUnsubscribeRequested,
    NodeUnsubscribeStarted,
    NodeUnsubscribeSucceeded,
    NodeWriteFailed,
    NodeWriteRequested,
    NodeWriteStarted,
    NodeWriteSucceeded,
    NodeValueLoaded,
    RootBrowseFailed,
    RootBrowseRequested,
    RootBrowseStarted,
    RootBrowseSucceeded,
)
from opcua_tui.application.ports.opcua_client import OpcUaClientPort
from opcua_tui.domain.endpoint import sanitize_endpoint
from opcua_tui.domain.models import SubscriptionValueUpdate

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
                safe_endpoint = sanitize_endpoint(params.endpoint)
                await self.dispatch(ConnectionStarted(endpoint=safe_endpoint))
                try:
                    await self.opcua.stop_subscription_stream()
                    session = await self.opcua.connect(params)
                    await self.dispatch(ConnectionSucceeded(session=session))
                except Exception as exc:
                    error_ref = self._log_operation_failure("connect", endpoint=safe_endpoint)
                    await self.dispatch(
                        ConnectionFailed(
                            endpoint=safe_endpoint, error=str(exc), error_ref=error_ref
                        )
                    )

            case ConnectionSucceeded():
                try:
                    await self.opcua.start_subscription_stream(
                        on_update=self._on_subscription_update
                    )
                except Exception:
                    logger.exception(
                        "Failed to start subscription stream",
                        extra={"operation": "start_subscription_stream"},
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

            case NodeWriteRequested(
                node_id=node_id, value_text=value_text, variant_hint=variant_hint
            ):
                await self.dispatch(NodeWriteStarted(node_id=node_id))
                try:
                    await self.opcua.write_value(node_id, value_text, variant_hint)
                    value = await self.opcua.read_value(node_id)
                    await self.dispatch(NodeValueLoaded(value=value))
                    await self.dispatch(NodeWriteSucceeded(node_id=node_id))
                except Exception as exc:
                    error_ref = self._log_operation_failure("write_value", node_id=node_id)
                    await self.dispatch(
                        NodeWriteFailed(node_id=node_id, error=str(exc), error_ref=error_ref)
                    )

            case NodeSubscribeRequested(node_id=node_id, display_name=display_name):
                await self.dispatch(NodeSubscribeStarted(node_id=node_id))
                try:
                    canonical_node_id = await self.opcua.subscribe_value(node_id)
                    await self.dispatch(
                        NodeSubscribeSucceeded(node_id=canonical_node_id, display_name=display_name)
                    )
                except Exception as exc:
                    error_ref = self._log_operation_failure("subscribe_value", node_id=node_id)
                    await self.dispatch(
                        NodeSubscribeFailed(node_id=node_id, error=str(exc), error_ref=error_ref)
                    )

            case NodeUnsubscribeRequested(node_id=node_id):
                await self.dispatch(NodeUnsubscribeStarted(node_id=node_id))
                try:
                    await self.opcua.unsubscribe_value(node_id)
                    await self.dispatch(NodeUnsubscribeSucceeded(node_id=node_id))
                except Exception as exc:
                    error_ref = self._log_operation_failure("unsubscribe_value", node_id=node_id)
                    await self.dispatch(
                        NodeUnsubscribeFailed(node_id=node_id, error=str(exc), error_ref=error_ref)
                    )

    async def _on_subscription_update(self, update: SubscriptionValueUpdate) -> None:
        await self.dispatch(NodeSubscriptionValueReceived(update=update))

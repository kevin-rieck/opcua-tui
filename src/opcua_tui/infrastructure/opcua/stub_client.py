from __future__ import annotations

import re
import uuid
from typing import Any

from asyncua import Client, ua

from opcua_tui.domain.models import (
    ConnectParams,
    DataValueView,
    NodeAttributes,
    NodeRef,
    ServerInfo,
    SessionInfo,
)


class StubOpcUaClientAdapter:
    def __init__(self) -> None:
        self._client: Client | None = None
        self._session_id: str | None = None

    async def connect(self, params: ConnectParams) -> SessionInfo:
        if self._client is not None:
            await self.disconnect()

        client = Client(url=params.endpoint)
        await client.connect()
        self._client = client

        self._session_id = uuid.uuid4().hex
        try:
            if hasattr(client, "get_session"):
                session = await client.get_session()  # type: ignore[no-untyped-call]
                candidate = getattr(session, "SessionId", None)
                if candidate is not None:
                    self._session_id = str(candidate)
        except Exception:
            pass

        server_name = "OPC UA Server"
        try:
            endpoint = await client.nodes.server.get_child(
                ["0:ServerStatus", "0:BuildInfo", "0:ProductName"]
            )
            product_name = await endpoint.read_value()
            if product_name:
                server_name = str(product_name)
        except Exception:
            pass

        return SessionInfo(
            session_id=self._session_id or "unknown-session",
            endpoint=params.endpoint,
            server=ServerInfo(application_name=server_name),
        )

    async def disconnect(self) -> None:
        if self._client is None:
            return
        try:
            await self._client.disconnect()
        finally:
            self._client = None
            self._session_id = None

    async def browse_children(self, node_id: str | None) -> list[NodeRef]:
        client = self._require_client()
        node = (
            client.nodes.root
            if node_id is None
            else client.get_node(self._normalize_node_id(node_id))
        )
        children = await node.get_children()
        result: list[NodeRef] = []

        for child in children:
            display_name = await self._safe_display_name(child)
            node_class = await self._safe_node_class(child)
            has_children = await self._safe_has_children(child)
            result.append(
                NodeRef(
                    node_id=self._node_id_to_string(child.nodeid),
                    display_name=display_name,
                    node_class=node_class,
                    has_children=has_children,
                )
            )

        return result

    async def read_attributes(self, node_id: str) -> NodeAttributes:
        client = self._require_client()
        normalized_node_id = self._normalize_node_id(node_id)
        node = client.get_node(normalized_node_id)
        canonical_node_id = self._node_id_to_string(getattr(node, "nodeid", normalized_node_id))

        display_name = await self._safe_display_name(node)
        browse_name = await self._safe_browse_name(node)
        node_class = await self._safe_node_class(node)
        description = await self._safe_description(node)
        data_type = await self._safe_data_type(node)
        access_level = await self._safe_access_level(node)

        return NodeAttributes(
            node_id=canonical_node_id,
            display_name=display_name,
            browse_name=browse_name,
            node_class=node_class,
            description=description,
            data_type=data_type,
            access_level=access_level,
        )

    async def read_value(self, node_id: str) -> DataValueView:
        client = self._require_client()
        normalized_node_id = self._normalize_node_id(node_id)
        node = client.get_node(normalized_node_id)
        canonical_node_id = self._node_id_to_string(getattr(node, "nodeid", normalized_node_id))

        try:
            data_value = await node.read_data_value()
            variant = data_value.Value
            value = variant.Value if variant is not None else None
            variant_type = variant.VariantType.name if variant is not None else None
            status_code = (
                data_value.StatusCode.name if data_value.StatusCode is not None else "Unknown"
            )
        except ua.UaStatusCodeError as exc:
            value = None
            variant_type = None
            status_code = exc.__class__.__name__

        return DataValueView(
            node_id=canonical_node_id,
            value=value,
            variant_type=variant_type,
            status_code=status_code,
        )

    def _require_client(self) -> Client:
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")
        return self._client

    def _node_id_to_string(self, node_id: Any) -> str:
        try:
            if hasattr(node_id, "to_string"):
                return node_id.to_string()
        except Exception:
            pass
        return str(node_id)

    def _normalize_node_id(self, node_id: Any) -> Any:
        if node_id is None:
            return None

        if isinstance(node_id, ua.NodeId):
            return node_id

        if not isinstance(node_id, str):
            return node_id

        parsed = self._parse_nodeid_repr(node_id)
        if parsed is not None:
            return parsed
        return node_id

    def _parse_nodeid_repr(self, node_id_repr: str) -> ua.NodeId | None:
        pattern = (
            r"^NodeId\(Identifier=(?P<identifier>.+), "
            r"NamespaceIndex=(?P<ns>\d+), "
            r"NodeIdType=<NodeIdType\.(?P<kind>\w+): \d+>\)$"
        )
        match = re.match(pattern, node_id_repr)
        if not match:
            return None

        raw_identifier = match.group("identifier").strip()
        namespace_index = int(match.group("ns"))
        kind = match.group("kind")

        if raw_identifier.startswith("'") and raw_identifier.endswith("'"):
            identifier: Any = raw_identifier[1:-1]
        else:
            try:
                identifier = int(raw_identifier)
            except ValueError:
                identifier = raw_identifier

        node_type = {
            "TwoByte": ua.NodeIdType.TwoByte,
            "FourByte": ua.NodeIdType.FourByte,
            "Numeric": ua.NodeIdType.Numeric,
            "String": ua.NodeIdType.String,
            "Guid": ua.NodeIdType.Guid,
            "ByteString": ua.NodeIdType.ByteString,
        }.get(kind)
        if node_type is None:
            return None

        return ua.NodeId(identifier, namespace_index, node_type)

    async def _safe_display_name(self, node: Any) -> str:
        try:
            value = await node.read_display_name()
            return value.Text or self._node_id_to_string(node.nodeid)
        except Exception:
            return self._node_id_to_string(node.nodeid)

    async def _safe_browse_name(self, node: Any) -> str:
        try:
            value = await node.read_browse_name()
            if value is None:
                return "-"
            name = getattr(value, "Name", None)
            ns_index = getattr(value, "NamespaceIndex", None)
            if name is None:
                return str(value)
            if ns_index is None:
                return str(name)
            return f"{ns_index}:{name}"
        except Exception:
            return "-"

    async def _safe_node_class(self, node: Any) -> str:
        try:
            value = await node.read_node_class()
            if isinstance(value, ua.NodeClass):
                return value.name
            return str(value)
        except Exception:
            return "Unknown"

    async def _safe_has_children(self, node: Any) -> bool:
        try:
            children = await node.get_children()
            return len(children) > 0
        except Exception:
            return False

    async def _safe_description(self, node: Any) -> str | None:
        try:
            value = await node.read_description()
            text = value.Text if value is not None else None
            return text if text else None
        except Exception:
            return None

    async def _safe_data_type(self, node: Any) -> str | None:
        try:
            node_class = await node.read_node_class()
            if node_class != ua.NodeClass.Variable:
                return None
            dtype_nodeid = await node.read_data_type()
            dtype_node = self._require_client().get_node(dtype_nodeid)
            browse_name = await dtype_node.read_browse_name()
            return browse_name.Name if browse_name is not None else str(dtype_nodeid)
        except Exception:
            return None

    async def _safe_access_level(self, node: Any) -> str | None:
        try:
            node_class = await node.read_node_class()
            if node_class != ua.NodeClass.Variable:
                return None
            access_level = await node.read_access_level()
            if isinstance(access_level, set):
                return ",".join(sorted(str(item) for item in access_level))
            return str(access_level)
        except Exception:
            return None

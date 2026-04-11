from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

from asyncua import Client, ua
from asyncua.crypto import security_policies

from opcua_tui.domain.enums import AuthenticationMode, SecurityMode, SecurityPolicy
from opcua_tui.domain.models import (
    ConnectParams,
    DataValueView,
    NodeAttributes,
    NodeRef,
    ServerInfo,
    SessionInfo,
)
from opcua_tui.infrastructure.opcua.pki import ClientPkiStore


SECURITY_POLICY_MAP: dict[SecurityPolicy, type[security_policies.SecurityPolicy]] = {
    SecurityPolicy.BASIC128RSA15: security_policies.SecurityPolicyBasic128Rsa15,
    SecurityPolicy.BASIC256: security_policies.SecurityPolicyBasic256,
    SecurityPolicy.BASIC256SHA256: security_policies.SecurityPolicyBasic256Sha256,
    SecurityPolicy.AES128_SHA256_RSAOAEP: security_policies.SecurityPolicyAes128Sha256RsaOaep,
    SecurityPolicy.AES256_SHA256_RSAPSS: security_policies.SecurityPolicyAes256Sha256RsaPss,
}

SECURITY_MODE_MAP: dict[SecurityMode, ua.MessageSecurityMode] = {
    SecurityMode.SIGN: ua.MessageSecurityMode.Sign,
    SecurityMode.SIGN_AND_ENCRYPT: ua.MessageSecurityMode.SignAndEncrypt,
}


class StubOpcUaClientAdapter:
    def __init__(self, *, pki_store: ClientPkiStore | None = None) -> None:
        self._client: Client | None = None
        self._session_id: str | None = None
        self._pki_store = pki_store or ClientPkiStore()

    async def connect(self, params: ConnectParams) -> SessionInfo:
        if self._client is not None:
            await self.disconnect()

        client = Client(url=params.endpoint)
        await self._configure_security(client=client, params=params)
        self._configure_auth(client=client, params=params)
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

    async def _configure_security(self, *, client: Client, params: ConnectParams) -> None:
        if params.security_mode == SecurityMode.NONE:
            if params.security_policy != SecurityPolicy.NONE:
                raise ValueError("Security policy must be None when security mode is None.")
            return

        if params.security_policy == SecurityPolicy.NONE:
            raise ValueError("Security policy is required for secure connection modes.")

        mode = SECURITY_MODE_MAP.get(params.security_mode)
        policy = SECURITY_POLICY_MAP.get(params.security_policy)
        if mode is None:
            raise ValueError(f"Unsupported security mode: {params.security_mode.value}")
        if policy is None:
            raise ValueError(f"Unsupported security policy: {params.security_policy.value}")

        material = self._pki_store.ensure_client_certificate_material(
            certificate_path=params.certificate_path,
            private_key_path=params.private_key_path,
        )
        self._validate_private_key_unencrypted(material.private_key_path)
        await client.set_security(
            policy=policy,
            certificate=material.certificate_path,
            private_key=material.private_key_path,
            mode=mode,
        )

    def _configure_auth(self, *, client: Client, params: ConnectParams) -> None:
        if params.authentication_mode == AuthenticationMode.ANONYMOUS:
            return

        if params.authentication_mode == AuthenticationMode.USERNAME_PASSWORD:
            username = params.username.strip()
            password = params.password
            if not username:
                raise ValueError("Username is required for username/password authentication.")
            if not password:
                raise ValueError("Password is required for username/password authentication.")
            client.set_user(username)
            client.set_password(password)
            return

        if params.authentication_mode == AuthenticationMode.CERTIFICATE:
            raise ValueError("Certificate authentication is not supported in v1.")

        raise ValueError(f"Unsupported authentication mode: {params.authentication_mode.value}")

    def _validate_private_key_unencrypted(self, private_key_path: Path) -> None:
        try:
            text = private_key_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # DER key format has no marker that indicates passphrase support in this check.
            return
        if "ENCRYPTED PRIVATE KEY" in text:
            raise ValueError("Encrypted private keys are not supported in v1.")

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

    async def write_value(
        self, node_id: str, value_text: str, variant_hint: str | None = None
    ) -> None:
        client = self._require_client()
        normalized_node_id = self._normalize_node_id(node_id)
        node = client.get_node(normalized_node_id)
        coerced_value, variant_type = self._coerce_write_value(value_text, variant_hint)
        try:
            if variant_type is None:
                await node.write_value(coerced_value)
            else:
                await node.write_value(coerced_value, variant_type)
        except ua.UaStatusCodeError as exc:
            # Some servers reject writes that include status/timestamps in DataValue.
            if not self._is_bad_write_not_supported(exc):
                raise
            await self._write_value_only(node, coerced_value, variant_type)

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

    def _coerce_write_value(
        self, value_text: str, variant_hint: str | None
    ) -> tuple[Any, ua.VariantType | None]:
        normalized = value_text.strip()
        if not normalized:
            raise ValueError("Value is required.")

        variant_type = self._resolve_variant_type(variant_hint)
        if variant_type is not None:
            return self._coerce_value_for_variant(normalized, variant_type), variant_type

        lowered = normalized.lower()
        if lowered in {"true", "false"}:
            return lowered == "true", None

        try:
            return int(normalized, 10), None
        except ValueError:
            pass

        try:
            return float(normalized), None
        except ValueError:
            return normalized, None

    def _resolve_variant_type(self, variant_hint: str | None) -> ua.VariantType | None:
        hint = (variant_hint or "").strip().lower()
        if not hint:
            return None

        alias_map = {
            "bool": ua.VariantType.Boolean,
            "boolean": ua.VariantType.Boolean,
            "sbyte": ua.VariantType.SByte,
            "byte": ua.VariantType.Byte,
            "int16": ua.VariantType.Int16,
            "short": ua.VariantType.Int16,
            "uint16": ua.VariantType.UInt16,
            "word": ua.VariantType.UInt16,
            "int32": ua.VariantType.Int32,
            "dword": ua.VariantType.UInt32,
            "uint32": ua.VariantType.UInt32,
            "int64": ua.VariantType.Int64,
            "long": ua.VariantType.Int64,
            "uint64": ua.VariantType.UInt64,
            "float": ua.VariantType.Float,
            "single": ua.VariantType.Float,
            "double": ua.VariantType.Double,
            "string": ua.VariantType.String,
            "char": ua.VariantType.String,
            "text": ua.VariantType.String,
        }
        if hint in alias_map:
            return alias_map[hint]

        if "bool" in hint:
            return ua.VariantType.Boolean
        if "float" in hint:
            return ua.VariantType.Float
        if "double" in hint:
            return ua.VariantType.Double
        if "uint64" in hint:
            return ua.VariantType.UInt64
        if "int64" in hint:
            return ua.VariantType.Int64
        if "uint32" in hint:
            return ua.VariantType.UInt32
        if "int32" in hint:
            return ua.VariantType.Int32
        if "uint16" in hint:
            return ua.VariantType.UInt16
        if "int16" in hint:
            return ua.VariantType.Int16
        if "sbyte" in hint:
            return ua.VariantType.SByte
        if "byte" in hint:
            return ua.VariantType.Byte
        if any(token in hint for token in ("string", "char", "text")):
            return ua.VariantType.String
        return None

    def _coerce_value_for_variant(self, value_text: str, variant_type: ua.VariantType) -> Any:
        if variant_type == ua.VariantType.Boolean:
            return self._parse_bool(value_text)
        if variant_type == ua.VariantType.SByte:
            return self._parse_bounded_int(value_text, -128, 127, "SByte")
        if variant_type == ua.VariantType.Byte:
            return self._parse_bounded_int(value_text, 0, 255, "Byte")
        if variant_type == ua.VariantType.Int16:
            return self._parse_bounded_int(value_text, -32768, 32767, "Int16")
        if variant_type == ua.VariantType.UInt16:
            return self._parse_bounded_int(value_text, 0, 65535, "UInt16")
        if variant_type == ua.VariantType.Int32:
            return self._parse_bounded_int(value_text, -2147483648, 2147483647, "Int32")
        if variant_type == ua.VariantType.UInt32:
            return self._parse_bounded_int(value_text, 0, 4294967295, "UInt32")
        if variant_type == ua.VariantType.Int64:
            return self._parse_bounded_int(
                value_text, -9223372036854775808, 9223372036854775807, "Int64"
            )
        if variant_type == ua.VariantType.UInt64:
            return self._parse_bounded_int(value_text, 0, 18446744073709551615, "UInt64")
        if variant_type in {ua.VariantType.Float, ua.VariantType.Double}:
            return float(value_text)
        if variant_type == ua.VariantType.String:
            return value_text
        raise ValueError(f"Writing values as {variant_type.name} is not yet supported.")

    def _parse_bool(self, value: str) -> bool:
        lowered = value.lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
        raise ValueError("Boolean values must be true/false, 1/0, yes/no, or on/off.")

    def _parse_bounded_int(self, value_text: str, minimum: int, maximum: int, label: str) -> int:
        value = int(value_text, 10)
        if value < minimum or value > maximum:
            raise ValueError(f"{label} must be between {minimum} and {maximum}.")
        return value

    async def _write_value_only(
        self, node: Any, value: Any, variant_type: ua.VariantType | None = None
    ) -> None:
        if not hasattr(node, "write_attribute"):
            raise RuntimeError("Server rejected the write format and no fallback is available.")
        data_value = ua.DataValue(
            Value=ua.Variant(value, variant_type)
            if variant_type is not None
            else ua.Variant(value),
            StatusCode_=None,
            SourceTimestamp=None,
            ServerTimestamp=None,
            SourcePicoseconds=None,
            ServerPicoseconds=None,
        )
        await node.write_attribute(ua.AttributeIds.Value, data_value)

    def _is_bad_write_not_supported(self, exc: ua.UaStatusCodeError) -> bool:
        code = getattr(exc, "code", None)
        if code == ua.StatusCodes.BadWriteNotSupported:
            return True
        return "BadWriteNotSupported" in repr(exc)

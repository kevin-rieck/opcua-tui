import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from opcua_tui.domain.enums import AuthenticationMode, SecurityMode, SecurityPolicy
from opcua_tui.domain.models import ConnectParams
from opcua_tui.infrastructure.opcua.pki import ClientCertificateMaterial
from opcua_tui.infrastructure.opcua import stub_client
from opcua_tui.infrastructure.opcua.stub_client import StubOpcUaClientAdapter


def test_stub_client_public_methods_return_domain_models(monkeypatch) -> None:
    class FakeNode:
        def __init__(
            self,
            nodeid: str,
            display_name: str,
            node_class,
            *,
            browse_name: str | None = None,
            ns_index: int = 2,
            description: str | None = None,
            data_type: str | None = None,
            access_level: set[str] | None = None,
            value=None,
            variant_type: str = "String",
            children: list["FakeNode"] | None = None,
            raise_bad_write: bool = False,
        ) -> None:
            self.nodeid = nodeid
            self._display_name = display_name
            self._node_class = node_class
            self._browse_name = browse_name or display_name
            self._ns_index = ns_index
            self._description = description
            self._data_type = data_type
            self._access_level = access_level or set()
            self._value = value
            self._variant_type = variant_type
            self._children = children or []
            self._raise_bad_write = raise_bad_write

        async def get_children(self):
            return self._children

        async def read_display_name(self):
            return SimpleNamespace(Text=self._display_name)

        async def read_node_class(self):
            return self._node_class

        async def read_browse_name(self):
            return SimpleNamespace(Name=self._browse_name, NamespaceIndex=self._ns_index)

        async def read_description(self):
            return SimpleNamespace(Text=self._description)

        async def read_data_type(self):
            return self._data_type

        async def read_access_level(self):
            return self._access_level

        async def read_data_value(self):
            variant = SimpleNamespace(
                Value=self._value, VariantType=SimpleNamespace(name=self._variant_type)
            )
            return SimpleNamespace(Value=variant, StatusCode=SimpleNamespace(name="Good"))

        async def read_value(self):
            return self._value

        async def write_value(self, value, variant_type=None):
            if self._raise_bad_write:
                raise stub_client.ua.UaStatusCodeError(
                    stub_client.ua.StatusCodes.BadWriteNotSupported
                )
            self._value = value
            if variant_type is not None:
                self._variant_type = variant_type.name

        async def write_attribute(self, _attribute_id, data_value):
            self._value = data_value.Value.Value

    class FakeServerNode:
        def __init__(self, product_name_node: FakeNode) -> None:
            self._product_name_node = product_name_node

        async def get_child(self, _path):
            return self._product_name_node

    class FakeClient:
        def __init__(self, url: str) -> None:
            self.url = url
            self._connected = False
            self._node_map: dict[str, FakeNode] = {}

            dtype_double = FakeNode(
                "i=11",
                "Double",
                stub_client.ua.NodeClass.DataType,
                browse_name="Double",
                ns_index=0,
            )
            dtype_int32 = FakeNode(
                "i=6", "Int32", stub_client.ua.NodeClass.DataType, browse_name="Int32", ns_index=0
            )
            dtype_string = FakeNode(
                "i=12",
                "String",
                stub_client.ua.NodeClass.DataType,
                browse_name="String",
                ns_index=0,
            )
            self._node_map[dtype_double.nodeid] = dtype_double
            self._node_map[dtype_int32.nodeid] = dtype_int32
            self._node_map[dtype_string.nodeid] = dtype_string

            temp = FakeNode(
                "ns=2;s=Temperature",
                "Temperature",
                stub_client.ua.NodeClass.Variable,
                data_type="i=11",
                access_level={"CurrentRead"},
                description="Process temperature",
                value=42.3,
                variant_type="Double",
            )
            speed = FakeNode(
                "ns=2;s=Machine/Speed",
                "Speed",
                stub_client.ua.NodeClass.Variable,
                data_type="i=6",
                access_level={"CurrentRead"},
                value=1200,
                variant_type="Int32",
                raise_bad_write=True,
            )
            state = FakeNode(
                "ns=2;s=Machine/State",
                "State",
                stub_client.ua.NodeClass.Variable,
                data_type="i=12",
                access_level={"CurrentRead"},
                value="Running",
                variant_type="String",
            )
            other = FakeNode(
                "ns=2;s=AnyOther",
                "AnyOther",
                stub_client.ua.NodeClass.Variable,
                data_type="i=12",
                access_level={"CurrentRead"},
                value="N/A",
                variant_type="String",
            )
            machine = FakeNode(
                "ns=2;s=Machine",
                "Machine",
                stub_client.ua.NodeClass.Object,
                children=[speed, state],
            )
            objects = FakeNode(
                "i=85",
                "Objects",
                stub_client.ua.NodeClass.Object,
                ns_index=0,
                children=[machine, temp, other],
            )
            root = FakeNode(
                "i=84", "Root", stub_client.ua.NodeClass.Object, ns_index=0, children=[objects]
            )

            for node in [temp, speed, state, other, machine, objects, root]:
                self._node_map[node.nodeid] = node

            product_name = FakeNode(
                "ns=0;s=ProductName",
                "ProductName",
                stub_client.ua.NodeClass.Variable,
                ns_index=0,
                value="Stub OPC UA Server",
            )
            self.nodes = SimpleNamespace(
                root=root,
                server=FakeServerNode(product_name),
            )

        async def connect(self):
            self._connected = True

        async def disconnect(self):
            self._connected = False

        async def get_session(self):
            return SimpleNamespace(SessionId="fake-session")

        def get_node(self, node_id):
            key = node_id.to_string() if hasattr(node_id, "to_string") else str(node_id)
            if key in self._node_map:
                return self._node_map[key]
            return FakeNode(key, key, stub_client.ua.NodeClass.Object, children=[])

    monkeypatch.setattr(stub_client, "Client", FakeClient)

    async def scenario() -> None:
        client = StubOpcUaClientAdapter()

        session = await client.connect(ConnectParams(endpoint="opc.tcp://localhost:4840"))
        roots = await client.browse_children(None)
        unknown = await client.browse_children("missing")
        attrs = await client.read_attributes("ns=2;s=Temperature")
        temp = await client.read_value("ns=2;s=Temperature")
        speed = await client.read_value("ns=2;s=Machine/Speed")
        state = await client.read_value("ns=2;s=Machine/State")
        other = await client.read_value("ns=2;s=AnyOther")
        await client.write_value("ns=2;s=Machine/Speed", "1300", "Int32")
        speed_after_write = await client.read_value("ns=2;s=Machine/Speed")
        await client.write_value("ns=2;s=AnyOther", "true", "Boolean")
        other_after_bool_write = await client.read_value("ns=2;s=AnyOther")
        await client.disconnect()

        assert session.endpoint == "opc.tcp://localhost:4840"
        assert session.server.application_name == "Stub OPC UA Server"
        assert session.session_id == "fake-session"
        assert len(roots) >= 1
        assert unknown == []
        assert attrs.node_id == "ns=2;s=Temperature"
        assert attrs.data_type == "Double"
        assert temp.value == 42.3
        assert speed.value == 1200
        assert state.value == "Running"
        assert isinstance(other.value, str)
        assert speed_after_write.value == 1300
        assert other_after_bool_write.value is True

    asyncio.run(scenario())


def test_stub_client_coerce_write_value_supports_int16_and_float() -> None:
    client = StubOpcUaClientAdapter()

    value_i16, type_i16 = client._coerce_write_value("32767", "Int16")
    value_f32, type_f32 = client._coerce_write_value("12.5", "Float")

    assert value_i16 == 32767
    assert type_i16 == stub_client.ua.VariantType.Int16
    assert value_f32 == 12.5
    assert type_f32 == stub_client.ua.VariantType.Float


def test_stub_client_coerce_write_value_rejects_out_of_range_int16() -> None:
    client = StubOpcUaClientAdapter()

    with pytest.raises(ValueError, match="Int16 must be between -32768 and 32767"):
        client._coerce_write_value("40000", "Int16")


def test_stub_client_write_value_passes_explicit_variant_type(monkeypatch) -> None:
    class FakeNode:
        def __init__(self) -> None:
            self.last_call: tuple[object, object | None] | None = None

        async def write_value(self, value, variant_type=None):
            self.last_call = (value, variant_type)

    class FakeClient:
        def __init__(self, url: str) -> None:
            self.url = url
            self.node = FakeNode()

        async def connect(self) -> None:
            return None

        async def disconnect(self) -> None:
            return None

        def get_node(self, _node_id):
            return self.node

    monkeypatch.setattr(stub_client, "Client", FakeClient)

    async def scenario() -> None:
        client = StubOpcUaClientAdapter()
        await client.connect(ConnectParams(endpoint="opc.tcp://localhost:4840"))
        fake_node = client._require_client().get_node("ns=2;s=F32")
        await client.write_value("ns=2;s=F32", "1.25", "Float")
        assert fake_node.last_call == (1.25, stub_client.ua.VariantType.Float)
        await client.disconnect()

    asyncio.run(scenario())


def test_stub_client_connect_configures_secure_channel_and_username_auth(monkeypatch) -> None:
    class FakeSecureClient:
        def __init__(self, url: str) -> None:
            self.url = url
            self.application_uri = "urn:test:secure-client"
            self.security_calls: list[dict[str, object]] = []
            self.user = None
            self.password = None
            product_name = SimpleNamespace(read_value=lambda: _async_return("Secure Server"))
            self.nodes = SimpleNamespace(
                server=SimpleNamespace(
                    get_child=lambda _path: _async_return(product_name),
                )
            )

        async def set_security(self, **kwargs) -> None:
            self.security_calls.append(kwargs)

        def set_user(self, value: str) -> None:
            self.user = value

        def set_password(self, value: str) -> None:
            self.password = value

        async def connect(self) -> None:
            return None

        async def disconnect(self) -> None:
            return None

        async def get_session(self):
            return SimpleNamespace(SessionId="secure-session")

        def get_node(self, node_id):
            raise AssertionError(f"Unexpected get_node call: {node_id}")

    class FakePkiStore:
        async def ensure_client_certificate_material(
            self, *, certificate_path: str, private_key_path: str, app_uri: str
        ):
            assert certificate_path == ""
            assert private_key_path == ""
            assert app_uri == "urn:test:secure-client"
            return ClientCertificateMaterial(
                certificate_path=Path("client.der"),
                private_key_path=Path("client.pem"),
                fingerprint_sha256="FINGERPRINT",
            )

    monkeypatch.setattr(stub_client, "Client", FakeSecureClient)
    monkeypatch.setattr(
        StubOpcUaClientAdapter,
        "_validate_private_key_unencrypted",
        lambda _self, _path: None,
    )

    async def scenario() -> None:
        client = StubOpcUaClientAdapter(pki_store=FakePkiStore())
        session = await client.connect(
            ConnectParams(
                endpoint="opc.tcp://localhost:4840",
                security_mode=SecurityMode.SIGN,
                security_policy=SecurityPolicy.BASIC256SHA256,
                authentication_mode=AuthenticationMode.USERNAME_PASSWORD,
                username="operator",
                password="secret",
            )
        )
        secure_client = client._require_client()
        assert secure_client.user == "operator"
        assert secure_client.password == "secret"
        assert len(secure_client.security_calls) == 1
        call = secure_client.security_calls[0]
        assert call["certificate"] == Path("client.der")
        assert call["private_key"] == Path("client.pem")
        assert call["mode"] == stub_client.ua.MessageSecurityMode.Sign
        assert session.session_id == "secure-session"

    asyncio.run(scenario())


def test_stub_client_connect_rejects_invalid_security_combinations() -> None:
    client = StubOpcUaClientAdapter()

    with pytest.raises(ValueError, match="Security policy must be None"):
        asyncio.run(
            client._configure_security(
                client=SimpleNamespace(),
                params=ConnectParams(
                    endpoint="opc.tcp://localhost:4840",
                    security_mode=SecurityMode.NONE,
                    security_policy=SecurityPolicy.BASIC256SHA256,
                ),
            )
        )

    with pytest.raises(ValueError, match="Security policy is required"):
        asyncio.run(
            client._configure_security(
                client=SimpleNamespace(),
                params=ConnectParams(
                    endpoint="opc.tcp://localhost:4840",
                    security_mode=SecurityMode.SIGN,
                    security_policy=SecurityPolicy.NONE,
                ),
            )
        )


async def _async_return(value):
    return value

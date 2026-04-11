import asyncio

from opcua_tui.application.ports.opcua_client import OpcUaClientPort
from opcua_tui.domain.models import (
    ConnectParams,
    DataValueView,
    NodeAttributes,
    NodeRef,
    ServerInfo,
    SessionInfo,
)


class FakeAdapter:
    async def start_subscription_stream(self, on_update) -> None:
        return None

    async def stop_subscription_stream(self) -> None:
        return None

    async def subscribe_value(self, node_id: str) -> str:
        return node_id

    async def unsubscribe_value(self, node_id: str) -> None:
        return None

    async def connect(self, params: ConnectParams) -> SessionInfo:
        return SessionInfo(
            session_id="fake-session",
            endpoint=params.endpoint,
            server=ServerInfo(application_name="Fake Server"),
        )

    async def disconnect(self) -> None:
        return None

    async def browse_children(self, node_id: str | None) -> list[NodeRef]:
        label = "root" if node_id is None else f"{node_id}/child"
        return [NodeRef(node_id=label, display_name=label, node_class="Object")]

    async def read_attributes(self, node_id: str) -> NodeAttributes:
        return NodeAttributes(
            node_id=node_id,
            display_name=node_id,
            browse_name=node_id,
            node_class="Object",
        )

    async def read_value(self, node_id: str) -> DataValueView:
        return DataValueView(node_id=node_id, value=123, variant_type="int", status_code="Good")


def _use_port(port: OpcUaClientPort) -> OpcUaClientPort:
    return port


def test_fake_adapter_satisfies_protocol_surface() -> None:
    async def scenario() -> None:
        port = _use_port(FakeAdapter())
        session = await port.connect(ConnectParams(endpoint="opc.tcp://localhost:4840"))
        roots = await port.browse_children(None)
        attrs = await port.read_attributes("n1")
        value = await port.read_value("n1")
        await port.start_subscription_stream(lambda _u: None)
        await port.subscribe_value("n1")
        await port.unsubscribe_value("n1")
        await port.stop_subscription_stream()
        await port.disconnect()

        assert session.endpoint == "opc.tcp://localhost:4840"
        assert roots[0].display_name == "root"
        assert attrs.node_id == "n1"
        assert value.status_code == "Good"

    asyncio.run(scenario())

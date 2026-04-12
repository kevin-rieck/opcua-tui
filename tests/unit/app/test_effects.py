import asyncio

import pytest

from opcua_tui.app.effects import Effects
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
    NodeUnsubscribeRequested,
    NodeUnsubscribeStarted,
    NodeUnsubscribeSucceeded,
    NodeWriteFailed,
    NodeWriteRequested,
    NodeWriteStarted,
    NodeWriteSucceeded,
    NodeValueLoaded,
    OperationFinished,
    OperationStarted,
    RootBrowseFailed,
    RootBrowseRequested,
    RootBrowseStarted,
    RootBrowseSucceeded,
)
from opcua_tui.domain.models import (
    ConnectParams,
    DataValueView,
    NodeAttributes,
    NodeRef,
    ServerInfo,
    SessionInfo,
    SubscriptionValueUpdate,
)


class FakeOpcUa:
    def __init__(self) -> None:
        self.raise_on_connect = False
        self.raise_on_browse = False
        self.raise_on_attrs = False
        self.raise_on_value = False
        self.raise_on_write = False
        self.raise_on_subscribe = False
        self.raise_on_unsubscribe = False
        self.last_node_id: str | None = None
        self.last_write: tuple[str, str, str | None] | None = None
        self.subscription_callback = None

    async def connect(self, params: ConnectParams) -> SessionInfo:
        if self.raise_on_connect:
            raise RuntimeError("connect failed")
        return SessionInfo(
            session_id="fake",
            endpoint=params.endpoint,
            server=ServerInfo(application_name="Fake"),
        )

    async def disconnect(self) -> None:
        return None

    async def start_subscription_stream(self, on_update) -> None:
        self.subscription_callback = on_update
        return None

    async def stop_subscription_stream(self) -> None:
        self.subscription_callback = None
        return None

    async def browse_children(self, node_id: str | None) -> list[NodeRef]:
        if self.raise_on_browse:
            raise RuntimeError("browse failed")
        if node_id is None:
            return [
                NodeRef(
                    node_id="i=85", display_name="Objects", node_class="Object", has_children=True
                )
            ]
        return [NodeRef(node_id=f"{node_id}/child", display_name="Child", node_class="Variable")]

    async def read_attributes(self, node_id: str) -> NodeAttributes:
        self.last_node_id = node_id
        if self.raise_on_attrs:
            raise RuntimeError("attrs failed")
        return NodeAttributes(
            node_id=node_id,
            display_name="X",
            browse_name="X",
            node_class="Variable",
        )

    async def read_value(self, node_id: str) -> DataValueView:
        self.last_node_id = node_id
        if self.raise_on_value:
            raise RuntimeError("value failed")
        return DataValueView(node_id=node_id, value=1, variant_type="int", status_code="Good")

    async def write_value(
        self, node_id: str, value_text: str, variant_hint: str | None = None
    ) -> None:
        self.last_write = (node_id, value_text, variant_hint)
        if self.raise_on_write:
            raise RuntimeError("write failed")
        return None

    async def subscribe_value(self, node_id: str) -> str:
        if self.raise_on_subscribe:
            raise RuntimeError("subscribe failed")
        return node_id

    async def unsubscribe_value(self, node_id: str) -> None:
        if self.raise_on_unsubscribe:
            raise RuntimeError("unsubscribe failed")
        return None


def _run_effect(message: object, opcua: FakeOpcUa) -> list[object]:
    dispatched: list[object] = []

    async def dispatch(msg: object) -> None:
        dispatched.append(msg)

    effects = Effects(dispatch=dispatch, opcua=opcua)
    asyncio.run(effects.handle(message))
    return dispatched


def test_effects_connect_success_and_failure() -> None:
    params = ConnectParams(endpoint="opc.tcp://localhost:4840")

    success_messages = _run_effect(ConnectRequested(params=params), FakeOpcUa())
    assert isinstance(success_messages[0], OperationStarted)
    assert isinstance(success_messages[1], ConnectionStarted)
    assert isinstance(success_messages[2], ConnectionSucceeded)
    assert isinstance(success_messages[3], OperationFinished)

    failing_client = FakeOpcUa()
    failing_client.raise_on_connect = True
    failure_messages = _run_effect(ConnectRequested(params=params), failing_client)
    assert isinstance(failure_messages[0], OperationStarted)
    assert isinstance(failure_messages[1], ConnectionStarted)
    assert isinstance(failure_messages[2], ConnectionFailed)
    assert isinstance(failure_messages[3], OperationFinished)
    assert failure_messages[2].error_ref is not None
    assert failure_messages[3].error_ref is not None


def test_effects_connection_succeeded_starts_subscription_stream() -> None:
    session = SessionInfo(
        session_id="fake",
        endpoint="opc.tcp://localhost:4840",
        server=ServerInfo(application_name="Fake"),
    )
    client = FakeOpcUa()
    _run_effect(ConnectionSucceeded(session=session), client)
    assert client.subscription_callback is not None


def test_effects_subscription_callback_dispatches_value_message() -> None:
    dispatched: list[object] = []
    client = FakeOpcUa()

    async def dispatch(msg: object) -> None:
        dispatched.append(msg)

    session = SessionInfo(
        session_id="fake",
        endpoint="opc.tcp://localhost:4840",
        server=ServerInfo(application_name="Fake"),
    )
    effects = Effects(dispatch=dispatch, opcua=client)
    asyncio.run(effects.handle(ConnectionSucceeded(session=session)))
    update = SubscriptionValueUpdate(
        node_id="n1",
        value=1,
        rendered_value="1",
        variant_type="Int32",
        status_code="Good",
    )
    asyncio.run(client.subscription_callback(update))

    assert isinstance(dispatched[0], NodeSubscriptionValueReceived)


def test_effects_root_browse_success_and_failure() -> None:
    success_messages = _run_effect(RootBrowseRequested(), FakeOpcUa())
    assert isinstance(success_messages[0], OperationStarted)
    assert isinstance(success_messages[1], RootBrowseStarted)
    assert isinstance(success_messages[2], RootBrowseSucceeded)
    assert isinstance(success_messages[3], OperationFinished)

    failing_client = FakeOpcUa()
    failing_client.raise_on_browse = True
    failure_messages = _run_effect(RootBrowseRequested(), failing_client)
    assert isinstance(failure_messages[0], OperationStarted)
    assert isinstance(failure_messages[1], RootBrowseStarted)
    assert isinstance(failure_messages[2], RootBrowseFailed)
    assert isinstance(failure_messages[3], OperationFinished)
    assert failure_messages[2].error_ref is not None


def test_effects_node_expand_success_and_failure() -> None:
    success_messages = _run_effect(NodeExpandRequested(node_id="i=85"), FakeOpcUa())
    assert isinstance(success_messages[0], OperationStarted)
    assert isinstance(success_messages[1], ChildrenLoadStarted)
    assert isinstance(success_messages[2], ChildrenLoadSucceeded)
    assert isinstance(success_messages[3], OperationFinished)

    failing_client = FakeOpcUa()
    failing_client.raise_on_browse = True
    failure_messages = _run_effect(NodeExpandRequested(node_id="i=85"), failing_client)
    assert isinstance(failure_messages[0], OperationStarted)
    assert isinstance(failure_messages[1], ChildrenLoadStarted)
    assert isinstance(failure_messages[2], ChildrenLoadFailed)
    assert isinstance(failure_messages[3], OperationFinished)
    assert failure_messages[2].error_ref is not None


def test_effects_node_selected_success_and_failure() -> None:
    node_id = "ns=2;s=Temperature"

    success_messages = _run_effect(NodeSelected(node_id=node_id), FakeOpcUa())
    assert isinstance(success_messages[0], OperationStarted)
    assert isinstance(success_messages[1], NodeInspectionStarted)
    assert isinstance(success_messages[2], NodeAttributesLoaded)
    assert isinstance(success_messages[3], NodeValueLoaded)
    assert isinstance(success_messages[4], OperationFinished)

    failing_client = FakeOpcUa()
    failing_client.raise_on_value = True
    failure_messages = _run_effect(NodeSelected(node_id=node_id), failing_client)
    assert isinstance(failure_messages[0], OperationStarted)
    assert isinstance(failure_messages[1], NodeInspectionStarted)
    assert isinstance(failure_messages[2], NodeInspectionFailed)
    assert isinstance(failure_messages[3], OperationFinished)
    assert failure_messages[2].error_ref is not None


def test_effects_node_write_success_and_failure() -> None:
    node_id = "ns=2;s=Temperature"
    client = FakeOpcUa()

    success_messages = _run_effect(
        NodeWriteRequested(node_id=node_id, value_text="42", variant_hint="Int32"), client
    )
    assert isinstance(success_messages[0], OperationStarted)
    assert isinstance(success_messages[1], NodeWriteStarted)
    assert isinstance(success_messages[2], NodeValueLoaded)
    assert isinstance(success_messages[3], NodeWriteSucceeded)
    assert isinstance(success_messages[4], OperationFinished)
    assert client.last_write == (node_id, "42", "Int32")

    failing_client = FakeOpcUa()
    failing_client.raise_on_write = True
    failure_messages = _run_effect(
        NodeWriteRequested(node_id=node_id, value_text="42", variant_hint="Int32"), failing_client
    )
    assert isinstance(failure_messages[0], OperationStarted)
    assert isinstance(failure_messages[1], NodeWriteStarted)
    assert isinstance(failure_messages[2], NodeWriteFailed)
    assert isinstance(failure_messages[3], OperationFinished)
    assert failure_messages[2].error_ref is not None


def test_effects_subscription_success_and_failure() -> None:
    node_id = "ns=2;s=Temperature"
    client = FakeOpcUa()
    success_messages = _run_effect(
        NodeSubscribeRequested(node_id=node_id, display_name="Temperature"), client
    )
    assert isinstance(success_messages[0], OperationStarted)
    assert isinstance(success_messages[1], NodeSubscribeStarted)
    assert isinstance(success_messages[2], NodeSubscribeSucceeded)
    assert isinstance(success_messages[3], OperationFinished)

    failing_client = FakeOpcUa()
    failing_client.raise_on_subscribe = True
    failure_messages = _run_effect(
        NodeSubscribeRequested(node_id=node_id, display_name="Temperature"),
        failing_client,
    )
    assert isinstance(failure_messages[0], OperationStarted)
    assert isinstance(failure_messages[1], NodeSubscribeStarted)
    assert isinstance(failure_messages[2], NodeSubscribeFailed)
    assert isinstance(failure_messages[3], OperationFinished)
    assert failure_messages[2].error_ref is not None


def test_effects_unsubscribe_success() -> None:
    node_id = "ns=2;s=Temperature"
    success_messages = _run_effect(NodeUnsubscribeRequested(node_id=node_id), FakeOpcUa())
    assert isinstance(success_messages[0], OperationStarted)
    assert isinstance(success_messages[1], NodeUnsubscribeStarted)
    assert isinstance(success_messages[2], NodeUnsubscribeSucceeded)
    assert isinstance(success_messages[3], OperationFinished)


def test_effects_logs_exception_context_with_error_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    params = ConnectParams(endpoint="opc.tcp://localhost:4840")
    failing_client = FakeOpcUa()
    failing_client.raise_on_connect = True
    captured: dict[str, object] = {}

    def fake_exception(_message: str, *, extra: dict[str, object]) -> None:
        captured.update(extra)

    monkeypatch.setattr("opcua_tui.app.effects.logger.exception", fake_exception)
    failure_messages = _run_effect(ConnectRequested(params=params), failing_client)

    assert isinstance(failure_messages[2], ConnectionFailed)
    assert failure_messages[2].error_ref is not None
    assert captured["operation"] == "connect"
    assert captured["endpoint"] == "opc.tcp://localhost:4840"
    assert captured["error_ref"] == failure_messages[2].error_ref


def test_effects_redacts_endpoint_credentials_in_connect_flow() -> None:
    params = ConnectParams(endpoint="opc.tcp://user:pass@example.com:4840")
    failing_client = FakeOpcUa()
    failing_client.raise_on_connect = True

    failure_messages = _run_effect(ConnectRequested(params=params), failing_client)

    started = failure_messages[1]
    failed = failure_messages[2]
    assert isinstance(started, ConnectionStarted)
    assert isinstance(failed, ConnectionFailed)
    assert started.endpoint == "opc.tcp://***@example.com:4840"
    assert failed.endpoint == "opc.tcp://***@example.com:4840"

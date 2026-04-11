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
    NodeSelected,
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
from opcua_tui.domain.models import (
    ConnectParams,
    DataValueView,
    NodeAttributes,
    NodeRef,
    ServerInfo,
    SessionInfo,
)


class FakeOpcUa:
    def __init__(self) -> None:
        self.raise_on_connect = False
        self.raise_on_browse = False
        self.raise_on_attrs = False
        self.raise_on_value = False
        self.raise_on_write = False
        self.last_node_id: str | None = None
        self.last_write: tuple[str, str, str | None] | None = None

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
    assert isinstance(success_messages[0], ConnectionStarted)
    assert isinstance(success_messages[1], ConnectionSucceeded)

    failing_client = FakeOpcUa()
    failing_client.raise_on_connect = True
    failure_messages = _run_effect(ConnectRequested(params=params), failing_client)
    assert isinstance(failure_messages[0], ConnectionStarted)
    assert isinstance(failure_messages[1], ConnectionFailed)
    assert failure_messages[1].error_ref is not None


def test_effects_root_browse_success_and_failure() -> None:
    success_messages = _run_effect(RootBrowseRequested(), FakeOpcUa())
    assert isinstance(success_messages[0], RootBrowseStarted)
    assert isinstance(success_messages[1], RootBrowseSucceeded)

    failing_client = FakeOpcUa()
    failing_client.raise_on_browse = True
    failure_messages = _run_effect(RootBrowseRequested(), failing_client)
    assert isinstance(failure_messages[0], RootBrowseStarted)
    assert isinstance(failure_messages[1], RootBrowseFailed)
    assert failure_messages[1].error_ref is not None


def test_effects_node_expand_success_and_failure() -> None:
    success_messages = _run_effect(NodeExpandRequested(node_id="i=85"), FakeOpcUa())
    assert isinstance(success_messages[0], ChildrenLoadStarted)
    assert isinstance(success_messages[1], ChildrenLoadSucceeded)

    failing_client = FakeOpcUa()
    failing_client.raise_on_browse = True
    failure_messages = _run_effect(NodeExpandRequested(node_id="i=85"), failing_client)
    assert isinstance(failure_messages[0], ChildrenLoadStarted)
    assert isinstance(failure_messages[1], ChildrenLoadFailed)
    assert failure_messages[1].error_ref is not None


def test_effects_node_selected_success_and_failure() -> None:
    node_id = "ns=2;s=Temperature"

    success_messages = _run_effect(NodeSelected(node_id=node_id), FakeOpcUa())
    assert isinstance(success_messages[0], NodeInspectionStarted)
    assert isinstance(success_messages[1], NodeAttributesLoaded)
    assert isinstance(success_messages[2], NodeValueLoaded)

    failing_client = FakeOpcUa()
    failing_client.raise_on_value = True
    failure_messages = _run_effect(NodeSelected(node_id=node_id), failing_client)
    assert isinstance(failure_messages[0], NodeInspectionStarted)
    assert isinstance(failure_messages[1], NodeInspectionFailed)
    assert failure_messages[1].error_ref is not None


def test_effects_node_write_success_and_failure() -> None:
    node_id = "ns=2;s=Temperature"
    client = FakeOpcUa()

    success_messages = _run_effect(
        NodeWriteRequested(node_id=node_id, value_text="42", variant_hint="Int32"), client
    )
    assert isinstance(success_messages[0], NodeWriteStarted)
    assert isinstance(success_messages[1], NodeValueLoaded)
    assert isinstance(success_messages[2], NodeWriteSucceeded)
    assert client.last_write == (node_id, "42", "Int32")

    failing_client = FakeOpcUa()
    failing_client.raise_on_write = True
    failure_messages = _run_effect(
        NodeWriteRequested(node_id=node_id, value_text="42", variant_hint="Int32"), failing_client
    )
    assert isinstance(failure_messages[0], NodeWriteStarted)
    assert isinstance(failure_messages[1], NodeWriteFailed)
    assert failure_messages[1].error_ref is not None


def test_effects_logs_exception_context_with_error_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    params = ConnectParams(endpoint="opc.tcp://localhost:4840")
    failing_client = FakeOpcUa()
    failing_client.raise_on_connect = True
    captured: dict[str, object] = {}

    def fake_exception(_message: str, *, extra: dict[str, object]) -> None:
        captured.update(extra)

    monkeypatch.setattr("opcua_tui.app.effects.logger.exception", fake_exception)
    failure_messages = _run_effect(ConnectRequested(params=params), failing_client)

    assert isinstance(failure_messages[1], ConnectionFailed)
    assert failure_messages[1].error_ref is not None
    assert captured["operation"] == "connect"
    assert captured["endpoint"] == params.endpoint
    assert captured["error_ref"] == failure_messages[1].error_ref

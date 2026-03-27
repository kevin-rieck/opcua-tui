import asyncio

from opcua_tui.app.bootstrap import build_store
from opcua_tui.app.messages import ConnectRequested, RootBrowseRequested
from opcua_tui.app.store import Store
from opcua_tui.domain.models import ConnectParams, NodeRef, ServerInfo, SessionInfo
from opcua_tui.infrastructure.opcua.stub_client import StubOpcUaClientAdapter


def test_build_store_returns_wired_store() -> None:
    store = build_store()
    assert isinstance(store, Store)


def test_build_store_connect_and_browse_flow_updates_state(monkeypatch) -> None:
    async def fake_connect(_self, params: ConnectParams) -> SessionInfo:
        return SessionInfo(
            session_id="s-1",
            endpoint=params.endpoint,
            server=ServerInfo(application_name="Fake OPC UA"),
        )

    async def fake_browse_children(_self, node_id: str | None) -> list[NodeRef]:
        if node_id is None:
            return [
                NodeRef(
                    node_id="i=85", display_name="Objects", node_class="Object", has_children=True
                )
            ]
        return []

    monkeypatch.setattr(StubOpcUaClientAdapter, "connect", fake_connect)
    monkeypatch.setattr(StubOpcUaClientAdapter, "browse_children", fake_browse_children)

    async def scenario() -> None:
        store = build_store()

        await store.dispatch(
            ConnectRequested(params=ConnectParams(endpoint="opc.tcp://example:4840"))
        )
        await store.dispatch(RootBrowseRequested())

        assert store.state.session.status == "connected"
        assert store.state.session.session is not None
        assert store.state.session.session.endpoint == "opc.tcp://example:4840"
        assert len(store.state.browser.roots) > 0

    asyncio.run(scenario())

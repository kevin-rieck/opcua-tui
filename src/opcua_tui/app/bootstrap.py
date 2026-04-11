from __future__ import annotations

from opcua_tui.application.ports.opcua_client import OpcUaClientPort
from opcua_tui.app.effects import Effects
from opcua_tui.app.reducer import reduce
from opcua_tui.app.store import Store
from opcua_tui.domain.models import AppState
from opcua_tui.infrastructure.opcua.stub_client import StubOpcUaClientAdapter


def build_store(opcua: OpcUaClientPort | None = None) -> Store:
    state = AppState()
    opcua_client: OpcUaClientPort = opcua or StubOpcUaClientAdapter()

    store: Store | None = None
    effects: Effects | None = None

    async def effect_handler(message: object) -> None:
        assert effects is not None
        await effects.handle(message)

    store = Store(initial_state=state, reducer=reduce, effect_handler=effect_handler)
    effects = Effects(dispatch=store.dispatch, opcua=opcua_client)
    return store

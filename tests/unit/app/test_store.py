import asyncio

import pytest

from opcua_tui.app.store import Store
from opcua_tui.domain.models import AppState, UiState


def test_store_dispatch_reduces_notifies_subscribers_then_runs_effect() -> None:
    async def scenario() -> None:
        order: list[str] = []
        seen_status: list[str] = []

        def reducer(_state: AppState, message: object) -> AppState:
            order.append(f"reduce:{message}")
            return AppState(ui=UiState(status_text=str(message)))

        async def effect_handler(message: object) -> None:
            order.append(f"effect:{message}")

        store = Store(initial_state=AppState(), reducer=reducer, effect_handler=effect_handler)
        store.subscribe(lambda state: seen_status.append(state.ui.status_text))

        await store.dispatch("hello")

        assert store.state.ui.status_text == "hello"
        assert seen_status == ["hello"]
        assert order == ["reduce:hello", "effect:hello"]

    asyncio.run(scenario())


def test_store_dispatch_notifies_each_subscriber_for_each_message() -> None:
    async def scenario() -> None:
        calls: list[str] = []

        def reducer(_state: AppState, message: object) -> AppState:
            return AppState(ui=UiState(status_text=str(message)))

        async def effect_handler(_message: object) -> None:
            return None

        store = Store(initial_state=AppState(), reducer=reducer, effect_handler=effect_handler)
        store.subscribe(lambda state: calls.append(f"s1:{state.ui.status_text}"))
        store.subscribe(lambda state: calls.append(f"s2:{state.ui.status_text}"))

        await store.dispatch("first")
        await store.dispatch("second")

        assert calls == ["s1:first", "s2:first", "s1:second", "s2:second"]

    asyncio.run(scenario())


def test_store_dispatch_logs_and_reraises_effect_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        captured: dict[str, object] = {}

        def reducer(_state: AppState, message: object) -> AppState:
            return AppState(ui=UiState(status_text=str(message)))

        async def effect_handler(_message: object) -> None:
            raise RuntimeError("boom")

        def fake_exception(_message: str, *, extra: dict[str, object]) -> None:
            captured.update(extra)

        monkeypatch.setattr("opcua_tui.app.store.logger.exception", fake_exception)

        store = Store(initial_state=AppState(), reducer=reducer, effect_handler=effect_handler)

        with pytest.raises(RuntimeError, match="boom"):
            await store.dispatch("hello")

        assert captured["operation"] == "store_effect"
        assert captured["message_type"] == "str"

    asyncio.run(scenario())

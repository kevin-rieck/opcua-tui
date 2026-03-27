from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from opcua_tui.domain.models import AppState

Reducer = Callable[[AppState, object], AppState]
Subscriber = Callable[[AppState], None]
EffectHandler = Callable[[object], Awaitable[None]]
logger = logging.getLogger(__name__)


class Store:
    def __init__(
        self, initial_state: AppState, reducer: Reducer, effect_handler: EffectHandler
    ) -> None:
        self._state = initial_state
        self._reducer = reducer
        self._effect_handler = effect_handler
        self._subscribers: list[Subscriber] = []
        self._lock = asyncio.Lock()

    @property
    def state(self) -> AppState:
        return self._state

    def subscribe(self, fn: Subscriber) -> None:
        self._subscribers.append(fn)

    async def dispatch(self, message: object) -> None:
        message_type = type(message).__name__
        async with self._lock:
            try:
                self._state = self._reducer(self._state, message)
            except Exception:
                logger.exception(
                    "Reducer failed during dispatch",
                    extra={"operation": "store_reduce", "message_type": message_type},
                )
                raise

            for sub in self._subscribers:
                try:
                    sub(self._state)
                except Exception:
                    logger.exception(
                        "Subscriber failed during dispatch",
                        extra={
                            "operation": "store_subscriber",
                            "message_type": message_type,
                            "subscriber": getattr(sub, "__name__", sub.__class__.__name__),
                        },
                    )
                    raise

        try:
            await self._effect_handler(message)
        except Exception:
            logger.exception(
                "Effect handler failed during dispatch",
                extra={"operation": "store_effect", "message_type": message_type},
            )
            raise

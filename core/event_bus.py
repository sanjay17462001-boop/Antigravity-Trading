"""
Antigravity Trading — Async Event Bus
Lightweight pub/sub system for decoupled communication between
data feeds, strategies, and execution engines.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

logger = logging.getLogger("antigravity.events")

# Type for event handlers
EventHandler = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    """
    In-process async pub/sub event bus.
    
    Topics:
        tick        — Real-time tick data
        candle      — New candle formed
        signal      — Strategy signal emitted
        order       — Order state change
        fill        — Order filled
        position    — Position update
        risk        — Risk alert
        error       — System error
        heartbeat   — System health pulse
    """

    def __init__(self):
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._running = False

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Subscribe a coroutine handler to a topic."""
        self._subscribers[topic].append(handler)
        logger.debug(f"Subscribed {handler.__qualname__} to '{topic}'")

    def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        """Remove a handler from a topic."""
        if handler in self._subscribers[topic]:
            self._subscribers[topic].remove(handler)
            logger.debug(f"Unsubscribed {handler.__qualname__} from '{topic}'")

    async def publish(self, topic: str, data: Any = None) -> None:
        """
        Publish data to all subscribers of a topic.
        Each handler is called concurrently via asyncio.gather.
        Failed handlers are logged but don't crash the bus.
        """
        handlers = self._subscribers.get(topic, [])
        if not handlers:
            return

        tasks = []
        for handler in handlers:
            tasks.append(self._safe_call(handler, topic, data))

        await asyncio.gather(*tasks)

    async def _safe_call(self, handler: EventHandler, topic: str, data: Any) -> None:
        """Call a handler with error isolation."""
        try:
            await handler(data)
        except Exception as e:
            logger.error(
                f"Event handler {handler.__qualname__} failed on '{topic}': {e}",
                exc_info=True,
            )

    def clear(self, topic: str | None = None) -> None:
        """Clear all subscribers for a topic, or all topics if None."""
        if topic:
            self._subscribers[topic].clear()
        else:
            self._subscribers.clear()

    @property
    def topics(self) -> list[str]:
        """List all active topics."""
        return list(self._subscribers.keys())

    def subscriber_count(self, topic: str) -> int:
        return len(self._subscribers.get(topic, []))


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus

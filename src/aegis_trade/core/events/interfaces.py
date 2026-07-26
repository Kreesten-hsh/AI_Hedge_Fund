from typing import Protocol, Iterator, runtime_checkable
from aegis_trade.core.events.domain import DomainEvent


@runtime_checkable
class EventHandler(Protocol):
    def handle(self, event: DomainEvent) -> None:
        """Handles a dispatched domain event."""
        ...


@runtime_checkable
class EventPublisher(Protocol):
    def publish(self, event: DomainEvent) -> None:
        """Publishes an event to the bus."""
        ...


@runtime_checkable
class EventSubscriber(Protocol):
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribes a handler to a specific event type."""
        ...
        
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribes a handler from a specific event type."""
        ...


@runtime_checkable
class EventBus(EventPublisher, EventSubscriber, Protocol):
    """
    A central event bus for publishing and subscribing to events.
    """
    def clear(self) -> None:
        """Removes all subscribers and resets the bus state."""
        ...


@runtime_checkable
class EventStore(Protocol):
    """
    Protocol for persisting and loading events.
    (Implementation is intentionally deferred to Phase E - PR #2).
    """
    def append(self, event: DomainEvent) -> None:
        """Appends an event to the store."""
        ...
        
    def load_stream(self, stream_id: str) -> Iterator[DomainEvent]:
        """Loads a specific stream of events."""
        ...

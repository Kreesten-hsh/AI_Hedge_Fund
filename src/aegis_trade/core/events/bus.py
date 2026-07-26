from collections import defaultdict
from typing import Dict, List

from aegis_trade.core.events.domain import DomainEvent
from aegis_trade.core.events.interfaces import EventBus, EventHandler


class InMemoryEventBus(EventBus):
    """
    A synchronous, in-memory implementation of the EventBus.
    This bus does not perform logging, persisting, or replay. It solely
    dispatches events to registered handlers.
    """
    
    def __init__(self):
        # We use a list to preserve insertion/subscription order
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            
    def publish(self, event: DomainEvent) -> None:
        # Dispatch to all handlers registered for the exact event_type
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            handler.handle(event)
            
    def clear(self) -> None:
        self._handlers.clear()

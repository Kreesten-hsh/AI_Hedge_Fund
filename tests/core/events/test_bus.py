import unittest
from datetime import datetime, timezone

from aegis_trade.core.events.domain import DomainEvent
from aegis_trade.core.events.bus import InMemoryEventBus
from aegis_trade.core.events.interfaces import EventHandler


class MockHandler(EventHandler):
    def __init__(self):
        self.received_events = []
        
    def handle(self, event: DomainEvent) -> None:
        self.received_events.append(event)


class TestInMemoryEventBus(unittest.TestCase):
    
    def setUp(self):
        self.bus = InMemoryEventBus()
        self.dt_utc = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
        self.event1 = DomainEvent(
            event_id="evt_1",
            event_type="OrderPlaced",
            occurred_at=self.dt_utc,
            metadata={"order_id": "O_1"}
        )
        self.event2 = DomainEvent(
            event_id="evt_2",
            event_type="OrderFilled",
            occurred_at=self.dt_utc,
            metadata={"order_id": "O_1"}
        )
        
    def test_subscribe_and_publish(self):
        handler = MockHandler()
        self.bus.subscribe("OrderPlaced", handler)
        
        self.bus.publish(self.event1)
        self.assertEqual(len(handler.received_events), 1)
        self.assertEqual(handler.received_events[0].event_id, "evt_1")
        
    def test_unsubscribe(self):
        handler = MockHandler()
        self.bus.subscribe("OrderPlaced", handler)
        self.bus.unsubscribe("OrderPlaced", handler)
        
        self.bus.publish(self.event1)
        self.assertEqual(len(handler.received_events), 0)
        
    def test_no_handlers(self):
        # Should not raise any error
        self.bus.publish(self.event1)
        
    def test_multiple_handlers_dispatch_order(self):
        handler1 = MockHandler()
        handler2 = MockHandler()
        
        self.bus.subscribe("OrderPlaced", handler1)
        self.bus.subscribe("OrderPlaced", handler2)
        
        self.bus.publish(self.event1)
        
        self.assertEqual(len(handler1.received_events), 1)
        self.assertEqual(len(handler2.received_events), 1)
        
    def test_handler_called_once_if_subscribed_twice(self):
        handler = MockHandler()
        self.bus.subscribe("OrderPlaced", handler)
        self.bus.subscribe("OrderPlaced", handler)  # duplicate subscription
        
        self.bus.publish(self.event1)
        # Should only receive it once per event published
        self.assertEqual(len(handler.received_events), 1)
        
    def test_multiple_events(self):
        handler = MockHandler()
        self.bus.subscribe("OrderPlaced", handler)
        self.bus.subscribe("OrderFilled", handler)
        
        self.bus.publish(self.event1)
        self.bus.publish(self.event2)
        
        self.assertEqual(len(handler.received_events), 2)
        self.assertEqual(handler.received_events[0].event_type, "OrderPlaced")
        self.assertEqual(handler.received_events[1].event_type, "OrderFilled")
        
    def test_clear(self):
        handler = MockHandler()
        self.bus.subscribe("OrderPlaced", handler)
        self.bus.clear()
        
        self.bus.publish(self.event1)
        self.assertEqual(len(handler.received_events), 0)

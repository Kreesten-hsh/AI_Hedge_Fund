import unittest


from aegis_trade.core.events.interfaces import (
    EventBus,
    EventHandler,
    EventPublisher,
    EventSubscriber,
    EventStore
)
from aegis_trade.core.events.bus import InMemoryEventBus


class TestInterfaces(unittest.TestCase):
    
    def test_in_memory_bus_implements_protocols(self):
        self.assertTrue(issubclass(InMemoryEventBus, EventBus))
        self.assertTrue(issubclass(InMemoryEventBus, EventPublisher))
        self.assertTrue(issubclass(InMemoryEventBus, EventSubscriber))
        
    def test_protocols_are_abstract(self):
        # Protocols should not be directly instantiable
        with self.assertRaises(TypeError):
            EventBus()
            
        with self.assertRaises(TypeError):
            EventHandler()
            
        with self.assertRaises(TypeError):
            EventStore()

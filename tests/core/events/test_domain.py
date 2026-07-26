import unittest
from datetime import datetime, timezone, timedelta
from dataclasses import FrozenInstanceError

from aegis_trade.core.events.domain import DomainEvent
from aegis_trade.core.events.exceptions import EventValidationError


class TestDomainEvent(unittest.TestCase):
    
    def setUp(self):
        self.dt_utc = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    
    def test_immutability(self):
        event = DomainEvent(
            event_id="evt_123",
            event_type="test_event",
            occurred_at=self.dt_utc,
            metadata={"key": "value"}
        )
        with self.assertRaises(FrozenInstanceError):
            event.event_id = "evt_456"
            
    def test_utc_enforcement_missing_tz(self):
        dt_naive = datetime(2026, 7, 24, 12, 0, 0)
        with self.assertRaisesRegex(EventValidationError, "must be timezone-aware"):
            DomainEvent(
                event_id="evt_123",
                event_type="test",
                occurred_at=dt_naive,
                metadata={}
            )
            
    def test_utc_enforcement_wrong_tz(self):
        dt_est = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone(timedelta(hours=-5)))
        with self.assertRaisesRegex(EventValidationError, "strictly in UTC"):
            DomainEvent(
                event_id="evt_123",
                event_type="test",
                occurred_at=dt_est,
                metadata={}
            )
            
    def test_hash_is_deterministic(self):
        event1 = DomainEvent(
            event_id="evt_123",
            event_type="test",
            occurred_at=self.dt_utc,
            metadata={"b": 2, "a": 1}
        )
        event2 = DomainEvent(
            event_id="evt_123",
            event_type="test",
            occurred_at=self.dt_utc,
            metadata={"a": 1, "b": 2}
        )
        self.assertEqual(event1.hash, event2.hash)
        
    def test_hash_differs_on_content(self):
        event1 = DomainEvent(
            event_id="evt_123",
            event_type="test",
            occurred_at=self.dt_utc,
            metadata={"a": 1}
        )
        event2 = DomainEvent(
            event_id="evt_123",
            event_type="test",
            occurred_at=self.dt_utc,
            metadata={"a": 2}
        )
        self.assertNotEqual(event1.hash, event2.hash)
        
    def test_equality(self):
        event1 = DomainEvent(
            event_id="evt_123",
            event_type="test",
            occurred_at=self.dt_utc,
            metadata={"a": 1}
        )
        event2 = DomainEvent(
            event_id="evt_123",
            event_type="test",
            occurred_at=self.dt_utc,
            metadata={"a": 1}
        )
        self.assertEqual(event1, event2)
        
    def test_metadata_not_serializable(self):
        class NonSerializable:
            pass
            
        with self.assertRaisesRegex(EventValidationError, "must be JSON serializable"):
            DomainEvent(
                event_id="evt_123",
                event_type="test",
                occurred_at=self.dt_utc,
                metadata={"obj": NonSerializable()}
            )
            
    def test_missing_fields(self):
        with self.assertRaisesRegex(EventValidationError, "event_id cannot be empty"):
            DomainEvent(
                event_id="",
                event_type="test",
                occurred_at=self.dt_utc,
                metadata={}
            )
        with self.assertRaisesRegex(EventValidationError, "event_type cannot be empty"):
            DomainEvent(
                event_id="evt_1",
                event_type="",
                occurred_at=self.dt_utc,
                metadata={}
            )

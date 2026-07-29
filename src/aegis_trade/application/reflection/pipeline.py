import logging
from decimal import Decimal

from aegis_trade.core.events.interfaces import EventBus, EventHandler
from aegis_trade.domain.core import Side, TimeFrame
from aegis_trade.engine.events import (
    ExperienceSavedEvent,
    ExperienceRejectedEvent,
    MarketEvent,
    PositionEvent,
    TradeEvent
)
from aegis_trade.application.memory.manager import MemoryManager
from aegis_trade.application.reflection.builder import ExperienceBuilder
from aegis_trade.application.reflection.extractor import LiveFeatureExtractor
from aegis_trade.application.reflection.observer import TradeObserver
from aegis_trade.application.reflection.snapshot import MarketSnapshotBuilder


logger = logging.getLogger("ReflectionPipeline")


class ReflectionPipeline(EventHandler):
    """
    Coordinates the reflection process from trade closed to memory saved.
    Hooks into the EventBus.
    """
    def __init__(
        self,
        event_bus: EventBus,
        memory_manager: MemoryManager,
        experience_builder: ExperienceBuilder,
    ):
        self._event_bus = event_bus
        self._memory_manager = memory_manager
        self._builder = experience_builder
        
        self._snapshot_builder = MarketSnapshotBuilder()
        self._extractor = LiveFeatureExtractor()
        self._observer = TradeObserver()
        
        # Subscribe to events
        self._event_bus.subscribe("market", self)
        self._event_bus.subscribe("position", self)
        self._event_bus.subscribe("trade", self)

    def handle(self, event) -> None:
        if event.event_type == "market":
            self._on_market_event(event)
        elif event.event_type == "position":
            self._on_position_event(event)
        elif event.event_type == "trade":
            self._on_trade_event(event)

    def _on_market_event(self, event: MarketEvent) -> None:
        self._snapshot_builder.on_market_event(event)
        
    def _on_position_event(self, event: PositionEvent) -> None:
        if event.action == "opened":
            snapshot = self._snapshot_builder.get_snapshot(event.symbol)
            if snapshot:
                self._observer.on_position_opened(event, snapshot)
            else:
                logger.warning(f"No snapshot available when position opened for {event.symbol}")
        elif event.action == "updated":
            # Pass current price from latest snapshot if needed, or from event if available
            pass
            
    def _on_trade_event(self, event: TradeEvent) -> None:
        if event.action == "closed":
            observation = self._observer.on_trade_closed(event)
            if not observation:
                msg = f"No observation found for closed trade on {event.symbol}"
                logger.warning(msg)
                self._event_bus.publish(ExperienceRejectedEvent(
                    timestamp=event.timestamp,
                    reason=msg
                ))
                return

            try:
                # 1. Extract features from entry snapshot
                features = self._extractor.extract(observation.entry_snapshot)
                
                # 2. Calculate metrics (Duration, Drawdown)
                duration = int((event.timestamp - observation.opened_at).total_seconds())
                max_drawdown = Decimal(str(observation.max_drawdown_tracked))
                
                metadata = {"trade_id": event.trade_id}
                if event.exit_reason:
                    metadata["exit_reason"] = event.exit_reason.value
                
                # 3. Build Experience (Assuming default Side and TimeFrame for now, as TradeEvent lacks them)
                # In a real scenario, Side and TimeFrame should come from TradeObservation
                experience = self._builder.build(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    timeframe=TimeFrame.M5,  # Mocked default
                    decision_side=Side.LONG, # Mocked default
                    features=features,
                    pnl=event.realized_pnl,
                    max_drawdown=max_drawdown,
                    duration_seconds=duration,
                    metadata=metadata
                )
                
                # 4. Save to MemoryManager
                exp_id = self._memory_manager.save_experience(experience)
                
                # 5. Emit Audit Event
                self._event_bus.publish(ExperienceSavedEvent(
                    timestamp=event.timestamp,
                    experience_id=exp_id,
                    category=experience.category,
                    pnl=experience.pnl
                ))
                
            except Exception as e:
                logger.error(f"Failed to process reflection for trade {event.trade_id}: {e}")
                self._event_bus.publish(ExperienceRejectedEvent(
                    timestamp=event.timestamp,
                    reason=str(e)
                ))

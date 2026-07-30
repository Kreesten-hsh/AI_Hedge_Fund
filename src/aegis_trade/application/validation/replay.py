import asyncio
import random
import psutil
import os
import logging
from typing import AsyncIterable, Callable, Awaitable

from aegis_trade.domain.core import Tick

logger = logging.getLogger(__name__)

class TickReplayEngine:
    """
    Replays historical ticks at accelerated speed while simulating real-world execution conditions
    such as network latency, and monitoring memory consumption to detect leaks.
    """
    def __init__(self, speed_factor: float = 100.0, latency_ms_min: int = 1, latency_ms_max: int = 50):
        self.speed_factor = speed_factor
        self.latency_ms_min = latency_ms_min
        self.latency_ms_max = latency_ms_max
        self._process = psutil.Process(os.getpid())
        
    async def run(self, tick_stream: AsyncIterable[Tick], callback: Callable[[Tick], Awaitable[None]]) -> None:
        """
        Replays the tick stream, firing the callback for each tick after a simulated latency delay.
        Tracks memory usage.
        
        Args:
            tick_stream: Async iterator of historical ticks.
            callback: Async function to call with each tick.
        """
        start_memory = self._get_memory_mb()
        peak_memory = start_memory
        tick_count = 0
        
        async for tick in tick_stream:
            # Simulate latency
            latency_ms = random.randint(self.latency_ms_min, self.latency_ms_max)
            # Scale latency by speed factor (e.g., 50ms at 100x is 0.5ms real wait)
            sleep_time = (latency_ms / 1000.0) / self.speed_factor
            
            await asyncio.sleep(sleep_time)
            await callback(tick)
            
            tick_count += 1
            if tick_count % 1000 == 0:
                current_memory = self._get_memory_mb()
                peak_memory = max(peak_memory, current_memory)
                
        end_memory = self._get_memory_mb()
        memory_diff = end_memory - start_memory
        
        logger.info(f"Replay completed. Ticks processed: {tick_count}")
        logger.info(f"Memory Check: Start={start_memory:.2f}MB, End={end_memory:.2f}MB, Peak={peak_memory:.2f}MB, Leakage~={memory_diff:.2f}MB")
        
        if memory_diff > 50.0:  # arbitrary 50MB warning threshold
            logger.warning(f"Potential memory leak detected during replay! ({memory_diff:.2f}MB increase)")

    def _get_memory_mb(self) -> float:
        return self._process.memory_info().rss / (1024 * 1024)

import hashlib
from typing import Sequence
from aegis_trade.domain import MarketBar, Symbol, TimeFrame

def compute_dataset_hash(
    symbol: Symbol, 
    timeframe: TimeFrame | None, 
    bars: Sequence[MarketBar]
) -> str:
    """
    Computes a deterministic SHA-256 hash for a sequence of MarketBars.
    The canonical representation is:
    SYMBOL|TIMEFRAME
    TIMESTAMP_ISO8601_UTC|OPEN|HIGH|LOW|CLOSE|VOLUME
    """
    hasher = hashlib.sha256()
    
    tf_str = timeframe.value if timeframe else "NONE"
    header = f"{symbol.name}|{symbol.asset_class.value}|{tf_str}\n"
    hasher.update(header.encode('utf-8'))
    
    for bar in bars:
        ts = bar.timestamp.isoformat()
        line = f"{ts}|{bar.open}|{bar.high}|{bar.low}|{bar.close}|{bar.volume}\n"
        hasher.update(line.encode('utf-8'))
        
    return hasher.hexdigest()

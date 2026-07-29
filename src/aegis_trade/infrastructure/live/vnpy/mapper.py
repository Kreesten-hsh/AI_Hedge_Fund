from aegis_trade.domain.core import Symbol

class VnPySymbolMapper:
    """
    Translates Aegis generic symbols to vn.py specific gateway symbols.
    For example: BTCUSDT -> BTCUSDT.BINANCE
    """
    def __init__(self, default_exchange: str):
        self.default_exchange = default_exchange
        
    def to_vnpy_symbol(self, aegis_symbol: Symbol) -> str:
        # Depending on the broker/gateway, vn.py usually uses format 'symbol.EXCHANGE'
        # e.g., 'AAPL.SMART', 'BTCUSDT.BINANCE'
        return f"{aegis_symbol.name}.{self.default_exchange}"

    def from_vnpy_symbol(self, vnpy_symbol: str) -> Symbol:
        # e.g., 'BTCUSDT.BINANCE' -> Symbol(name='BTCUSDT', ...)
        parts = vnpy_symbol.split(".")
        if len(parts) >= 1:
            name = parts[0]
            # Assumes base symbol parsing or looking up in a catalog
            return Symbol(name=name, asset_class="CRYPTO") # simplified, in real we need a lookup table
        raise ValueError(f"Invalid vnpy symbol format: {vnpy_symbol}")

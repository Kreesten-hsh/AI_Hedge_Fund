import os
import time
from typing import Sequence
import MetaTrader5 as mt5 # type: ignore

from aegis_trade.domain import Symbol, TimeFrame, MarketBar, Tick, HealthStatus
from aegis_trade.providers.normalization import MT5DataNormalizer
from aegis_trade.providers.validation import StrictDataValidator
from aegis_trade.core.exceptions import DataFetchError

class MT5Provider:
    """
    Fournisseur de données via MetaTrader 5.
    S'occupe de l'extraction, puis délègue la normalisation et la validation.
    """

    def __init__(self):
        self.normalizer = MT5DataNormalizer()
        self.validator = StrictDataValidator()
        self.initialized = False

    def _ensure_connected(self):
        if not self.initialized:
            login_str = os.environ.get("MT5_LOGIN")
            password = os.environ.get("MT5_PASSWORD")
            server = os.environ.get("MT5_SERVER")
            path = os.environ.get("MT5_TERMINAL_PATH")

            init_kwargs = {}
            if path: 
                init_kwargs["path"] = path

            # 1. Initialiser le terminal sans credentials
            if not mt5.initialize(**init_kwargs):
                raise Exception(f"MT5 init failed: {mt5.last_error()} (Path: {path})")
                
            # 4. Afficher le terminal utilisé
            print(f"MT5 Terminal Info: {mt5.terminal_info()}")
            
            # 2. Vérifier si la session est déjà active sur le bon compte
            account_info = mt5.account_info()
            expected_login = int(login_str) if login_str else None
            
            is_connected_to_correct_account = (
                account_info is not None and 
                expected_login is not None and 
                account_info.login == expected_login
            )
            
            if not is_connected_to_correct_account:
                # 3. S'authentifier explicitement si nécessaire
                if login_str and password and server:
                    if not mt5.login(login=expected_login, password=password, server=server):
                        error_code = mt5.last_error()
                        raise Exception(f"MT5 login failed: {error_code} for account {expected_login} on {server}")

            self.initialized = True

    def _get_mt5_timeframe(self, timeframe: TimeFrame) -> int:
        mapping = {
            TimeFrame.M1: mt5.TIMEFRAME_M1,
            TimeFrame.M5: mt5.TIMEFRAME_M5,
            TimeFrame.M15: mt5.TIMEFRAME_M15,
            TimeFrame.M30: mt5.TIMEFRAME_M30,
            TimeFrame.H1: mt5.TIMEFRAME_H1,
            TimeFrame.H4: mt5.TIMEFRAME_H4,
            TimeFrame.D1: mt5.TIMEFRAME_D1,
        }
        if timeframe not in mapping:
            raise ValueError(f"Unsupported timeframe for MT5: {timeframe}")
        return mapping[timeframe]

    def health_check(self) -> HealthStatus:
        start_time = time.perf_counter()
        try:
            self._ensure_connected()
            info = mt5.terminal_info()
            if info is None:
                raise Exception(f"Terminal info is None. {mt5.last_error()}")
            latency = time.perf_counter() - start_time
            return HealthStatus(
                connected=True,
                latency=latency,
                provider="mt5",
                version=f"{info.build}",
                last_error=None
            )
        except Exception as e:
            return HealthStatus(
                connected=False,
                latency=0.0,
                provider="mt5",
                version="unknown",
                last_error=str(e)
            )

    def get_bars(self, symbol: Symbol, timeframe: TimeFrame, limit: int) -> Sequence[MarketBar]:
        self._ensure_connected()
        mt5_tf = self._get_mt5_timeframe(timeframe)

        # Extraction
        rates = mt5.copy_rates_from_pos(symbol.name, mt5_tf, 0, limit)
        if rates is None or len(rates) == 0:
            raise DataFetchError(f"Failed to fetch rates for {symbol.name}. Error: {mt5.last_error()}")

        # Normalization
        normalized_bars = self.normalizer.normalize_bars(rates, symbol, timeframe)

        # Validation
        validated_bars = self.validator.validate_bars(normalized_bars)

        return validated_bars

    def get_bars_range(self, symbol: Symbol, timeframe: TimeFrame, date_from, date_to) -> Sequence[MarketBar]:
        self._ensure_connected()
        mt5_tf = self._get_mt5_timeframe(timeframe)

        # Extraction
        rates = mt5.copy_rates_range(symbol.name, mt5_tf, date_from, date_to)
        if rates is None or len(rates) == 0:
            raise DataFetchError(f"Failed to fetch rates for {symbol.name} between {date_from} and {date_to}. Error: {mt5.last_error()}")

        # Normalization
        normalized_bars = self.normalizer.normalize_bars(rates, symbol, timeframe)

        # Validation
        validated_bars = self.validator.validate_bars(normalized_bars)

        return validated_bars

    def get_ticks(self, symbol: Symbol, limit: int) -> Sequence[Tick]:
        self._ensure_connected()

        # Extraction
        ticks = mt5.copy_ticks_from(symbol.name, 0, limit, mt5.COPY_TICKS_ALL)
        if ticks is None or len(ticks) == 0:
            raise DataFetchError(f"Failed to fetch ticks for {symbol.name}. Error: {mt5.last_error()}")

        # Normalization
        normalized_ticks = self.normalizer.normalize_ticks(ticks, symbol)

        # Validation
        validated_ticks = self.validator.validate_ticks(normalized_ticks)

        return validated_ticks

"""Provider de données macroéconomiques FRED via fredapi.

Permet d'extraire les séries macroéconomiques de la Réserve Fédérale de St. Louis (FRED),
notamment les taux réels 10 ans (DFII10), élément clé pour la modélisation de l'Or.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence

import pandas as pd
from fredapi import Fred

from aegis_trade.domain.core import AssetClass, EconomicIndicator, Symbol
from aegis_trade.domain.exceptions.data import DataProviderError

logger = logging.getLogger(__name__)


class FredDataProvider:
    """Provider d'indicateurs macroéconomiques s'appuyant sur la bibliothèque `fredapi`.

    Récupère des séries macro fondamentales comme `DFII10` (Taux Réel 10 ans US - TIPS).
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("FRED_API_KEY")
        if not self.api_key:
            logger.warning(
                "Clé FRED_API_KEY non fournie. Les appels vers l'API FRED échoueront sans clé valide."
            )
            self._fred: Fred | None = None
        else:
            self._fred = Fred(api_key=self.api_key)

    def fetch_series(
        self,
        series_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> pd.Series:
        """Récupère une série brute Pandas depuis FRED."""
        if not self._fred:
            raise DataProviderError(
                "FRED API key non configurée. Définir FRED_API_KEY dans les variables d'environnement."
            )
        try:
            series = self._fred.get_series(
                series_id,
                observation_start=start_date.strftime("%Y-%m-%d") if start_date else None,
                observation_end=end_date.strftime("%Y-%m-%d") if end_date else None,
            )
            if series.empty:
                logger.warning(f"FRED a retourné une série vide pour ID={series_id}")
            return series
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la série FRED {series_id}: {e}")
            raise DataProviderError(f"FRED API Error pour {series_id}: {e}") from e

    def fetch_macro(
        self,
        symbol: Symbol,
        start: datetime,
        end: datetime,
    ) -> Sequence[EconomicIndicator]:
        """Récupère des indicateurs macro au format du domaine Aegis."""
        series_data = self.fetch_series(symbol.name, start_date=start, end_date=end)
        indicators: list[EconomicIndicator] = []
        for ts, val in series_data.items():
            if pd.isna(val):
                continue
            # Force UTC timezone
            dt = pd.to_datetime(ts).to_pydatetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            indicators.append(
                EconomicIndicator(
                    symbol=symbol,
                    timestamp=dt,
                    value=Decimal(str(val)),
                )
            )
        return indicators

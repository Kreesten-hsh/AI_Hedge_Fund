import numpy as np

# ---------------------------------------------------------------------------
# Metrics (IC, Rank IC, etc.)
# ---------------------------------------------------------------------------

def pearson_ic(x: np.ndarray, y: np.ndarray) -> float:
    """Pearson correlation between x and y. Returns NaN if degenerate."""
    if len(x) < 3:
        return float("nan")
    std_x, std_y = x.std(), y.std()
    if std_x == 0 or std_y == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def _rank(arr: np.ndarray) -> np.ndarray:
    """Average-rank implementation (handles ties)."""
    temp = arr.argsort()
    ranks = np.empty_like(temp, dtype=float)
    ranks[temp] = np.arange(len(arr), dtype=float)
    # Handle ties by averaging
    for val in np.unique(arr):
        mask = arr == val
        ranks[mask] = ranks[mask].mean()
    return ranks


def spearman_rank_ic(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman rank correlation. Implemented without scipy."""
    if len(x) < 3:
        return float("nan")
    rank_x = _rank(x)
    rank_y = _rank(y)
    return pearson_ic(rank_x, rank_y)


def sliding_ic(features: np.ndarray, returns: np.ndarray, window: int = 10) -> np.ndarray:
    """Rolling Spearman Rank IC with the given window size."""
    n = len(features)
    if n < window:
        return np.array([])
    ics = []
    for i in range(n - window + 1):
        ic = spearman_rank_ic(features[i:i + window], returns[i:i + window])
        ics.append(ic)
    return np.array(ics)


# ---------------------------------------------------------------------------
# Indicators — SINGLE SOURCE OF AUTHORITY (Lot 3, souveraineté numérique)
#
# Ce module fait autorité pour le True Range, le lissage de Wilder et l'ATR.
# Aucun autre module ne recalcule ces grandeurs : `technical_extractor`,
# `reflection/extractor` et `ai_decision_engine` appellent ces fonctions.
#
# Trois formules divergentes coexistaient avant ce lot, mesurées contre la
# référence Wilder 1978 sur 120 barres : `rolling(14).mean()` sur-estimait de
# +6,6 %, une moyenne de `high - low` sans True Range sous-estimait de -9,5 %,
# et un `ewm(alpha=1/14)` sans amorce SMA produisait 14 barres fausses en
# warmup sans NaN pour les signaler. Voir tests/utils/test_indicator_authority.py.
# ---------------------------------------------------------------------------

def compute_ema(prices: np.ndarray, period: int) -> np.ndarray:
    """Compute EMA series over price array."""
    ema = np.empty_like(prices)
    multiplier = 2.0 / (period + 1)
    ema[0] = prices[0]
    for i in range(1, len(prices)):
        ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1]
    return ema


def true_range(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> np.ndarray:
    """True Range series. First element uses high-low only.

    La première barre n'a pas de clôture précédente : son True Range se réduit
    à `high - low`. Le remplacer par un NaN décalerait toute la série d'un
    cran par rapport à l'amorce SMA de Wilder.
    """
    n = len(highs)
    if n == 0:
        return np.empty(0, dtype=float)
    tr = np.empty(n, dtype=float)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr[i] = max(hl, hc, lc)
    return tr


def wilder_smooth(series: np.ndarray, period: int) -> np.ndarray:
    """Wilder's exponential smoothing (used by ATR, ADX, RSI).

    Amorce en moyenne simple des `period` premières valeurs, puis récurrence.
    Les `period - 1` premières positions restent NaN : une valeur y serait
    calculée sur un échantillon incomplet, donc fausse, et rien en aval ne
    saurait la distinguer d'une valeur établie.
    """
    if period < 1:
        raise ValueError(f"period must be >= 1, got {period}")
    n = len(series)
    out = np.full(n, np.nan, dtype=float)
    if n < period:
        return out
    out[period - 1] = series[:period].mean()
    for i in range(period, n):
        out[i] = (out[i - 1] * (period - 1) + series[i]) / period
    return out


def compute_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int) -> np.ndarray:
    """Average True Range (Wilder 1978). Autorité numérique du projet.

    Retourne une série de même longueur que l'entrée, dont les `period - 1`
    premières valeurs sont NaN (warmup explicite).

    Ce module reste une feuille numpy : les appelants pandas convertissent
    (`Series.to_numpy(dtype=float)`) plutôt que d'ajouter pandas ici.
    """
    tr = true_range(highs, lows, closes)
    return wilder_smooth(tr, period)


def compute_adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    """ADX indicator. Returns the ADX series (NaN for warmup bars)."""
    n = len(highs)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)

    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm[i] = up if (up > down and up > 0) else 0.0
        minus_dm[i] = down if (down > up and down > 0) else 0.0

    atr = compute_atr(highs, lows, closes, period)
    smooth_plus = wilder_smooth(plus_dm, period)
    smooth_minus = wilder_smooth(minus_dm, period)

    plus_di = np.where(atr > 0, 100.0 * smooth_plus / atr, 0.0)
    minus_di = np.where(atr > 0, 100.0 * smooth_minus / atr, 0.0)

    di_sum = plus_di + minus_di
    dx = np.where(di_sum > 0, 100.0 * np.abs(plus_di - minus_di) / di_sum, 0.0)

    adx = wilder_smooth(dx, period)
    return adx


def compute_rsi(prices: np.ndarray, period: int = 14) -> float:
    """Compute RSI at the end of the price series."""
    if len(prices) < period + 1:
        return float("nan")
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # Wilder's smoothed average
    avg_gain = gains[:period].mean()
    avg_loss = losses[:period].mean()
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + rs)))

"""
Antigravity Trading — Technical Indicator Library
Wraps pandas-ta with custom additions. All indicators return pandas Series/DataFrame.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger("antigravity.strategy.indicators")


def calculate_indicator(name: str, data: pd.DataFrame, **kwargs) -> pd.Series | pd.DataFrame:
    """
    Universal indicator calculator.
    
    Args:
        name: Indicator name (case-insensitive)
        data: DataFrame with at least: open, high, low, close, volume
        **kwargs: Indicator-specific parameters
        
    Returns:
        Series or DataFrame with indicator values
        
    Supported indicators:
        Trend: sma, ema, wma, dema, tema, supertrend, vwap, adx
        Momentum: rsi, macd, stoch, cci, mfi, roc, willr
        Volatility: atr, bbands, keltner, donchian
        Volume: obv, vwap, ad, cmf
        Custom: candle_pattern, pivot_points, vix_regime
    """
    name = name.lower().strip()

    # Try pandas-ta first
    try:
        import pandas_ta as ta

        # Ensure DataFrame has proper column names
        df = data.copy()
        df.columns = [c.lower() for c in df.columns]

        result = df.ta(kind=name, **kwargs)
        if result is not None and not (isinstance(result, pd.DataFrame) and result.empty):
            return result
    except Exception as e:
        logger.debug("pandas-ta failed for '%s': %s, trying custom...", name, e)

    # Custom implementations
    custom_fn = CUSTOM_INDICATORS.get(name)
    if custom_fn:
        return custom_fn(data, **kwargs)

    raise ValueError(f"Unknown indicator: {name}. Available: {list(CUSTOM_INDICATORS.keys())}")


# ---------------------------------------------------------------------------
# Custom indicator implementations
# ---------------------------------------------------------------------------

def sma(data: pd.DataFrame, length: int = 20, column: str = "close") -> pd.Series:
    """Simple Moving Average."""
    return data[column].rolling(window=length).mean()


def ema(data: pd.DataFrame, length: int = 20, column: str = "close") -> pd.Series:
    """Exponential Moving Average."""
    return data[column].ewm(span=length, adjust=False).mean()


def rsi(data: pd.DataFrame, length: int = 14, column: str = "close") -> pd.Series:
    """Relative Strength Index."""
    delta = data[column].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(span=length, adjust=False).mean()
    avg_loss = loss.ewm(span=length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(
    data: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    column: str = "close",
) -> pd.DataFrame:
    """MACD with signal line and histogram."""
    fast_ema = data[column].ewm(span=fast, adjust=False).mean()
    slow_ema = data[column].ewm(span=slow, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame({
        "MACD": macd_line,
        "Signal": signal_line,
        "Histogram": histogram,
    })


def atr(data: pd.DataFrame, length: int = 14) -> pd.Series:
    """Average True Range."""
    high = data["high"]
    low = data["low"]
    close = data["close"]
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(span=length, adjust=False).mean()


def bollinger_bands(
    data: pd.DataFrame,
    length: int = 20,
    std_dev: float = 2.0,
    column: str = "close",
) -> pd.DataFrame:
    """Bollinger Bands."""
    middle = data[column].rolling(window=length).mean()
    std = data[column].rolling(window=length).std()
    return pd.DataFrame({
        "BB_Upper": middle + (std_dev * std),
        "BB_Middle": middle,
        "BB_Lower": middle - (std_dev * std),
    })


def supertrend(
    data: pd.DataFrame,
    length: int = 10,
    multiplier: float = 3.0,
) -> pd.DataFrame:
    """SuperTrend indicator."""
    hl2 = (data["high"] + data["low"]) / 2
    atr_val = atr(data, length)

    upper_band = hl2 + (multiplier * atr_val)
    lower_band = hl2 - (multiplier * atr_val)

    supertrend = pd.Series(index=data.index, dtype=float)
    direction = pd.Series(index=data.index, dtype=int)

    supertrend.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, len(data)):
        if data["close"].iloc[i] > upper_band.iloc[i - 1]:
            direction.iloc[i] = 1
        elif data["close"].iloc[i] < lower_band.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

            if direction.iloc[i] == 1 and lower_band.iloc[i] < lower_band.iloc[i - 1]:
                lower_band.iloc[i] = lower_band.iloc[i - 1]
            if direction.iloc[i] == -1 and upper_band.iloc[i] > upper_band.iloc[i - 1]:
                upper_band.iloc[i] = upper_band.iloc[i - 1]

        supertrend.iloc[i] = lower_band.iloc[i] if direction.iloc[i] == 1 else upper_band.iloc[i]

    return pd.DataFrame({
        "SuperTrend": supertrend,
        "Direction": direction,
    })


def vwap(data: pd.DataFrame) -> pd.Series:
    """Volume Weighted Average Price (intraday)."""
    typical_price = (data["high"] + data["low"] + data["close"]) / 3
    cumulative_tp_vol = (typical_price * data["volume"]).cumsum()
    cumulative_vol = data["volume"].cumsum()
    return cumulative_tp_vol / cumulative_vol.replace(0, np.nan)


def stochastic(
    data: pd.DataFrame,
    k_length: int = 14,
    d_length: int = 3,
) -> pd.DataFrame:
    """Stochastic Oscillator."""
    lowest_low = data["low"].rolling(window=k_length).min()
    highest_high = data["high"].rolling(window=k_length).max()
    k = 100 * (data["close"] - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = k.rolling(window=d_length).mean()
    return pd.DataFrame({"Stoch_K": k, "Stoch_D": d})


def adx(data: pd.DataFrame, length: int = 14) -> pd.DataFrame:
    """Average Directional Index."""
    high = data["high"]
    low = data["low"]
    close = data["close"]

    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    atr_val = atr(data, length)
    plus_di = 100 * (plus_dm.ewm(span=length, adjust=False).mean() / atr_val)
    minus_di = 100 * (minus_dm.ewm(span=length, adjust=False).mean() / atr_val)

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
    adx_val = dx.ewm(span=length, adjust=False).mean()

    return pd.DataFrame({
        "ADX": adx_val,
        "Plus_DI": plus_di,
        "Minus_DI": minus_di,
    })


def pivot_points(data: pd.DataFrame) -> pd.DataFrame:
    """Classic Pivot Points."""
    pp = (data["high"] + data["low"] + data["close"]) / 3
    r1 = 2 * pp - data["low"]
    s1 = 2 * pp - data["high"]
    r2 = pp + (data["high"] - data["low"])
    s2 = pp - (data["high"] - data["low"])
    return pd.DataFrame({
        "PP": pp, "R1": r1, "S1": s1, "R2": r2, "S2": s2,
    })


def vix_regime(data: pd.DataFrame, low_threshold: float = 15.0, high_threshold: float = 22.0) -> pd.Series:
    """
    VIX regime detection.
    Returns: 'LOW_VOL', 'NORMAL', 'HIGH_VOL' based on VIX levels.
    """
    def classify(val):
        if val < low_threshold:
            return "LOW_VOL"
        elif val > high_threshold:
            return "HIGH_VOL"
        return "NORMAL"

    return data["close"].apply(classify)


def obv(data: pd.DataFrame) -> pd.Series:
    """On Balance Volume."""
    sign = np.sign(data["close"].diff())
    return (sign * data["volume"]).cumsum()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

CUSTOM_INDICATORS = {
    "sma": sma,
    "ema": ema,
    "rsi": rsi,
    "macd": macd,
    "atr": atr,
    "bbands": bollinger_bands,
    "bollinger": bollinger_bands,
    "supertrend": supertrend,
    "vwap": vwap,
    "stochastic": stochastic,
    "stoch": stochastic,
    "adx": adx,
    "pivot_points": pivot_points,
    "vix_regime": vix_regime,
    "obv": obv,
}

"""
indicators.py - テクニカル指標計算モジュール
SMA/EMA、ATR(Wilder方式)、RSI、Donchianチャネルを実装する。
"""

import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    ranges = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1)
    return ranges.max(axis=1)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder方式の平滑化: ATR = (前期ATR×(N-1) + 当期TR) / N"""
    tr = true_range(df)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def donchian_channel(df: pd.DataFrame, period: int) -> pd.DataFrame:
    """当日を含まないN日高値/安値（タートルズSystem1のブレイクアウト判定に使用）"""
    upper = df["high"].shift(1).rolling(window=period, min_periods=period).max()
    lower = df["low"].shift(1).rolling(window=period, min_periods=period).min()
    return pd.DataFrame({"donchian_upper": upper, "donchian_lower": lower})

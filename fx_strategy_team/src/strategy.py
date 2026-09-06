"""
strategy.py - シグナル生成モジュール
ドンチャンチャネル・ブレイクアウト(タートルズSystem1型) + EMAトレンドフィルター。
根拠・出典は fx_strategy_team/README.md の「戦略の根拠」セクションを参照。
"""

import pandas as pd

from . import indicators as ind


class DonchianTrendStrategy:
    def __init__(self, entry_period: int = 20, exit_period: int = 10,
                 trend_fast_ema: int = 50, trend_slow_ema: int = 200,
                 atr_period: int = 14, atr_multiplier: float = 3.0):
        self.entry_period = entry_period
        self.exit_period = exit_period
        self.trend_fast_ema = trend_fast_ema
        self.trend_slow_ema = trend_slow_ema
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        df: date, open, high, low, close の日足データ（date昇順）
        戻り値: 元データに指標・シグナル列を付加したDataFrame
        """
        out = df.copy().reset_index(drop=True)

        out["ema_fast"] = ind.ema(out["close"], self.trend_fast_ema)
        out["ema_slow"] = ind.ema(out["close"], self.trend_slow_ema)
        out["atr"] = ind.atr(out, self.atr_period)

        entry_channel = ind.donchian_channel(out, self.entry_period)
        exit_channel = ind.donchian_channel(out, self.exit_period)
        out["entry_upper"] = entry_channel["donchian_upper"]
        out["entry_lower"] = entry_channel["donchian_lower"]
        out["exit_upper"] = exit_channel["donchian_upper"]
        out["exit_lower"] = exit_channel["donchian_lower"]

        out["trend"] = "neutral"
        out.loc[out["ema_fast"] > out["ema_slow"], "trend"] = "up"
        out.loc[out["ema_fast"] < out["ema_slow"], "trend"] = "down"

        out["entry_signal"] = None
        long_entry = (out["trend"] == "up") & (out["close"] > out["entry_upper"])
        short_entry = (out["trend"] == "down") & (out["close"] < out["entry_lower"])
        out.loc[long_entry, "entry_signal"] = "long"
        out.loc[short_entry, "entry_signal"] = "short"

        out["exit_signal"] = None
        out.loc[out["close"] < out["exit_lower"], "exit_signal"] = "exit_long"
        out.loc[out["close"] > out["exit_upper"], "exit_signal"] = "exit_short"

        return out

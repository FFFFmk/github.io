"""
backtester.py - バックテストエンジン
strategy.py が生成したシグナルとOHLCデータを受け取り、
1トレード1ポジション（両建て・ピラミッディングなし）でトレードをシミュレートする。

注意: これはユーザー自身が用意した実際のヒストリカルデータに対して実行するための
汎用エンジンである。fx_strategy_team に同梱される sample_data は動作確認専用の
架空データであり、ここで算出される成績は実際の相場でのパフォーマンスを示すものではない。
"""

from .risk_manager import PositionSizer, DrawdownManager


class Backtester:
    def __init__(self, position_sizer: PositionSizer, drawdown_manager: DrawdownManager):
        self.position_sizer = position_sizer
        self.drawdown_manager = drawdown_manager

    def run(self, df, initial_equity: float) -> dict:
        equity = initial_equity
        position = None
        trades = []
        equity_curve = []

        for _, row in df.iterrows():
            risk_multiplier = self.drawdown_manager.update(equity)

            if position is not None:
                exit_price = self._check_exit(row, position)
                if exit_price is not None:
                    pnl = self._pnl(position, exit_price)
                    equity += pnl
                    trades.append({
                        "entry_date": position["entry_date"],
                        "exit_date": row["date"],
                        "side": position["side"],
                        "entry_price": position["entry_price"],
                        "exit_price": exit_price,
                        "units": position["units"],
                        "pnl": pnl,
                        "risk_amount": position["risk_amount"],
                        "r_multiple": pnl / position["risk_amount"] if position["risk_amount"] else 0,
                    })
                    position = None

            equity_curve.append({"date": row["date"], "equity": equity})

            if (position is None and row.get("entry_signal") in ("long", "short")
                    and risk_multiplier > 0 and row.get("atr") and row["atr"] > 0):
                position = self._open_position(row, equity, risk_multiplier)

        return {"trades": trades, "equity_curve": equity_curve, "final_equity": equity}

    def _open_position(self, row, equity: float, risk_multiplier: float) -> dict:
        side = row["entry_signal"]
        atr_value = row["atr"]
        units = self.position_sizer.calculate_units(equity, atr_value, risk_multiplier)
        stop_distance = atr_value * self.position_sizer.atr_multiplier
        entry_price = row["close"]
        stop_price = entry_price - stop_distance if side == "long" else entry_price + stop_distance

        return {
            "side": side,
            "entry_date": row["date"],
            "entry_price": entry_price,
            "units": units,
            "stop_price": stop_price,
            "risk_amount": units * stop_distance,
        }

    @staticmethod
    def _check_exit(row, position) -> float:
        side = position["side"]
        if side == "long":
            if row["low"] <= position["stop_price"]:
                return position["stop_price"]
            if row.get("exit_signal") == "exit_long":
                return row["close"]
        else:
            if row["high"] >= position["stop_price"]:
                return position["stop_price"]
            if row.get("exit_signal") == "exit_short":
                return row["close"]
        return None

    @staticmethod
    def _pnl(position, exit_price: float) -> float:
        if position["side"] == "long":
            return (exit_price - position["entry_price"]) * position["units"]
        return (position["entry_price"] - exit_price) * position["units"]


def compute_metrics(result: dict, initial_equity: float) -> dict:
    trades = result["trades"]
    equity_curve = result["equity_curve"]

    if not trades:
        return {
            "total_trades": 0, "win_rate": None, "profit_factor": None,
            "expectancy": None, "max_drawdown_pct": _max_drawdown(equity_curve),
            "final_equity": result["final_equity"],
            "total_return_pct": (result["final_equity"] - initial_equity) / initial_equity * 100,
        }

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = -sum(t["pnl"] for t in losses)

    return {
        "total_trades": len(trades),
        "win_rate": len(wins) / len(trades) * 100,
        "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else None,
        "expectancy": sum(t["pnl"] for t in trades) / len(trades),
        "max_drawdown_pct": _max_drawdown(equity_curve),
        "final_equity": result["final_equity"],
        "total_return_pct": (result["final_equity"] - initial_equity) / initial_equity * 100,
    }


def _max_drawdown(equity_curve: list) -> float:
    peak = None
    max_dd = 0.0
    for point in equity_curve:
        eq = point["equity"]
        if peak is None or eq > peak:
            peak = eq
        if peak:
            dd = (peak - eq) / peak * 100
            max_dd = max(max_dd, dd)
    return max_dd

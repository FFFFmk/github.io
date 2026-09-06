"""
main.py - CLIエントリーポイント
使い方: python src/main.py --data sample_data/gbpjpy_sample_FICTIONAL.csv --pair GBPJPY
"""

import argparse
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.data_loader import load_from_csv
from src.strategy import DonchianTrendStrategy
from src.risk_manager import PositionSizer, DrawdownManager
from src.backtester import Backtester, compute_metrics
from src.report_generator import generate_report, print_summary


def load_config() -> dict:
    config_path = os.path.join(BASE_DIR, "config", "settings.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="FX戦略チーム バックテストツール")
    parser.add_argument("--data", required=True, help="OHLC CSVファイルのパス")
    parser.add_argument("--pair", default="GBPJPY", choices=["GBPJPY", "GBPUSD"])
    parser.add_argument("--equity", type=float, default=None, help="初期資金（未指定ならconfig既定値）")
    parser.add_argument("--sample", action="store_true",
                        help="架空のサンプルデータで実行することを明示するフラグ（レポートに注記される）")
    args = parser.parse_args()

    config = load_config()
    pair_config = config["pairs"][args.pair]
    initial_equity = args.equity if args.equity is not None else config["default_equity"]

    print(f"\n  データ読み込み中: {args.data}")
    df = load_from_csv(args.data)
    print(f"  {len(df)} 件のデータを読み込みました。")

    strategy = DonchianTrendStrategy(
        entry_period=pair_config["entry_period"],
        exit_period=pair_config["exit_period"],
        trend_fast_ema=pair_config["trend_fast_ema"],
        trend_slow_ema=pair_config["trend_slow_ema"],
        atr_period=pair_config["atr_period"],
        atr_multiplier=pair_config["atr_multiplier"],
    )
    df_signals = strategy.generate_signals(df)

    position_sizer = PositionSizer(
        risk_pct_per_trade=pair_config["risk_pct_per_trade"],
        atr_multiplier=pair_config["atr_multiplier"],
    )
    drawdown_manager = DrawdownManager(
        halve_risk_at_pct=config["drawdown_rules"]["halve_risk_at_pct"],
        stop_trading_at_pct=config["drawdown_rules"]["stop_trading_at_pct"],
    )

    print("  バックテスト実行中...")
    backtester = Backtester(position_sizer, drawdown_manager)
    result = backtester.run(df_signals, initial_equity)
    metrics = compute_metrics(result, initial_equity)

    print_summary(args.pair, metrics, is_sample_data=args.sample)

    filepath = generate_report(args.pair, metrics, result["trades"],
                               result["equity_curve"], is_sample_data=args.sample)
    print(f"  レポート保存先: {filepath}\n")


if __name__ == "__main__":
    main()

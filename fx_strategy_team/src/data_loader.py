"""
data_loader.py - データ読み込みモジュール

このリポジトリの実行環境からは為替のヒストリカルデータAPIへ直接アクセスできないため、
このツールは「ユーザー自身が用意したCSVファイル」を読み込む方式を取る。
CSVはブローカーのMT4/MT5エクスポート、TradingViewのエクスポート、
Alpha Vantage/OANDA等のAPIレスポンスをCSV化したものなどを想定している。
"""

import pandas as pd

REQUIRED_COLUMNS = ["date", "open", "high", "low", "close"]


def load_from_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"CSVに必要な列がありません: {missing}. "
            f"必要な列: {REQUIRED_COLUMNS}"
        )

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df[REQUIRED_COLUMNS]


def fetch_from_api(pair: str, api_key: str, provider: str = "alphavantage"):
    """
    実データ取得のプレースホルダ。

    このサンドボックス環境は外部の為替データAPIに到達できないため未実装。
    実運用では、ユーザー自身のAPIキー（Alpha Vantage, OANDA等）を用意し、
    各プロバイダのAPI仕様に従って日足OHLCを取得し、
    load_from_csv() が読み込める形式（date,open,high,low,close）で保存すること。
    """
    raise NotImplementedError(
        "実データ取得にはユーザー自身のAPIキーと外部ネットワークアクセスが必要です。"
        "取得したデータをCSVに保存し load_from_csv() を使ってください。"
    )

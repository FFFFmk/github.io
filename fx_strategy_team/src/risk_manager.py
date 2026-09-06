"""
risk_manager.py - リスク管理モジュール
ATRベースのポジションサイジング、ポートフォリオ全体のリスク上限、
ドローダウンに応じたリスク逓減ルールを実装する。
根拠・出典は README.md の「リスク管理の根拠」セクションを参照。

前提: 口座通貨 = 通貨ペアのクオート通貨（GBPJPYならJPY、GBPUSDならUSD）。
異なる口座通貨で運用する場合は、実際のポジションサイズを別途為替換算すること。
"""


class PositionSizer:
    def __init__(self, risk_pct_per_trade: float, atr_multiplier: float):
        self.risk_pct_per_trade = risk_pct_per_trade
        self.atr_multiplier = atr_multiplier

    def calculate_units(self, equity: float, atr_value: float,
                        risk_multiplier: float = 1.0) -> float:
        """
        equity: 口座資金（クオート通貨建て）
        atr_value: ATR（価格単位）
        risk_multiplier: ドローダウンルール等による追加倍率（1.0=通常, 0.5=半減, 0=停止）

        建玉サイズ(base通貨単位) = (資金 × リスク%) ÷ (ATR × ストップ倍率)
        """
        if atr_value is None or atr_value <= 0 or risk_multiplier <= 0:
            return 0.0
        risk_amount = equity * (self.risk_pct_per_trade / 100) * risk_multiplier
        stop_distance = atr_value * self.atr_multiplier
        return risk_amount / stop_distance


class PortfolioRiskManager:
    """複数ペア・複数ポジション合計のリスク上限（ポートフォリオヒート）を管理"""

    def __init__(self, max_total_risk_pct: float):
        self.max_total_risk_pct = max_total_risk_pct
        self.open_risk_pct = 0.0

    def can_open(self, new_trade_risk_pct: float) -> bool:
        return (self.open_risk_pct + new_trade_risk_pct) <= self.max_total_risk_pct

    def add_position(self, risk_pct: float):
        self.open_risk_pct += risk_pct

    def remove_position(self, risk_pct: float):
        self.open_risk_pct = max(0.0, self.open_risk_pct - risk_pct)


class DrawdownManager:
    """資金ピークからのドローダウンに応じてリスクを段階的に縮小・停止する"""

    def __init__(self, halve_risk_at_pct: float, stop_trading_at_pct: float):
        self.halve_risk_at_pct = halve_risk_at_pct
        self.stop_trading_at_pct = stop_trading_at_pct
        self.peak_equity = None

    def update(self, current_equity: float) -> float:
        """現在の資金を記録し、適用すべきリスク倍率(1.0/0.5/0.0)を返す"""
        if self.peak_equity is None or current_equity > self.peak_equity:
            self.peak_equity = current_equity

        if self.peak_equity <= 0:
            return 1.0

        drawdown_pct = (self.peak_equity - current_equity) / self.peak_equity * 100

        if drawdown_pct >= self.stop_trading_at_pct:
            return 0.0
        if drawdown_pct >= self.halve_risk_at_pct:
            return 0.5
        return 1.0

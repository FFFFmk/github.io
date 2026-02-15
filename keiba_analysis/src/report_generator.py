"""
report_generator.py - レポート生成モジュール
Excelレポートの自動生成
"""

import os
import logging
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, numbers
)
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.utils import get_column_letter

from . import database as db

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output", "reports"
)

# スタイル定義
HEADER_FONT = Font(name="Meiryo", bold=True, size=11, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
TITLE_FONT = Font(name="Meiryo", bold=True, size=14, color="2F5496")
SUBTITLE_FONT = Font(name="Meiryo", bold=True, size=12, color="333333")
DATA_FONT = Font(name="Meiryo", size=10)
GOOD_FILL = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
WARN_FILL = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
BAD_FILL = PatternFill(start_color="F8CECC", end_color="F8CECC", fill_type="solid")
BEST_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
THIN_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin")
)


class ReportGenerator:
    """Excelレポート生成クラス"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.budget = self.config.get("budget", 10000)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def generate_report(self, analysis_results: list, date_str: str) -> str:
        """
        分析結果からExcelレポートを生成

        analysis_results: analyze_race()の結果リスト
        date_str: 対象日 (YYYY-MM-DD)
        戻り値: 生成したファイルパス
        """
        wb = Workbook()

        # シート1: サマリー
        self._create_summary_sheet(wb, analysis_results, date_str)

        # シート2: レース別詳細
        for i, result in enumerate(analysis_results):
            self._create_race_detail_sheet(wb, result, i)

        # シート3: 詳細データ
        self._create_detailed_data_sheet(wb, analysis_results)

        # シート4: 投資戦略
        self._create_investment_sheet(wb, analysis_results)

        # シート5: 統計ダッシュボード
        self._create_dashboard_sheet(wb)

        # デフォルトシートを削除（存在する場合）
        if "Sheet" in wb.sheetnames:
            del wb["Sheet"]

        # ファイル保存
        filename = f"競馬分析レポート_{date_str.replace('-', '')}.xlsx"
        filepath = os.path.join(OUTPUT_DIR, filename)
        wb.save(filepath)
        logger.info("レポート生成完了: %s", filepath)
        return filepath

    # =========================================================================
    # シート1: サマリー
    # =========================================================================

    def _create_summary_sheet(self, wb: Workbook, results: list, date_str: str):
        ws = wb.active
        ws.title = "サマリー"

        # タイトル
        ws.merge_cells("A1:G1")
        ws["A1"] = f"競馬分析レポート - {date_str}"
        ws["A1"].font = TITLE_FONT
        ws["A1"].alignment = Alignment(horizontal="center")

        ws.merge_cells("A2:G2")
        ws["A2"] = f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ws["A2"].font = Font(name="Meiryo", size=9, color="666666")
        ws["A2"].alignment = Alignment(horizontal="center")

        # ヘッダー
        headers = ["レース名", "競馬場", "距離", "信頼度", "推奨馬", "オッズ", "期待値"]
        row = 4
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.alignment = Alignment(horizontal="center")
            cell.border = THIN_BORDER

        # データ
        row = 5
        for result in results:
            race = result.get("race", {})
            recs = result.get("recommendations", [])
            confidence = result.get("confidence", "−")

            if recs:
                top_rec = recs[0]
                rec_name = top_rec["horse_name"]
                rec_odds = top_rec.get("odds", "−")
                rec_ev = top_rec.get("expected_value", "−")
            else:
                rec_name = "推奨なし"
                rec_odds = "−"
                rec_ev = "−"

            race_name = race.get("race_name", "")
            venue = race.get("venue", "")
            dist_surface = ""
            if race.get("surface"):
                dist_surface = f"{race.get('surface', '')}{race.get('distance', '')}m"

            values = [race_name, venue, dist_surface, confidence,
                      rec_name, rec_odds, rec_ev]

            for col, val in enumerate(values, 1):
                cell = ws.cell(row=row, column=col, value=val)
                cell.font = DATA_FONT
                cell.border = THIN_BORDER
                cell.alignment = Alignment(horizontal="center")

                # 信頼度による色分け
                if col == 4:
                    if val == "高":
                        cell.fill = GOOD_FILL
                    elif val == "中":
                        cell.fill = WARN_FILL
                    elif val == "低":
                        cell.fill = BAD_FILL

                # 期待値による色分け
                if col == 7 and isinstance(val, (int, float)):
                    if val >= 0.5:
                        cell.fill = BEST_FILL
                    elif val >= 0:
                        cell.fill = GOOD_FILL
                    else:
                        cell.fill = BAD_FILL

            row += 1

        # 列幅調整
        col_widths = [30, 10, 12, 10, 15, 10, 12]
        for i, w in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

    # =========================================================================
    # シート2: レース別詳細
    # =========================================================================

    def _create_race_detail_sheet(self, wb: Workbook, result: dict, index: int):
        race = result.get("race", {})
        entries = result.get("entries", [])
        dev = result.get("development", {})

        venue = race.get("venue", "")
        race_num = race.get("race_number", "")
        sheet_name = f"{venue}{race_num}R"
        # シート名の長さ制限
        if len(sheet_name) > 31:
            sheet_name = sheet_name[:31]

        ws = wb.create_sheet(title=sheet_name)

        # レース情報ヘッダー
        ws.merge_cells("A1:H1")
        title = f"{race.get('race_name', '')} ({venue} {race_num}R)"
        ws["A1"] = title
        ws["A1"].font = SUBTITLE_FONT

        # レース条件
        conditions = []
        if race.get("surface"):
            conditions.append(race["surface"])
        if race.get("distance"):
            conditions.append(f"{race['distance']}m")
        if race.get("condition"):
            conditions.append(f"馬場:{race['condition']}")
        if race.get("weather"):
            conditions.append(f"天候:{race['weather']}")

        ws.merge_cells("A2:H2")
        ws["A2"] = " / ".join(conditions)
        ws["A2"].font = Font(name="Meiryo", size=9, color="666666")

        # 展開予想
        ws.merge_cells("A3:H3")
        pace = dev.get("pace", "不明")
        adv = dev.get("pace_advantage", "不明")
        ws["A3"] = f"展開予想: {pace} → {adv}"
        ws["A3"].font = Font(name="Meiryo", size=10, bold=True, color="CC3300")

        # 出走馬テーブルヘッダー
        headers = ["馬番", "馬名", "枠", "騎手", "オッズ", "期待値",
                    "R/R比", "評価", "推奨度"]
        row = 5
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.alignment = Alignment(horizontal="center")
            cell.border = THIN_BORDER

        # データ
        row = 6
        for entry in entries:
            values = [
                entry.get("horse_number", ""),
                entry.get("horse_name", ""),
                entry.get("gate", ""),
                entry.get("jockey", ""),
                entry.get("odds_win", "−"),
                self._fmt_ev(entry.get("expected_value")),
                self._fmt_rr(entry.get("risk_reward")),
                entry.get("recommendation", "−"),
                entry.get("rec_stars", "−"),
            ]

            for col, val in enumerate(values, 1):
                cell = ws.cell(row=row, column=col, value=val)
                cell.font = DATA_FONT
                cell.border = THIN_BORDER
                cell.alignment = Alignment(horizontal="center")

            # 推奨度による行の色分け
            rec_level = entry.get("rec_level", -1)
            if rec_level >= 3:
                for c in range(1, len(headers) + 1):
                    ws.cell(row=row, column=c).fill = BEST_FILL
            elif rec_level >= 2:
                for c in range(1, len(headers) + 1):
                    ws.cell(row=row, column=c).fill = GOOD_FILL
            elif rec_level >= 1:
                for c in range(1, len(headers) + 1):
                    ws.cell(row=row, column=c).fill = WARN_FILL

            row += 1

        # 列幅
        col_widths = [8, 18, 6, 12, 10, 10, 10, 12, 10]
        for i, w in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

    # =========================================================================
    # シート3: 詳細データ
    # =========================================================================

    def _create_detailed_data_sheet(self, wb: Workbook, results: list):
        ws = wb.create_sheet(title="詳細データ")

        ws["A1"] = "詳細分析データ"
        ws["A1"].font = TITLE_FONT

        headers = [
            "レース", "馬番", "馬名", "騎手", "前走着順", "前走スコア",
            "コース適性", "距離適性", "騎手スコア", "枠順スコア",
            "血統スコア", "脚質", "ペース補正", "合計スコア",
            "推定勝率", "オッズ", "期待値", "R/R比"
        ]
        row = 3
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.alignment = Alignment(horizontal="center", wrap_text=True)
            cell.border = THIN_BORDER

        row = 4
        for result in results:
            race = result.get("race", {})
            race_label = f"{race.get('venue', '')}{race.get('race_number', '')}R"

            for entry in result.get("entries", []):
                scores = entry.get("scores", {})
                values = [
                    race_label,
                    entry.get("horse_number", ""),
                    entry.get("horse_name", ""),
                    entry.get("jockey", ""),
                    "",  # 前走着順（過去成績から取得可能）
                    scores.get("prev_race", "−"),
                    scores.get("course", "−"),
                    scores.get("distance", "−"),
                    scores.get("jockey", "−"),
                    scores.get("gate", "−"),
                    scores.get("pedigree", "−"),
                    entry.get("running_style", "−"),
                    entry.get("pace_score", 0),
                    entry.get("base_score", "−"),
                    self._fmt_pct(entry.get("estimated_win_prob")),
                    entry.get("odds_win", "−"),
                    self._fmt_ev(entry.get("expected_value")),
                    self._fmt_rr(entry.get("risk_reward")),
                ]

                for col, val in enumerate(values, 1):
                    cell = ws.cell(row=row, column=col, value=val)
                    cell.font = DATA_FONT
                    cell.border = THIN_BORDER
                    cell.alignment = Alignment(horizontal="center")

                row += 1

        # 列幅
        for i in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(i)].width = 12

    # =========================================================================
    # シート4: 投資戦略
    # =========================================================================

    def _create_investment_sheet(self, wb: Workbook, results: list):
        ws = wb.create_sheet(title="投資戦略")

        ws["A1"] = "投資戦略シート"
        ws["A1"].font = TITLE_FONT

        budget = self.budget
        ws["A3"] = f"予算: ¥{budget:,}"
        ws["A3"].font = Font(name="Meiryo", bold=True, size=12)

        # 戦略説明
        ws["A5"] = "配分ルール"
        ws["A5"].font = SUBTITLE_FONT

        strategies = [
            ("本命馬（期待値1.4以上）", f"¥{int(budget * 0.5):,}", "予算の50%"),
            ("対抗馬（期待値1.2-1.4）", f"¥{int(budget * 0.3):,}", "予算の30%"),
            ("穴馬（期待値1.5以上、オッズ10倍以上）", f"¥{int(budget * 0.2):,}", "予算の20%"),
        ]

        row = 6
        headers = ["カテゴリ", "配分額", "備考"]
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=h)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.border = THIN_BORDER

        row = 7
        for cat, amount, note in strategies:
            ws.cell(row=row, column=1, value=cat).font = DATA_FONT
            ws.cell(row=row, column=2, value=amount).font = DATA_FONT
            ws.cell(row=row, column=3, value=note).font = DATA_FONT
            for c in range(1, 4):
                ws.cell(row=row, column=c).border = THIN_BORDER
            row += 1

        # 推奨ベット一覧
        row += 2
        ws.cell(row=row, column=1, value="推奨ベット一覧").font = SUBTITLE_FONT
        row += 1

        bet_headers = ["レース", "馬名", "オッズ", "期待値", "カテゴリ", "推奨投資額"]
        for col, h in enumerate(bet_headers, 1):
            cell = ws.cell(row=row, column=col, value=h)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.border = THIN_BORDER

        row += 1
        honmei_budget = budget * 0.5
        taikou_budget = budget * 0.3
        ana_budget = budget * 0.2

        honmei_count = 0
        taikou_count = 0
        ana_count = 0

        # カテゴリ分け
        for result in results:
            race = result.get("race", {})
            race_label = f"{race.get('venue', '')}{race.get('race_number', '')}R"
            for rec in result.get("recommendations", []):
                ev = rec.get("expected_value", 0)
                odds = rec.get("odds", 0) or 0
                if ev >= 0.4:
                    honmei_count += 1
                elif ev >= 0.2:
                    taikou_count += 1
                elif ev >= 0.5 and odds >= 10:
                    ana_count += 1

        # 投資額計算
        for result in results:
            race = result.get("race", {})
            race_label = f"{race.get('venue', '')}{race.get('race_number', '')}R"

            for rec in result.get("recommendations", []):
                ev = rec.get("expected_value", 0)
                odds = rec.get("odds", 0) or 0

                if ev >= 0.4:
                    category = "本命"
                    bet_amount = int(honmei_budget / max(honmei_count, 1))
                elif ev >= 0.2:
                    category = "対抗"
                    bet_amount = int(taikou_budget / max(taikou_count, 1))
                elif odds >= 10 and ev > 0:
                    category = "穴馬"
                    bet_amount = int(ana_budget / max(ana_count, 1))
                else:
                    category = "少額"
                    bet_amount = 100

                # 100円単位に丸め
                bet_amount = max(100, (bet_amount // 100) * 100)

                values = [race_label, rec["horse_name"], odds,
                          self._fmt_ev(ev), category, f"¥{bet_amount:,}"]
                for col, val in enumerate(values, 1):
                    cell = ws.cell(row=row, column=col, value=val)
                    cell.font = DATA_FONT
                    cell.border = THIN_BORDER
                    cell.alignment = Alignment(horizontal="center")
                row += 1

        # 列幅
        for i, w in enumerate([15, 18, 10, 10, 10, 14], 1):
            ws.column_dimensions[get_column_letter(i)].width = w

    # =========================================================================
    # シート5: 統計ダッシュボード
    # =========================================================================

    def _create_dashboard_sheet(self, wb: Workbook):
        ws = wb.create_sheet(title="統計ダッシュボード")

        ws["A1"] = "統計ダッシュボード"
        ws["A1"].font = TITLE_FONT

        # 累積統計
        stats = db.get_cumulative_stats()

        ws["A3"] = "累積パフォーマンス"
        ws["A3"].font = SUBTITLE_FONT

        metrics = [
            ("総週数", stats.get("total_weeks", 0)),
            ("総ベット数", stats.get("total_bets", 0)),
            ("総的中数", stats.get("total_hits", 0)),
            ("累積的中率", f"{stats.get('cumulative_hit_rate', 0)}%"),
            ("累積投資額", f"¥{stats.get('total_investment', 0):,}"),
            ("累積回収額", f"¥{stats.get('total_return', 0):,}"),
            ("累積回収率", f"{stats.get('cumulative_return_rate', 0)}%"),
        ]

        row = 4
        for label, value in metrics:
            ws.cell(row=row, column=1, value=label).font = DATA_FONT
            ws.cell(row=row, column=1).border = THIN_BORDER
            cell = ws.cell(row=row, column=2, value=value)
            cell.font = Font(name="Meiryo", bold=True, size=11)
            cell.border = THIN_BORDER
            row += 1

        # 週次パフォーマンス推移
        row += 2
        ws.cell(row=row, column=1, value="週次パフォーマンス推移").font = SUBTITLE_FONT
        row += 1

        perf_headers = ["日付", "ベット数", "的中数", "的中率", "投資額", "回収額", "回収率"]
        for col, h in enumerate(perf_headers, 1):
            cell = ws.cell(row=row, column=col, value=h)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.border = THIN_BORDER

        performances = db.get_all_performance()
        data_start_row = row + 1

        for perf in performances:
            row += 1
            values = [
                perf.get("date", ""),
                perf.get("total_bets", 0),
                perf.get("total_hits", 0),
                f"{perf.get('hit_rate', 0)}%",
                perf.get("total_investment", 0),
                perf.get("total_return", 0),
                f"{perf.get('return_rate', 0)}%",
            ]
            for col, val in enumerate(values, 1):
                cell = ws.cell(row=row, column=col, value=val)
                cell.font = DATA_FONT
                cell.border = THIN_BORDER

        # グラフ（データがある場合のみ）
        if performances and len(performances) >= 2:
            data_end_row = row

            chart = LineChart()
            chart.title = "回収率推移"
            chart.y_axis.title = "回収率 (%)"
            chart.x_axis.title = "日付"
            chart.width = 20
            chart.height = 12

            data = Reference(ws, min_col=7, min_row=data_start_row - 1,
                             max_col=7, max_row=data_end_row)
            cats = Reference(ws, min_col=1, min_row=data_start_row,
                             max_row=data_end_row)
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(cats)
            ws.add_chart(chart, f"A{row + 3}")

        # 列幅
        for i, w in enumerate([14, 10, 10, 10, 12, 12, 10], 1):
            ws.column_dimensions[get_column_letter(i)].width = w

    # =========================================================================
    # コンソール出力
    # =========================================================================

    @staticmethod
    def print_summary(results: list):
        """分析結果のサマリーをコンソールに表示"""
        print("\n" + "=" * 70)
        print("  競馬分析結果サマリー")
        print("=" * 70)

        for result in results:
            race = result.get("race", {})
            recs = result.get("recommendations", [])
            dev = result.get("development", {})
            conf = result.get("confidence", "−")

            venue = race.get("venue", "")
            race_num = race.get("race_number", "")
            race_name = race.get("race_name", "")
            surface = race.get("surface", "")
            distance = race.get("distance", "")

            print(f"\n{'─' * 60}")
            print(f"  {venue} {race_num}R {race_name}")
            print(f"  {surface}{distance}m  信頼度: {conf}")
            print(f"  展開: {dev.get('pace', '−')} → {dev.get('pace_advantage', '−')}")
            print(f"{'─' * 60}")

            if recs:
                print(f"  {'馬名':<12} {'オッズ':>8} {'期待値':>8} {'R/R比':>8} {'評価':<8}")
                print(f"  {'-' * 52}")
                for rec in recs[:5]:  # 上位5頭まで
                    name = rec["horse_name"]
                    odds = rec.get("odds", "−")
                    ev = rec.get("expected_value", "−")
                    rr = rec.get("risk_reward", "−")
                    label = rec.get("recommendation", "−")
                    ev_str = f"{ev:.2f}" if isinstance(ev, (int, float)) else str(ev)
                    rr_str = f"{rr:.2f}" if isinstance(rr, (int, float)) else str(rr)
                    odds_str = f"{odds:.1f}" if isinstance(odds, (int, float)) else str(odds)
                    print(f"  {name:<12} {odds_str:>8} {ev_str:>8} {rr_str:>8} {label:<8}")
            else:
                print("  推奨馬なし")

        print(f"\n{'=' * 70}\n")

    # =========================================================================
    # ヘルパー
    # =========================================================================

    @staticmethod
    def _fmt_ev(val) -> str:
        if val is None:
            return "−"
        return f"{val:.2f}" if isinstance(val, (int, float)) else str(val)

    @staticmethod
    def _fmt_rr(val) -> str:
        if val is None:
            return "−"
        return f"{val:.2f}" if isinstance(val, (int, float)) else str(val)

    @staticmethod
    def _fmt_pct(val) -> str:
        if val is None:
            return "−"
        return f"{val * 100:.1f}%" if isinstance(val, (int, float)) else str(val)

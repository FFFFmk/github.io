"""
main.py - メインプログラム
競馬自動分析システム CLI メニュー
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta

# パスの設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src import database as db
from src.data_collector import DataCollector
from src.analyzer import Analyzer
from src.report_generator import ReportGenerator

# ログ設定
LOG_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(LOG_DIR, "keiba_analysis.log"),
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

VERSION = "1.0.0"


def load_config() -> dict:
    """設定ファイルを読み込む"""
    config_path = os.path.join(BASE_DIR, "config", "settings.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(config: dict):
    """設定ファイルを保存"""
    config_path = os.path.join(BASE_DIR, "config", "settings.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_next_weekend() -> tuple:
    """次の土曜日・日曜日の日付を取得"""
    today = datetime.now()
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0 and today.hour >= 18:
        days_until_saturday = 7
    saturday = today + timedelta(days=days_until_saturday)
    sunday = saturday + timedelta(days=1)
    return saturday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")


def clear_screen():
    """画面クリア"""
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    """ヘッダー表示"""
    print()
    print("━" * 50)
    print(f"  競馬自動分析システム v{VERSION}")
    print("━" * 50)
    print()


def print_menu():
    """メインメニュー表示"""
    sat, sun = get_next_weekend()
    print(f"  対象: {sat}（土）/ {sun}（日）")
    print()
    print("  1. 今週末のレースを分析")
    print("  2. 特定のレースを分析")
    print("  3. オッズを更新して再計算")
    print("  4. 週次レポートを表示")
    print("  5. 設定変更")
    print("  6. 終了")
    print()


def analyze_weekend(config: dict):
    """今週末のレースを一括分析"""
    sat, sun = get_next_weekend()
    print(f"\n  対象日: {sat}（土）, {sun}（日）")
    print("  10R以降のメインレースを分析します。")
    print()

    collector = DataCollector(config)
    analyzer = Analyzer(config)
    reporter = ReportGenerator(config)

    all_results = []

    for target_date in [sat, sun]:
        print(f"\n  === {target_date} のデータ収集中... ===\n")
        try:
            races = collector.collect_weekend_races(target_date)
            if not races:
                print(f"  {target_date}: レースデータを取得できませんでした。")
                print("  ネットワーク接続を確認してください。")
                continue

            print(f"  {len(races)} レースのデータを取得しました。")
            print("  分析実行中...\n")

            results = analyzer.analyze_all_races(races)
            all_results.extend(results)

            # コンソールにサマリー表示
            reporter.print_summary(results)

            # Excelレポート生成
            filepath = reporter.generate_report(results, target_date)
            print(f"  レポート保存先: {filepath}")

        except Exception as e:
            logger.error("分析エラー: %s", e)
            print(f"  エラーが発生しました: {e}")
            print("  詳細はログファイルを確認してください。")

    if all_results:
        print(f"\n  合計 {len(all_results)} レースの分析が完了しました。")
    else:
        print("\n  分析できるレースがありませんでした。")

    input("\n  Enterキーで戻る...")


def analyze_specific(config: dict):
    """特定のレースを分析"""
    print("\n  分析する日付を入力してください。")
    date_str = input("  日付 (YYYY-MM-DD): ").strip()

    if not date_str:
        print("  日付が入力されていません。")
        input("\n  Enterキーで戻る...")
        return

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print("  日付の形式が正しくありません。YYYY-MM-DD で入力してください。")
        input("\n  Enterキーで戻る...")
        return

    print(f"\n  {date_str} のレースを分析します...\n")

    collector = DataCollector(config)
    analyzer = Analyzer(config)
    reporter = ReportGenerator(config)

    try:
        races = collector.collect_weekend_races(date_str)
        if not races:
            print("  レースデータを取得できませんでした。")
            input("\n  Enterキーで戻る...")
            return

        print(f"  {len(races)} レースのデータを取得しました。")
        print("  分析実行中...\n")

        results = analyzer.analyze_all_races(races)
        reporter.print_summary(results)

        filepath = reporter.generate_report(results, date_str)
        print(f"  レポート保存先: {filepath}")

    except Exception as e:
        logger.error("分析エラー: %s", e)
        print(f"  エラーが発生しました: {e}")

    input("\n  Enterキーで戻る...")


def update_odds(config: dict):
    """オッズを更新して再計算"""
    print("\n  オッズ更新対象の日付を入力してください。")
    sat, sun = get_next_weekend()
    print(f"  （未入力の場合: {sat}）")

    date_str = input("  日付 (YYYY-MM-DD): ").strip()
    if not date_str:
        date_str = sat

    print(f"\n  {date_str} のオッズを更新中...\n")

    collector = DataCollector(config)
    analyzer = Analyzer(config)
    reporter = ReportGenerator(config)

    try:
        updated = collector.update_odds_only(date_str)
        if not updated:
            print("  更新するレースが見つかりませんでした。")
            print("  先にレース分析を実行してください。")
            input("\n  Enterキーで戻る...")
            return

        print(f"  {len(updated)} レースのオッズを更新しました。")
        print("  再分析中...\n")

        results = analyzer.analyze_all_races(updated)
        reporter.print_summary(results)

        filepath = reporter.generate_report(results, date_str)
        print(f"  更新レポート: {filepath}")

        # 期待値1.5超えアラート
        for result in results:
            for rec in result.get("recommendations", []):
                ev = rec.get("expected_value", 0)
                if ev >= 0.5:
                    race = result.get("race", {})
                    print(f"\n  *** アラート ***")
                    print(f"  高期待値: {race.get('venue')}{race.get('race_number')}R "
                          f"{rec['horse_name']} (期待値: {ev:.2f}, "
                          f"オッズ: {rec.get('odds', '−')})")

    except Exception as e:
        logger.error("オッズ更新エラー: %s", e)
        print(f"  エラーが発生しました: {e}")

    input("\n  Enterキーで戻る...")


def show_weekly_report(config: dict):
    """週次レポートを表示"""
    print("\n  === 週次パフォーマンスレポート ===\n")

    stats = db.get_cumulative_stats()
    perfs = db.get_all_performance()

    if not perfs:
        print("  まだパフォーマンスデータがありません。")
        print("  レース分析と結果登録を行ってから確認してください。")
        input("\n  Enterキーで戻る...")
        return

    print(f"  累積統計:")
    print(f"  {'─' * 40}")
    print(f"  総週数:     {stats.get('total_weeks', 0)}")
    print(f"  総ベット数: {stats.get('total_bets', 0)}")
    print(f"  総的中数:   {stats.get('total_hits', 0)}")
    print(f"  累積的中率: {stats.get('cumulative_hit_rate', 0)}%")
    print(f"  累積投資額: ¥{stats.get('total_investment', 0):,}")
    print(f"  累積回収額: ¥{stats.get('total_return', 0):,}")
    print(f"  累積回収率: {stats.get('cumulative_return_rate', 0)}%")

    print(f"\n  週次推移:")
    print(f"  {'─' * 60}")
    print(f"  {'日付':<12} {'的中率':>8} {'回収率':>8} {'投資額':>10} {'回収額':>10}")
    print(f"  {'─' * 60}")

    for perf in perfs[:10]:
        print(f"  {perf['date']:<12} "
              f"{perf.get('hit_rate', 0):>7.1f}% "
              f"{perf.get('return_rate', 0):>7.1f}% "
              f"¥{perf.get('total_investment', 0):>9,} "
              f"¥{perf.get('total_return', 0):>9,}")

    input("\n  Enterキーで戻る...")


def change_settings(config: dict) -> dict:
    """設定変更"""
    print("\n  === 設定変更 ===\n")
    print(f"  現在の設定:")
    print(f"  1. 予算: ¥{config.get('budget', 10000):,}")
    print(f"  2. 対象レース: {config.get('min_race_number', 10)}R 以降")
    print(f"  3. リクエスト間隔: {config.get('request_delay', 2)}秒")
    print()

    choice = input("  変更する項目 (1-3, 0で戻る): ").strip()

    if choice == "1":
        try:
            budget = int(input("  新しい予算 (円): ").strip())
            config["budget"] = budget
            save_config(config)
            print(f"  予算を ¥{budget:,} に変更しました。")
        except ValueError:
            print("  数値を入力してください。")

    elif choice == "2":
        try:
            min_race = int(input("  対象レース開始番号: ").strip())
            config["min_race_number"] = min_race
            save_config(config)
            print(f"  {min_race}R 以降を対象にします。")
        except ValueError:
            print("  数値を入力してください。")

    elif choice == "3":
        try:
            delay = int(input("  リクエスト間隔 (秒): ").strip())
            config["request_delay"] = delay
            save_config(config)
            print(f"  リクエスト間隔を {delay}秒 に変更しました。")
        except ValueError:
            print("  数値を入力してください。")

    input("\n  Enterキーで戻る...")
    return config


def main():
    """メインループ"""
    # データベース初期化
    db.init_database()

    # 設定読み込み
    config = load_config()

    while True:
        clear_screen()
        print_header()
        print_menu()

        choice = input("  選択してください (1-6): ").strip()

        if choice == "1":
            analyze_weekend(config)
        elif choice == "2":
            analyze_specific(config)
        elif choice == "3":
            update_odds(config)
        elif choice == "4":
            show_weekly_report(config)
        elif choice == "5":
            config = change_settings(config)
        elif choice == "6":
            print("\n  お疲れ様でした。またのご利用をお待ちしています。\n")
            break
        else:
            print("  1-6 の数字を入力してください。")
            input("  Enterキーで戻る...")


if __name__ == "__main__":
    main()

"""
database.py - データベース操作モジュール
競馬分析システムのSQLiteデータベース管理
"""

import sqlite3
import os
import logging
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "keiba.db")


@contextmanager
def get_connection():
    """データベース接続のコンテキストマネージャー"""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """データベースの初期化（テーブル作成）"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # レース情報
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS races (
                race_id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                venue TEXT NOT NULL,
                race_number INTEGER NOT NULL,
                race_name TEXT,
                distance INTEGER,
                surface TEXT,
                condition TEXT,
                weather TEXT,
                post_time TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 馬情報
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS horses (
                horse_id TEXT PRIMARY KEY,
                horse_name TEXT NOT NULL,
                birth_year INTEGER,
                sex TEXT,
                sire TEXT,
                dam_sire TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 出走記録
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS race_entries (
                entry_id TEXT PRIMARY KEY,
                race_id TEXT NOT NULL,
                horse_id TEXT NOT NULL,
                horse_name TEXT,
                jockey TEXT,
                trainer TEXT,
                gate INTEGER,
                horse_number INTEGER,
                weight REAL,
                horse_weight REAL,
                horse_weight_diff REAL,
                odds_win REAL,
                odds_place_min REAL,
                odds_place_max REAL,
                finish_position INTEGER,
                finish_time TEXT,
                margin TEXT,
                running_style TEXT,
                base_score REAL,
                expected_value REAL,
                risk_reward REAL,
                recommendation TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (race_id) REFERENCES races(race_id),
                FOREIGN KEY (horse_id) REFERENCES horses(horse_id)
            )
        """)

        # 過去成績
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS past_results (
                result_id TEXT PRIMARY KEY,
                horse_id TEXT NOT NULL,
                date TEXT,
                venue TEXT,
                race_name TEXT,
                distance INTEGER,
                surface TEXT,
                condition TEXT,
                finish_position INTEGER,
                field_size INTEGER,
                finish_time TEXT,
                margin TEXT,
                weight REAL,
                jockey TEXT,
                odds REAL,
                running_style TEXT,
                FOREIGN KEY (horse_id) REFERENCES horses(horse_id)
            )
        """)

        # 統計データ
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                stat_id TEXT PRIMARY KEY,
                venue TEXT,
                surface TEXT,
                distance INTEGER,
                gate INTEGER,
                running_style TEXT,
                sample_size INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                place_rate REAL DEFAULT 0.0,
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 血統統計
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sire_statistics (
                stat_id TEXT PRIMARY KEY,
                sire_name TEXT NOT NULL,
                venue TEXT,
                surface TEXT,
                distance_category TEXT,
                sample_size INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                place_rate REAL DEFAULT 0.0,
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 騎手統計
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jockey_statistics (
                stat_id TEXT PRIMARY KEY,
                jockey_name TEXT NOT NULL,
                venue TEXT,
                surface TEXT,
                sample_size INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                place_rate REAL DEFAULT 0.0,
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 成績追跡
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance (
                week_id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                total_bets INTEGER DEFAULT 0,
                total_hits INTEGER DEFAULT 0,
                hit_rate REAL DEFAULT 0.0,
                total_investment INTEGER DEFAULT 0,
                total_return INTEGER DEFAULT 0,
                return_rate REAL DEFAULT 0.0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_races_date ON races(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_races_venue ON races(venue)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_race ON race_entries(race_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entries_horse ON race_entries(horse_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_past_horse ON past_results(horse_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stats_venue ON statistics(venue, surface)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_perf_date ON performance(date)")

        conn.commit()
        logger.info("データベースを初期化しました: %s", DB_PATH)


# --- レース関連操作 ---

def upsert_race(race_data: dict):
    """レース情報の挿入/更新"""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO races (race_id, date, venue, race_number, race_name,
                             distance, surface, condition, weather, post_time, updated_at)
            VALUES (:race_id, :date, :venue, :race_number, :race_name,
                    :distance, :surface, :condition, :weather, :post_time,
                    datetime('now', 'localtime'))
            ON CONFLICT(race_id) DO UPDATE SET
                race_name=excluded.race_name, distance=excluded.distance,
                surface=excluded.surface, condition=excluded.condition,
                weather=excluded.weather, post_time=excluded.post_time,
                updated_at=datetime('now', 'localtime')
        """, race_data)


def get_races_by_date(date_str: str) -> list:
    """日付でレースを取得"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM races WHERE date = ? ORDER BY venue, race_number",
            (date_str,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_race(race_id: str) -> dict:
    """レースIDでレースを取得"""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM races WHERE race_id = ?", (race_id,)).fetchone()
        return dict(row) if row else None


# --- 馬関連操作 ---

def upsert_horse(horse_data: dict):
    """馬情報の挿入/更新"""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO horses (horse_id, horse_name, birth_year, sex, sire, dam_sire)
            VALUES (:horse_id, :horse_name, :birth_year, :sex, :sire, :dam_sire)
            ON CONFLICT(horse_id) DO UPDATE SET
                horse_name=excluded.horse_name, sire=excluded.sire,
                dam_sire=excluded.dam_sire
        """, horse_data)


# --- 出走記録操作 ---

def upsert_entry(entry_data: dict):
    """出走記録の挿入/更新"""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO race_entries (entry_id, race_id, horse_id, horse_name, jockey,
                trainer, gate, horse_number, weight, horse_weight, horse_weight_diff,
                odds_win, odds_place_min, odds_place_max, running_style,
                base_score, expected_value, risk_reward, recommendation, updated_at)
            VALUES (:entry_id, :race_id, :horse_id, :horse_name, :jockey,
                    :trainer, :gate, :horse_number, :weight, :horse_weight,
                    :horse_weight_diff, :odds_win, :odds_place_min, :odds_place_max,
                    :running_style, :base_score, :expected_value, :risk_reward,
                    :recommendation, datetime('now', 'localtime'))
            ON CONFLICT(entry_id) DO UPDATE SET
                odds_win=excluded.odds_win, odds_place_min=excluded.odds_place_min,
                odds_place_max=excluded.odds_place_max,
                base_score=excluded.base_score, expected_value=excluded.expected_value,
                risk_reward=excluded.risk_reward, recommendation=excluded.recommendation,
                updated_at=datetime('now', 'localtime')
        """, entry_data)


def get_entries_by_race(race_id: str) -> list:
    """レースIDで出走馬を取得"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM race_entries WHERE race_id = ? ORDER BY horse_number",
            (race_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_entry_result(entry_id: str, finish_position: int, finish_time: str = None,
                        margin: str = None):
    """レース結果を更新"""
    with get_connection() as conn:
        conn.execute("""
            UPDATE race_entries SET finish_position = ?, finish_time = ?,
                margin = ?, updated_at = datetime('now', 'localtime')
            WHERE entry_id = ?
        """, (finish_position, finish_time, margin, entry_id))


# --- 過去成績操作 ---

def insert_past_result(result_data: dict):
    """過去成績の挿入"""
    with get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO past_results
                (result_id, horse_id, date, venue, race_name, distance, surface,
                 condition, finish_position, field_size, finish_time, margin,
                 weight, jockey, odds, running_style)
            VALUES (:result_id, :horse_id, :date, :venue, :race_name, :distance,
                    :surface, :condition, :finish_position, :field_size,
                    :finish_time, :margin, :weight, :jockey, :odds, :running_style)
        """, result_data)


def get_past_results(horse_id: str, limit: int = 10) -> list:
    """馬の過去成績を取得"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM past_results WHERE horse_id = ? ORDER BY date DESC LIMIT ?",
            (horse_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def get_course_results(horse_id: str, venue: str, surface: str,
                       distance: int = None) -> list:
    """特定コースでの成績を取得"""
    with get_connection() as conn:
        query = """SELECT * FROM past_results
                   WHERE horse_id = ? AND venue = ? AND surface = ?"""
        params = [horse_id, venue, surface]
        if distance:
            query += " AND distance = ?"
            params.append(distance)
        query += " ORDER BY date DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# --- 統計操作 ---

def upsert_statistics(stat_data: dict):
    """統計データの挿入/更新"""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO statistics (stat_id, venue, surface, distance, gate,
                running_style, sample_size, win_rate, place_rate, updated_at)
            VALUES (:stat_id, :venue, :surface, :distance, :gate,
                    :running_style, :sample_size, :win_rate, :place_rate,
                    datetime('now', 'localtime'))
            ON CONFLICT(stat_id) DO UPDATE SET
                sample_size=excluded.sample_size, win_rate=excluded.win_rate,
                place_rate=excluded.place_rate, updated_at=datetime('now', 'localtime')
        """, stat_data)


def get_gate_statistics(venue: str, surface: str, distance: int = None) -> list:
    """枠順統計を取得"""
    with get_connection() as conn:
        query = "SELECT * FROM statistics WHERE venue = ? AND surface = ? AND gate IS NOT NULL"
        params = [venue, surface]
        if distance:
            query += " AND distance = ?"
            params.append(distance)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_style_statistics(venue: str, surface: str) -> list:
    """脚質統計を取得"""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM statistics
            WHERE venue = ? AND surface = ? AND running_style IS NOT NULL
        """, (venue, surface)).fetchall()
        return [dict(r) for r in rows]


# --- 血統統計操作 ---

def upsert_sire_stat(stat_data: dict):
    """血統統計の挿入/更新"""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO sire_statistics (stat_id, sire_name, venue, surface,
                distance_category, sample_size, win_rate, place_rate, updated_at)
            VALUES (:stat_id, :sire_name, :venue, :surface,
                    :distance_category, :sample_size, :win_rate, :place_rate,
                    datetime('now', 'localtime'))
            ON CONFLICT(stat_id) DO UPDATE SET
                sample_size=excluded.sample_size, win_rate=excluded.win_rate,
                place_rate=excluded.place_rate, updated_at=datetime('now', 'localtime')
        """, stat_data)


def get_sire_stat(sire_name: str, venue: str = None, surface: str = None) -> list:
    """血統統計を取得"""
    with get_connection() as conn:
        query = "SELECT * FROM sire_statistics WHERE sire_name = ?"
        params = [sire_name]
        if venue:
            query += " AND venue = ?"
            params.append(venue)
        if surface:
            query += " AND surface = ?"
            params.append(surface)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# --- 騎手統計操作 ---

def upsert_jockey_stat(stat_data: dict):
    """騎手統計の挿入/更新"""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO jockey_statistics (stat_id, jockey_name, venue, surface,
                sample_size, win_rate, place_rate, updated_at)
            VALUES (:stat_id, :jockey_name, :venue, :surface,
                    :sample_size, :win_rate, :place_rate,
                    datetime('now', 'localtime'))
            ON CONFLICT(stat_id) DO UPDATE SET
                sample_size=excluded.sample_size, win_rate=excluded.win_rate,
                place_rate=excluded.place_rate, updated_at=datetime('now', 'localtime')
        """, stat_data)


def get_jockey_stat(jockey_name: str, venue: str = None) -> list:
    """騎手統計を取得"""
    with get_connection() as conn:
        query = "SELECT * FROM jockey_statistics WHERE jockey_name = ?"
        params = [jockey_name]
        if venue:
            query += " AND venue = ?"
            params.append(venue)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# --- パフォーマンス追跡 ---

def upsert_performance(perf_data: dict):
    """成績追跡の挿入/更新"""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO performance (week_id, date, total_bets, total_hits,
                hit_rate, total_investment, total_return, return_rate)
            VALUES (:week_id, :date, :total_bets, :total_hits,
                    :hit_rate, :total_investment, :total_return, :return_rate)
            ON CONFLICT(week_id) DO UPDATE SET
                total_bets=excluded.total_bets, total_hits=excluded.total_hits,
                hit_rate=excluded.hit_rate, total_investment=excluded.total_investment,
                total_return=excluded.total_return, return_rate=excluded.return_rate
        """, perf_data)


def get_all_performance() -> list:
    """全パフォーマンスデータを取得"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM performance ORDER BY date DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_cumulative_stats() -> dict:
    """累積統計を取得"""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) as total_weeks,
                SUM(total_bets) as total_bets,
                SUM(total_hits) as total_hits,
                CASE WHEN SUM(total_bets) > 0
                    THEN ROUND(CAST(SUM(total_hits) AS REAL) / SUM(total_bets) * 100, 1)
                    ELSE 0 END as cumulative_hit_rate,
                SUM(total_investment) as total_investment,
                SUM(total_return) as total_return,
                CASE WHEN SUM(total_investment) > 0
                    THEN ROUND(CAST(SUM(total_return) AS REAL) / SUM(total_investment) * 100, 1)
                    ELSE 0 END as cumulative_return_rate
            FROM performance
        """).fetchone()
        return dict(row) if row else {}


if __name__ == "__main__":
    init_database()
    print(f"データベースを作成しました: {DB_PATH}")

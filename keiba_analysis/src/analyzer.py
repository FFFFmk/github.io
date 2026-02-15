"""
analyzer.py - 分析エンジンモジュール
基礎スコアリング、期待値計算、リスクリワード評価、展開予想
"""

import logging
from collections import Counter

from . import database as db

logger = logging.getLogger(__name__)


class Analyzer:
    """競馬分析エンジン"""

    # スコア上限
    MAX_SCORE = 10.0

    def __init__(self, config: dict = None):
        self.config = config or {}

    # =========================================================================
    # A. 基礎スコアリング（各項目10点満点）
    # =========================================================================

    def calculate_base_scores(self, race: dict, entries: list) -> list:
        """
        全出走馬の基礎スコアを計算

        race: レース情報 dict
        entries: 出走馬リスト（各馬のデータを含む）
        戻り値: スコア付きのエントリーリスト
        """
        venue = race.get("venue", "")
        surface = race.get("surface", "")
        distance = race.get("distance")
        race_id = race.get("race_id", "")

        for entry in entries:
            horse_id = entry.get("horse_id", "")
            scores = {}

            # 1. 前走成績評価
            scores["prev_race"] = self._score_prev_race(horse_id)

            # 2. コース適性評価
            scores["course"] = self._score_course_aptitude(horse_id, venue, surface)

            # 3. 距離適性評価
            scores["distance"] = self._score_distance_aptitude(horse_id, distance, surface)

            # 4. 騎手評価
            scores["jockey"] = self._score_jockey(entry.get("jockey", ""), venue, surface)

            # 5. 枠順評価
            scores["gate"] = self._score_gate(venue, surface, distance, entry.get("gate"))

            # 6. 血統評価
            scores["pedigree"] = self._score_pedigree(
                horse_id, venue, surface, distance
            )

            # 合計スコア
            total = sum(scores.values())
            entry["scores"] = scores
            entry["base_score"] = round(total, 2)

        return entries

    def _score_prev_race(self, horse_id: str) -> float:
        """前走成績評価（10点満点）"""
        results = db.get_past_results(horse_id, limit=1)
        if not results:
            return 5.0  # データなしは中立

        last = results[0]
        pos = last.get("finish_position")
        if pos is None:
            return 5.0

        score_map = {1: 10, 2: 8, 3: 6}
        if pos in score_map:
            return float(score_map[pos])
        elif pos <= 5:
            return 4.0
        else:
            return 2.0

    def _score_course_aptitude(self, horse_id: str, venue: str, surface: str) -> float:
        """コース適性評価（10点満点）"""
        results = db.get_course_results(horse_id, venue, surface)
        if not results:
            return 5.0

        wins = sum(1 for r in results if r.get("finish_position") == 1)
        total = len(results)
        win_rate = wins / total if total > 0 else 0

        return min(win_rate * 100, self.MAX_SCORE)

    def _score_distance_aptitude(self, horse_id: str, distance: int,
                                  surface: str) -> float:
        """距離適性評価（10点満点）"""
        if distance is None:
            return 5.0

        results = db.get_past_results(horse_id, limit=20)
        if not results:
            return 5.0

        # 同距離 ± 200m のレースを検索
        matching = [r for r in results
                    if r.get("distance") and r.get("surface") == surface
                    and abs(r["distance"] - distance) <= 200]
        if not matching:
            return 5.0

        wins = sum(1 for r in matching if r.get("finish_position") == 1)
        total = len(matching)
        win_rate = wins / total if total > 0 else 0

        return min(win_rate * 100, self.MAX_SCORE)

    def _score_jockey(self, jockey_name: str, venue: str, surface: str) -> float:
        """騎手評価（10点満点）"""
        if not jockey_name:
            return 5.0

        stats = db.get_jockey_stat(jockey_name, venue)
        if not stats:
            return 5.0

        # コースに対応する統計を優先
        best = None
        for s in stats:
            if s.get("surface") == surface:
                best = s
                break
        if best is None:
            best = stats[0]

        win_rate = best.get("win_rate", 0)
        return min(win_rate * 100, self.MAX_SCORE)

    def _score_gate(self, venue: str, surface: str, distance: int,
                    gate: int) -> float:
        """枠順評価（10点満点）"""
        if gate is None:
            return 5.0

        stats = db.get_gate_statistics(venue, surface, distance)
        if not stats:
            return 5.0

        for s in stats:
            if s.get("gate") == gate:
                win_rate = s.get("win_rate", 0)
                return min(win_rate * 100, self.MAX_SCORE)

        return 5.0

    def _score_pedigree(self, horse_id: str, venue: str, surface: str,
                        distance: int) -> float:
        """血統評価（10点満点）"""
        # 馬情報から父馬を取得
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT sire FROM horses WHERE horse_id = ?", (horse_id,)
            ).fetchone()

        if not row or not row["sire"]:
            return 5.0

        sire = row["sire"]
        # 距離カテゴリ
        dist_cat = self._distance_category(distance) if distance else None

        stats = db.get_sire_stat(sire, venue, surface)
        if not stats:
            return 5.0

        best = stats[0]
        if dist_cat:
            for s in stats:
                if s.get("distance_category") == dist_cat:
                    best = s
                    break

        win_rate = best.get("win_rate", 0)
        return min(win_rate * 100, self.MAX_SCORE)

    @staticmethod
    def _distance_category(distance: int) -> str:
        """距離カテゴリの分類"""
        if distance is None:
            return None
        if distance <= 1400:
            return "短距離"
        elif distance <= 1800:
            return "マイル"
        elif distance <= 2200:
            return "中距離"
        else:
            return "長距離"

    # =========================================================================
    # B. 期待値計算
    # =========================================================================

    def calculate_expected_values(self, entries: list) -> list:
        """
        各馬の期待値を計算

        期待値 = (推定勝率 × 単勝オッズ) - 1
        """
        # 基礎スコアを正規化して推定勝率に変換
        total_score = sum(e.get("base_score", 0) for e in entries)
        if total_score <= 0:
            total_score = 1  # ゼロ除算防止

        for entry in entries:
            base_score = entry.get("base_score", 0)
            # 推定勝率（正規化）
            estimated_win_prob = base_score / total_score
            entry["estimated_win_prob"] = round(estimated_win_prob, 4)

            odds = entry.get("odds_win")
            if odds and odds > 0:
                # 期待値 = (推定勝率 × 単勝オッズ) - 1
                ev = (estimated_win_prob * odds) - 1
                entry["expected_value"] = round(ev, 4)

                # オッズから算出される暗黙の勝率
                odds_implied_prob = 1.0 / odds
                entry["odds_implied_prob"] = round(odds_implied_prob, 4)

                # 乖離率（推定勝率がオッズ暗黙勝率より高い → プラス乖離 = お買い得）
                if odds_implied_prob > 0:
                    divergence = (estimated_win_prob - odds_implied_prob) / odds_implied_prob
                    entry["prob_divergence"] = round(divergence, 4)
                else:
                    entry["prob_divergence"] = 0
            else:
                entry["expected_value"] = None
                entry["odds_implied_prob"] = None
                entry["prob_divergence"] = None

        return entries

    # =========================================================================
    # C. リスクリワード評価
    # =========================================================================

    def calculate_risk_reward(self, entries: list) -> list:
        """
        リスクリワード比を計算

        R/R比 = 期待リターン / 期待損失
        推奨基準:
        - 1.5以上: 強く推奨 (◎)
        - 1.2-1.5: 推奨 (○)
        - 1.0-1.2: 検討可 (△)
        - 1.0未満: 回避 (×)
        """
        for entry in entries:
            prob = entry.get("estimated_win_prob", 0)
            odds = entry.get("odds_win")

            if odds and odds > 0 and prob > 0:
                expected_return = prob * (odds - 1)  # 的中時のリターン × 的中率
                expected_loss = (1 - prob) * 1        # 外れた場合の損失 × 非的中率
                rr = expected_return / expected_loss if expected_loss > 0 else 0
                entry["risk_reward"] = round(rr, 4)

                # 推奨度判定
                if rr >= 1.5:
                    entry["recommendation"] = "◎本命"
                    entry["rec_stars"] = "★★★"
                    entry["rec_level"] = 3
                elif rr >= 1.2:
                    entry["recommendation"] = "○対抗"
                    entry["rec_stars"] = "★★☆"
                    entry["rec_level"] = 2
                elif rr >= 1.0:
                    entry["recommendation"] = "△検討"
                    entry["rec_stars"] = "★☆☆"
                    entry["rec_level"] = 1
                else:
                    entry["recommendation"] = "×回避"
                    entry["rec_stars"] = "☆☆☆"
                    entry["rec_level"] = 0
            else:
                entry["risk_reward"] = None
                entry["recommendation"] = "−データ不足"
                entry["rec_stars"] = "−"
                entry["rec_level"] = -1

        return entries

    # =========================================================================
    # D. レース展開予想
    # =========================================================================

    def predict_race_development(self, entries: list) -> dict:
        """
        レース展開を予想

        戻り値: {
            "pace": "ハイペース"|"平均"|"スローペース",
            "style_distribution": {"逃げ": N, "先行": N, "差し": N, "追込": N},
            "pace_advantage": "先行有利"|"差し有利"|"展開不明",
            "entries": [各馬に展開評価を追加]
        }
        """
        # 各馬の想定脚質を収集
        styles = []
        for entry in entries:
            style = entry.get("running_style")
            if not style:
                style = self._estimate_style_from_history(entry.get("horse_id", ""))
                entry["running_style"] = style
            if style:
                styles.append(style)

        style_counts = Counter(styles)
        n_escape = style_counts.get("逃げ", 0)
        n_front = style_counts.get("先行", 0)
        n_closer = style_counts.get("差し", 0)
        n_late = style_counts.get("追込", 0)

        # ペース予想
        front_ratio = (n_escape + n_front) / len(entries) if entries else 0

        if n_escape >= 3 or front_ratio >= 0.5:
            pace = "ハイペース"
            pace_advantage = "差し・追込有利"
        elif n_escape <= 1 and front_ratio <= 0.3:
            pace = "スローペース"
            pace_advantage = "逃げ・先行有利"
        else:
            pace = "平均ペース"
            pace_advantage = "展開次第"

        # 各馬に展開の有利不利を付与
        for entry in entries:
            style = entry.get("running_style")
            if pace == "ハイペース":
                if style in ("差し", "追込"):
                    entry["pace_score"] = 2.0  # ボーナス
                elif style == "逃げ":
                    entry["pace_score"] = -2.0  # ペナルティ
                else:
                    entry["pace_score"] = 0.0
            elif pace == "スローペース":
                if style in ("逃げ", "先行"):
                    entry["pace_score"] = 2.0
                elif style == "追込":
                    entry["pace_score"] = -2.0
                else:
                    entry["pace_score"] = 0.0
            else:
                entry["pace_score"] = 0.0

        return {
            "pace": pace,
            "style_distribution": dict(style_counts),
            "pace_advantage": pace_advantage,
            "entries": entries,
        }

    def _estimate_style_from_history(self, horse_id: str) -> str:
        """過去成績から脚質を推定"""
        results = db.get_past_results(horse_id, limit=5)
        if not results:
            return "差し"  # デフォルト

        styles = [r.get("running_style") for r in results if r.get("running_style")]
        if not styles:
            return "差し"

        counter = Counter(styles)
        return counter.most_common(1)[0][0]

    # =========================================================================
    # 統合分析
    # =========================================================================

    def analyze_race(self, race: dict, entries: list) -> dict:
        """
        1レースの統合分析を実行

        戻り値: {
            "race": レース情報,
            "entries": 分析済みエントリーリスト,
            "development": 展開予想,
            "recommendations": 推奨馬リスト,
            "confidence": 信頼度
        }
        """
        logger.info("分析開始: %s %dR %s",
                     race.get("venue"), race.get("race_number"),
                     race.get("race_name", ""))

        # 1. 基礎スコア計算
        entries = self.calculate_base_scores(race, entries)

        # 2. 展開予想（ペーススコアの付与）
        development = self.predict_race_development(entries)
        entries = development["entries"]

        # ペーススコアを基礎スコアに加算
        for entry in entries:
            pace_bonus = entry.get("pace_score", 0)
            entry["base_score"] = round(entry.get("base_score", 0) + pace_bonus, 2)

        # 3. 期待値計算
        entries = self.calculate_expected_values(entries)

        # 4. リスクリワード評価
        entries = self.calculate_risk_reward(entries)

        # 5. 推奨馬の抽出
        recommendations = self._extract_recommendations(entries)

        # 6. 信頼度の算出
        confidence = self._calculate_confidence(entries)

        # 7. DB更新
        for entry in entries:
            db.upsert_entry({
                "entry_id": entry["entry_id"],
                "race_id": entry["race_id"],
                "horse_id": entry["horse_id"],
                "horse_name": entry["horse_name"],
                "jockey": entry.get("jockey", ""),
                "trainer": entry.get("trainer", ""),
                "gate": entry.get("gate"),
                "horse_number": entry.get("horse_number"),
                "weight": entry.get("weight"),
                "horse_weight": entry.get("horse_weight"),
                "horse_weight_diff": entry.get("horse_weight_diff"),
                "odds_win": entry.get("odds_win"),
                "odds_place_min": entry.get("odds_place_min"),
                "odds_place_max": entry.get("odds_place_max"),
                "running_style": entry.get("running_style"),
                "base_score": entry.get("base_score"),
                "expected_value": entry.get("expected_value"),
                "risk_reward": entry.get("risk_reward"),
                "recommendation": entry.get("recommendation"),
            })

        result = {
            "race": race,
            "entries": sorted(entries,
                              key=lambda e: e.get("expected_value") or -999,
                              reverse=True),
            "development": development,
            "recommendations": recommendations,
            "confidence": confidence,
        }

        logger.info("分析完了: %s %dR - 推奨馬 %d 頭, 信頼度 %s",
                     race.get("venue"), race.get("race_number"),
                     len(recommendations), confidence)

        return result

    def _extract_recommendations(self, entries: list) -> list:
        """推奨馬を抽出"""
        recs = []
        for entry in entries:
            ev = entry.get("expected_value")
            rr = entry.get("risk_reward")
            if ev is not None and ev > 0 and rr is not None and rr >= 1.0:
                recs.append({
                    "horse_name": entry["horse_name"],
                    "horse_number": entry.get("horse_number"),
                    "odds": entry.get("odds_win"),
                    "expected_value": ev,
                    "risk_reward": rr,
                    "recommendation": entry.get("recommendation"),
                    "rec_stars": entry.get("rec_stars"),
                })

        # 期待値の高い順にソート
        recs.sort(key=lambda x: x["expected_value"], reverse=True)
        return recs

    def _calculate_confidence(self, entries: list) -> str:
        """分析の信頼度を算出"""
        # データ充実度に基づく信頼度
        data_count = 0
        total = len(entries)
        if total == 0:
            return "低"

        for entry in entries:
            has_odds = entry.get("odds_win") is not None
            has_history = entry.get("past_results") and len(entry["past_results"]) > 0
            has_score = entry.get("base_score", 0) > 0
            if has_odds and has_score:
                data_count += 1
            elif has_odds or has_history:
                data_count += 0.5

        ratio = data_count / total

        if ratio >= 0.8:
            return "高"
        elif ratio >= 0.5:
            return "中"
        else:
            return "低"

    def analyze_all_races(self, races: list) -> list:
        """複数レースを一括分析"""
        results = []
        for race in races:
            entries = race.get("entries", [])
            if not entries:
                entries = db.get_entries_by_race(race.get("race_id", ""))
            if entries:
                result = self.analyze_race(race, entries)
                results.append(result)
        return results

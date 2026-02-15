"""
data_collector.py - データ収集モジュール
JRA公式サイト・netkeiba.comからレース情報を収集
"""

import re
import time
import json
import logging
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from . import database as db

logger = logging.getLogger(__name__)

# 定数
VENUES = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟",
    "05": "東京", "06": "中山", "07": "中京", "08": "京都",
    "09": "阪神", "10": "小倉",
}
VENUE_NAME_TO_CODE = {v: k for k, v in VENUES.items()}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_HEADERS = {"User-Agent": USER_AGENT}
REQUEST_DELAY = 2  # リクエスト間隔（秒）
MAX_RETRIES = 3


class DataCollector:
    """競馬データ収集クラス"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.session = requests.Session()
        self.session.headers.update(REQUEST_HEADERS)

    def _fetch(self, url: str, encoding: str = None) -> BeautifulSoup:
        """URLからHTMLを取得してパース"""
        for attempt in range(MAX_RETRIES):
            try:
                time.sleep(REQUEST_DELAY)
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
                if encoding:
                    resp.encoding = encoding
                return BeautifulSoup(resp.text, "html.parser")
            except requests.RequestException as e:
                logger.warning("取得失敗 (試行 %d/%d): %s - %s",
                               attempt + 1, MAX_RETRIES, url, e)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(REQUEST_DELAY * (attempt + 1))
        logger.error("データ取得に失敗しました: %s", url)
        return None

    @staticmethod
    def _generate_id(*parts) -> str:
        """一意のIDを生成"""
        raw = "_".join(str(p) for p in parts)
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    # =========================================================================
    # JRA公式サイトからのデータ収集
    # =========================================================================

    def collect_jra_race_list(self, date_str: str) -> list:
        """
        JRA公式サイトから指定日のレース一覧を取得
        date_str: YYYY-MM-DD 形式
        戻り値: レース情報のリスト
        """
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        jra_date = dt.strftime("%Y%m%d")

        url = f"https://www.jra.go.jp/keiba/calendar/{dt.year}/{dt.strftime('%m%d')}.html"
        logger.info("JRAレース一覧取得: %s", url)

        soup = self._fetch(url)
        races = []

        if soup is None:
            logger.warning("JRAからレース一覧を取得できませんでした。代替データを使用します。")
            return self._get_race_list_from_netkeiba(date_str)

        # JRAページ構造解析（レースリンクを探す）
        race_links = soup.find_all("a", href=re.compile(r"/JRADB/accessS\.html"))
        if not race_links:
            race_links = soup.find_all("a", href=re.compile(r"race"))

        if not race_links:
            logger.info("JRAのページ構造が変更された可能性があります。netkeibaから取得します。")
            return self._get_race_list_from_netkeiba(date_str)

        for link in race_links:
            try:
                race_info = self._parse_jra_race_link(link, date_str)
                if race_info:
                    races.append(race_info)
            except Exception as e:
                logger.warning("レース情報のパースに失敗: %s", e)

        return races

    def _parse_jra_race_link(self, link_element, date_str: str) -> dict:
        """JRAのレースリンクからレース情報を抽出"""
        text = link_element.get_text(strip=True)
        href = link_element.get("href", "")

        race_num_match = re.search(r"(\d+)R", text)
        if not race_num_match:
            return None

        race_number = int(race_num_match.group(1))
        if race_number < 10:
            return None

        venue_name = None
        for v in VENUES.values():
            if v in text:
                venue_name = v
                break

        if not venue_name:
            parent = link_element.find_parent()
            if parent:
                parent_text = parent.get_text()
                for v in VENUES.values():
                    if v in parent_text:
                        venue_name = v
                        break

        if not venue_name:
            return None

        race_id = self._generate_id(date_str, venue_name, race_number)
        return {
            "race_id": race_id,
            "date": date_str,
            "venue": venue_name,
            "race_number": race_number,
            "race_name": text,
            "distance": None,
            "surface": None,
            "condition": None,
            "weather": None,
            "post_time": None,
        }

    # =========================================================================
    # netkeibaからのデータ収集
    # =========================================================================

    def _get_race_list_from_netkeiba(self, date_str: str) -> list:
        """netkeibaからレース一覧を取得"""
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        nk_date = dt.strftime("%Y%m%d")

        url = f"https://race.netkeiba.com/top/race_list.html?kaisai_date={nk_date}"
        logger.info("netkeiba レース一覧取得: %s", url)

        soup = self._fetch(url, encoding="EUC-JP")
        races = []

        if soup is None:
            return races

        # レースリンクのパターン
        race_links = soup.find_all("a", href=re.compile(r"race_id=\d+"))

        seen_ids = set()
        for link in race_links:
            try:
                href = link.get("href", "")
                race_id_match = re.search(r"race_id=(\d+)", href)
                if not race_id_match:
                    continue

                nk_race_id = race_id_match.group(1)
                if nk_race_id in seen_ids:
                    continue
                seen_ids.add(nk_race_id)

                # race_idの構造: YYYYVVKKNNRR
                # YYYY=年, VV=競馬場コード, KK=開催回, NN=日, RR=レース番号
                if len(nk_race_id) >= 12:
                    venue_code = nk_race_id[4:6]
                    race_number = int(nk_race_id[10:12])
                else:
                    continue

                if race_number < 10:
                    continue

                venue_name = VENUES.get(venue_code, "不明")
                text = link.get_text(strip=True)
                race_name = text if text else f"{venue_name}{race_number}R"

                race_id = self._generate_id(date_str, venue_name, race_number)
                races.append({
                    "race_id": race_id,
                    "netkeiba_race_id": nk_race_id,
                    "date": date_str,
                    "venue": venue_name,
                    "race_number": race_number,
                    "race_name": race_name,
                    "distance": None,
                    "surface": None,
                    "condition": None,
                    "weather": None,
                    "post_time": None,
                })
            except Exception as e:
                logger.warning("netkeibaレース解析失敗: %s", e)

        return races

    def collect_race_detail_netkeiba(self, netkeiba_race_id: str, race_id: str) -> dict:
        """netkeibaからレース詳細（出馬表）を取得"""
        url = f"https://race.netkeiba.com/race/shutuba.html?race_id={netkeiba_race_id}"
        logger.info("出馬表取得: %s", url)

        soup = self._fetch(url, encoding="EUC-JP")
        if soup is None:
            return None

        result = {"race_info": {}, "entries": []}

        # レース情報の取得
        race_info = self._parse_race_header(soup, race_id)
        result["race_info"] = race_info

        # 出馬表の取得
        entries = self._parse_shutuba_table(soup, race_id)
        result["entries"] = entries

        return result

    def _parse_race_header(self, soup: BeautifulSoup, race_id: str) -> dict:
        """レースヘッダー情報をパース"""
        info = {}

        # レース名
        race_name_el = soup.find("div", class_="RaceName") or soup.find("h1", class_="RaceName")
        if race_name_el:
            info["race_name"] = race_name_el.get_text(strip=True)

        # レース条件（距離、馬場等）
        race_data_el = (soup.find("div", class_="RaceData01") or
                        soup.find("span", class_="RaceData01"))
        if race_data_el:
            text = race_data_el.get_text(strip=True)
            # 距離の抽出
            dist_match = re.search(r"(\d{4})m", text)
            if dist_match:
                info["distance"] = int(dist_match.group(1))

            # 芝/ダートの判定
            if "芝" in text:
                info["surface"] = "芝"
            elif "ダ" in text or "ダート" in text:
                info["surface"] = "ダート"
            elif "障" in text:
                info["surface"] = "障害"

            # 天候
            weather_match = re.search(r"天候:(\S+)", text)
            if weather_match:
                info["weather"] = weather_match.group(1)

            # 馬場状態
            cond_match = re.search(r"馬場:(\S+)", text)
            if cond_match:
                info["condition"] = cond_match.group(1)

            # 発走時刻
            time_match = re.search(r"(\d{1,2}:\d{2})", text)
            if time_match:
                info["post_time"] = time_match.group(1)

        return info

    def _parse_shutuba_table(self, soup: BeautifulSoup, race_id: str) -> list:
        """出馬表テーブルをパース"""
        entries = []

        # テーブルの探索
        table = (soup.find("table", class_="Shutuba_Table") or
                 soup.find("table", class_="RaceTable01") or
                 soup.find("table", id="shutuba_table"))

        if not table:
            logger.warning("出馬表テーブルが見つかりません")
            return entries

        rows = table.find_all("tr", class_=re.compile(r"HorseList"))
        if not rows:
            rows = table.find_all("tr")[1:]  # ヘッダーをスキップ

        for row in rows:
            try:
                entry = self._parse_horse_row(row, race_id)
                if entry:
                    entries.append(entry)
            except Exception as e:
                logger.warning("馬情報のパースに失敗: %s", e)

        return entries

    def _parse_horse_row(self, row, race_id: str) -> dict:
        """出馬表の1行（1頭分）をパース"""
        cells = row.find_all("td")
        if len(cells) < 4:
            return None

        # 各セルのテキスト取得
        cell_texts = [c.get_text(strip=True) for c in cells]

        # 枠番・馬番
        gate = self._safe_int(cell_texts[0]) if len(cell_texts) > 0 else None
        horse_number = self._safe_int(cell_texts[1]) if len(cell_texts) > 1 else None

        if horse_number is None:
            return None

        # 馬名
        horse_name = ""
        horse_id = ""
        horse_link = row.find("a", href=re.compile(r"horse/\d+"))
        if horse_link:
            horse_name = horse_link.get_text(strip=True)
            id_match = re.search(r"horse/(\d+)", horse_link.get("href", ""))
            if id_match:
                horse_id = id_match.group(1)
        else:
            horse_name = cell_texts[3] if len(cell_texts) > 3 else f"馬{horse_number}"
            horse_id = self._generate_id(race_id, horse_number)

        # 性別・年齢
        sex = ""
        age = None
        sex_age_text = cell_texts[4] if len(cell_texts) > 4 else ""
        sex_age_match = re.match(r"([牡牝セ])(\d+)", sex_age_text)
        if sex_age_match:
            sex = sex_age_match.group(1)
            age = int(sex_age_match.group(2))

        # 斤量
        weight = self._safe_float(cell_texts[5]) if len(cell_texts) > 5 else None

        # 騎手
        jockey = ""
        jockey_link = row.find("a", href=re.compile(r"jockey"))
        if jockey_link:
            jockey = jockey_link.get_text(strip=True)
        elif len(cell_texts) > 6:
            jockey = cell_texts[6]

        # 調教師
        trainer = ""
        trainer_link = row.find("a", href=re.compile(r"trainer"))
        if trainer_link:
            trainer = trainer_link.get_text(strip=True)
        elif len(cell_texts) > 7:
            trainer = cell_texts[7]

        # 馬体重
        horse_weight = None
        horse_weight_diff = None
        for cell_text in cell_texts:
            wt_match = re.search(r"(\d{3,4})\(([+\-]?\d+)\)", cell_text)
            if wt_match:
                horse_weight = float(wt_match.group(1))
                horse_weight_diff = float(wt_match.group(2))
                break

        # 単勝オッズ
        odds_win = None
        odds_cell = row.find("td", class_=re.compile(r"[Oo]dds"))
        if odds_cell:
            odds_win = self._safe_float(odds_cell.get_text(strip=True))

        entry_id = self._generate_id(race_id, horse_number)

        return {
            "entry_id": entry_id,
            "race_id": race_id,
            "horse_id": horse_id,
            "horse_name": horse_name,
            "jockey": jockey,
            "trainer": trainer,
            "gate": gate,
            "horse_number": horse_number,
            "weight": weight,
            "horse_weight": horse_weight,
            "horse_weight_diff": horse_weight_diff,
            "odds_win": odds_win,
            "odds_place_min": None,
            "odds_place_max": None,
            "sex": sex,
            "age": age,
            "running_style": None,
            "base_score": None,
            "expected_value": None,
            "risk_reward": None,
            "recommendation": None,
        }

    # =========================================================================
    # オッズ取得
    # =========================================================================

    def collect_odds(self, netkeiba_race_id: str, race_id: str) -> list:
        """netkeibaからオッズを取得"""
        url = f"https://race.netkeiba.com/odds/index.html?race_id={netkeiba_race_id}&type=b1"
        logger.info("オッズ取得: %s", url)

        soup = self._fetch(url, encoding="EUC-JP")
        if soup is None:
            return []

        odds_data = []
        # オッズテーブルの解析
        table = soup.find("table", class_=re.compile(r"[Oo]dds"))
        if not table:
            # 代替: JSON APIからの取得を試行
            return self._collect_odds_api(netkeiba_race_id, race_id)

        rows = table.find_all("tr")[1:]
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                horse_num = self._safe_int(cells[0].get_text(strip=True))
                odds_win = self._safe_float(cells[1].get_text(strip=True))
                if horse_num and odds_win:
                    odds_data.append({
                        "horse_number": horse_num,
                        "odds_win": odds_win,
                    })

        return odds_data

    def _collect_odds_api(self, netkeiba_race_id: str, race_id: str) -> list:
        """netkeibaのAPI経由でオッズを取得（代替手段）"""
        url = f"https://race.netkeiba.com/api/api_get_jra_odds.html?race_id={netkeiba_race_id}&type=1"
        logger.info("オッズAPI取得: %s", url)

        try:
            time.sleep(REQUEST_DELAY)
            resp = self.session.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return self._parse_odds_json(data, race_id)
        except Exception as e:
            logger.warning("オッズAPI取得失敗: %s", e)

        return []

    def _parse_odds_json(self, data: dict, race_id: str) -> list:
        """オッズJSONデータをパース"""
        odds_data = []
        if isinstance(data, dict) and "data" in data:
            for item in data["data"]:
                try:
                    odds_data.append({
                        "horse_number": int(item.get("umaban", 0)),
                        "odds_win": float(item.get("odds", 0)),
                    })
                except (ValueError, TypeError):
                    continue
        return odds_data

    # =========================================================================
    # 過去成績の収集
    # =========================================================================

    def collect_horse_history(self, horse_id: str, limit: int = 10) -> list:
        """netkeibaから馬の過去成績を収集"""
        url = f"https://db.netkeiba.com/horse/{horse_id}/"
        logger.info("馬の過去成績取得: %s (horse_id=%s)", url, horse_id)

        soup = self._fetch(url, encoding="EUC-JP")
        if soup is None:
            return []

        results = []
        table = soup.find("table", class_="db_h_race_results")
        if not table:
            table = soup.find("table", summary="競走成績")

        if not table:
            logger.warning("成績テーブルが見つかりません: horse_id=%s", horse_id)
            return []

        rows = table.find_all("tr")[1:limit + 1]
        for row in rows:
            try:
                result = self._parse_history_row(row, horse_id)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning("過去成績のパースに失敗: %s", e)

        return results

    def _parse_history_row(self, row, horse_id: str) -> dict:
        """過去成績の1行をパース"""
        cells = row.find_all("td")
        if len(cells) < 10:
            return None

        cell_texts = [c.get_text(strip=True) for c in cells]

        date_str = cell_texts[0] if len(cell_texts) > 0 else ""
        venue = cell_texts[1] if len(cell_texts) > 1 else ""
        race_name = cell_texts[4] if len(cell_texts) > 4 else ""

        # 距離・馬場
        distance = None
        surface = None
        dist_text = cell_texts[14] if len(cell_texts) > 14 else cell_texts[3] if len(cell_texts) > 3 else ""
        if dist_text:
            if "芝" in dist_text:
                surface = "芝"
            elif "ダ" in dist_text:
                surface = "ダート"
            d_match = re.search(r"(\d{4})", dist_text)
            if d_match:
                distance = int(d_match.group(1))

        # 着順
        finish_pos = self._safe_int(cell_texts[11]) if len(cell_texts) > 11 else None
        if finish_pos is None:
            finish_pos = self._safe_int(cell_texts[5]) if len(cell_texts) > 5 else None

        # 頭数
        field_size = self._safe_int(cell_texts[6]) if len(cell_texts) > 6 else None

        # タイム
        finish_time = cell_texts[7] if len(cell_texts) > 7 else None

        # 着差
        margin = cell_texts[8] if len(cell_texts) > 8 else None

        # 騎手
        jockey = cell_texts[12] if len(cell_texts) > 12 else None
        if not jockey:
            jockey_link = row.find("a", href=re.compile(r"jockey"))
            if jockey_link:
                jockey = jockey_link.get_text(strip=True)

        # 斤量
        weight = self._safe_float(cell_texts[13]) if len(cell_texts) > 13 else None

        # オッズ
        odds = self._safe_float(cell_texts[9]) if len(cell_texts) > 9 else None

        # 馬場状態
        condition = cell_texts[2] if len(cell_texts) > 2 else None

        # 通過順（脚質推定用）
        running_style = None
        pass_text = cell_texts[10] if len(cell_texts) > 10 else ""
        if pass_text:
            running_style = self._estimate_running_style(pass_text, field_size)

        result_id = self._generate_id(horse_id, date_str, venue, race_name)

        return {
            "result_id": result_id,
            "horse_id": horse_id,
            "date": date_str,
            "venue": venue,
            "race_name": race_name,
            "distance": distance,
            "surface": surface,
            "condition": condition,
            "finish_position": finish_pos,
            "field_size": field_size,
            "finish_time": finish_time,
            "margin": margin,
            "weight": weight,
            "jockey": jockey,
            "odds": odds,
            "running_style": running_style,
        }

    def _estimate_running_style(self, pass_order_text: str, field_size: int = None) -> str:
        """通過順位から脚質を推定"""
        positions = re.findall(r"\d+", pass_order_text)
        if not positions:
            return None

        positions = [int(p) for p in positions]
        first_pos = positions[0]
        size = field_size or 18

        ratio = first_pos / size if size > 0 else 0.5

        if ratio <= 0.15:
            return "逃げ"
        elif ratio <= 0.35:
            return "先行"
        elif ratio <= 0.65:
            return "差し"
        else:
            return "追込"

    # =========================================================================
    # 血統情報の収集
    # =========================================================================

    def collect_horse_pedigree(self, horse_id: str) -> dict:
        """netkeibaから血統情報を収集"""
        url = f"https://db.netkeiba.com/horse/{horse_id}/"
        logger.info("血統情報取得: %s", url)

        soup = self._fetch(url, encoding="EUC-JP")
        if soup is None:
            return {}

        pedigree = {"sire": None, "dam_sire": None}

        # 血統テーブル
        ped_table = soup.find("table", class_="blood_table")
        if ped_table:
            links = ped_table.find_all("a", href=re.compile(r"horse/ped"))
            if len(links) >= 1:
                pedigree["sire"] = links[0].get_text(strip=True)
            if len(links) >= 3:
                pedigree["dam_sire"] = links[2].get_text(strip=True)
        else:
            # プロフィール欄から取得
            profile = soup.find("div", class_="db_prof_area_02")
            if profile:
                text = profile.get_text()
                sire_match = re.search(r"父[：:](.+?)[\n\r]", text)
                if sire_match:
                    pedigree["sire"] = sire_match.group(1).strip()
                dam_sire_match = re.search(r"母父[：:](.+?)[\n\r]", text)
                if dam_sire_match:
                    pedigree["dam_sire"] = dam_sire_match.group(1).strip()

        return pedigree

    # =========================================================================
    # 天気情報の取得
    # =========================================================================

    def collect_weather(self, venue: str) -> dict:
        """競馬場の天気情報を取得（概要のみ）"""
        # 天気情報はJRA公式サイトのレース情報から取得
        # ここではダミー実装（実際はレース詳細取得時に天候情報を取得）
        return {"weather": "不明", "condition": "不明"}

    # =========================================================================
    # メインの収集フロー
    # =========================================================================

    def collect_weekend_races(self, target_date: str = None) -> list:
        """
        週末のメインレース（10R以降）のデータを一括収集

        target_date: 対象日 (YYYY-MM-DD形式)。Noneの場合は次の土曜日。
        戻り値: 収集したレースのリスト
        """
        if target_date is None:
            today = datetime.now()
            days_until_saturday = (5 - today.weekday()) % 7
            if days_until_saturday == 0 and today.hour >= 18:
                days_until_saturday = 7
            target = today + timedelta(days=days_until_saturday)
            target_date = target.strftime("%Y-%m-%d")

        logger.info("=== データ収集開始: %s ===", target_date)

        # 1. レース一覧を取得
        races = self._get_race_list_from_netkeiba(target_date)
        if not races:
            races = self.collect_jra_race_list(target_date)

        logger.info("取得レース数: %d", len(races))

        collected_races = []

        for race in races:
            try:
                nk_race_id = race.get("netkeiba_race_id")
                race_id = race["race_id"]

                # 2. レース詳細・出馬表を取得
                if nk_race_id:
                    detail = self.collect_race_detail_netkeiba(nk_race_id, race_id)
                    if detail:
                        # レース情報を更新
                        race_info = detail.get("race_info", {})
                        race.update({k: v for k, v in race_info.items() if v is not None})

                        # DBに保存
                        db_race = {
                            "race_id": race_id,
                            "date": race["date"],
                            "venue": race["venue"],
                            "race_number": race["race_number"],
                            "race_name": race.get("race_name", ""),
                            "distance": race.get("distance"),
                            "surface": race.get("surface"),
                            "condition": race.get("condition"),
                            "weather": race.get("weather"),
                            "post_time": race.get("post_time"),
                        }
                        db.upsert_race(db_race)

                        entries = detail.get("entries", [])
                        race["entries"] = entries

                        # 各馬のデータ処理
                        for entry in entries:
                            # 馬情報をDBに保存
                            self._save_horse_data(entry)
                            # 出走記録をDBに保存
                            self._save_entry_data(entry)

                            # 過去成績を取得
                            if entry.get("horse_id") and not entry["horse_id"].startswith(race_id[:8]):
                                history = self.collect_horse_history(entry["horse_id"], limit=5)
                                for h in history:
                                    db.insert_past_result(h)
                                entry["past_results"] = history

                                # 血統情報を取得
                                pedigree = self.collect_horse_pedigree(entry["horse_id"])
                                if pedigree.get("sire"):
                                    entry["sire"] = pedigree["sire"]
                                    entry["dam_sire"] = pedigree.get("dam_sire")
                                    db.upsert_horse({
                                        "horse_id": entry["horse_id"],
                                        "horse_name": entry["horse_name"],
                                        "birth_year": None,
                                        "sex": entry.get("sex", ""),
                                        "sire": pedigree["sire"],
                                        "dam_sire": pedigree.get("dam_sire"),
                                    })

                        collected_races.append(race)
                        logger.info("収集完了: %s %dR %s",
                                    race["venue"], race["race_number"],
                                    race.get("race_name", ""))

                # オッズ取得
                if nk_race_id:
                    odds_list = self.collect_odds(nk_race_id, race_id)
                    if odds_list:
                        self._apply_odds(race, odds_list)

            except Exception as e:
                logger.error("レースデータ収集エラー: %s - %s", race.get("race_name", ""), e)

        logger.info("=== データ収集完了: %d レース ===", len(collected_races))
        return collected_races

    def update_odds_only(self, target_date: str) -> list:
        """オッズのみを再取得して更新"""
        races = db.get_races_by_date(target_date)
        updated = []

        for race in races:
            entries = db.get_entries_by_race(race["race_id"])
            if not entries:
                continue

            # netkeiba race_id を推定
            # （本来はDB内にnetkeiba_race_idを保存すべきだが、簡易実装として再取得）
            nk_races = self._get_race_list_from_netkeiba(target_date)
            for nk_race in nk_races:
                if (nk_race["venue"] == race["venue"] and
                        nk_race["race_number"] == race["race_number"]):
                    nk_race_id = nk_race.get("netkeiba_race_id")
                    if nk_race_id:
                        odds_list = self.collect_odds(nk_race_id, race["race_id"])
                        if odds_list:
                            for odds_item in odds_list:
                                for entry in entries:
                                    if entry["horse_number"] == odds_item["horse_number"]:
                                        db.upsert_entry({
                                            **entry,
                                            "odds_win": odds_item["odds_win"],
                                        })
                            updated.append(race)
                    break

        return updated

    # =========================================================================
    # ヘルパーメソッド
    # =========================================================================

    def _save_horse_data(self, entry: dict):
        """馬情報をDBに保存"""
        db.upsert_horse({
            "horse_id": entry["horse_id"],
            "horse_name": entry["horse_name"],
            "birth_year": None,
            "sex": entry.get("sex", ""),
            "sire": entry.get("sire"),
            "dam_sire": entry.get("dam_sire"),
        })

    def _save_entry_data(self, entry: dict):
        """出走記録をDBに保存"""
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

    def _apply_odds(self, race: dict, odds_list: list):
        """オッズデータをレースの各馬に適用"""
        entries = race.get("entries", [])
        for odds_item in odds_list:
            for entry in entries:
                if entry.get("horse_number") == odds_item["horse_number"]:
                    entry["odds_win"] = odds_item["odds_win"]
                    self._save_entry_data(entry)
                    break

    @staticmethod
    def _safe_int(text: str) -> int:
        """安全にintに変換"""
        try:
            return int(re.sub(r"[^\d]", "", str(text)))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_float(text: str) -> float:
        """安全にfloatに変換"""
        try:
            cleaned = re.sub(r"[^\d.]", "", str(text))
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None

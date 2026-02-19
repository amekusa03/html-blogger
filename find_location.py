# -*- coding: utf-8 -*-

import logging
import re
import time
import xml.etree.ElementTree as ET
from logging import config, getLogger
from pathlib import Path

from bs4 import BeautifulSoup
from geopy.exc import GeocoderQuotaExceeded, GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim
from janome.tokenizer import Tokenizer
from json5 import load

from cons_progressber import ProgressBar
from file_class import SmartFile
from parameter import config, to_bool

# logging設定
with open("./data/log_config.json5", "r") as f:
    logging.config.dictConfig(load(f))
logger = getLogger(__name__)

# --- 設定 ---

# 入力元フォルダ
input_dir = config["find_location"]["input_dir"].lstrip("./")
# 出力先フォルダ
output_dir = config["find_location"]["output_dir"].lstrip("./")
location_xml_file = config["find_location"]["location_xml_file"]
geocode_retries = int(config["find_location"]["geocode_retries"])
geocode_wait = float(config["find_location"]["geocode_wait"])
geocode_timeout = int(config["find_location"]["geocode_timeout"])
geocode_debug = to_bool(config["find_location"]["geocode_debug"])
html_extensions = config["common"]["html_extensions"]
location_cache = None


def load_cache_location():
    """location.xmlから地域情報を読み込む"""
    global location_cache
    location_cache = {}
    try:
        if not Path(location_xml_file).exists():
            logger.warning(f"{location_xml_file} が見つかりません。")
            return False
        tree = ET.parse(str(Path(location_xml_file)))
        root = tree.getroot()

        for location in root.findall("location"):
            name_elem = location.find("name")
            lat_elem = location.find("latitude")
            lon_elem = location.find("longitude")

            if name_elem is not None and name_elem.text is not None:
                name = name_elem.text.strip()
                latitude = (
                    lat_elem.text.strip()
                    if lat_elem is not None and lat_elem.text is not None
                    else ""
                )
                longitude = (
                    lon_elem.text.strip()
                    if lon_elem is not None and lon_elem.text is not None
                    else ""
                )
                if name:
                    location_cache[name.lower()] = (name, latitude, longitude)
    except Exception as e:
        logger.error(f"XML読み込みエラー: {e}", exc_info=True)
    return True


def save_location_cache(location_name, latitude="", longitude=""):
    """location.xmlにキャッシュを保存"""
    try:
        if not Path(location_xml_file).exists():
            root = ET.Element("root")
            tree = ET.ElementTree(root)
        else:
            tree = ET.parse(str(Path(location_xml_file)))
            root = tree.getroot()

        for location in root.findall("location"):
            name_elem = location.find("name")
            if name_elem is not None and name_elem.text == location_name:
                lat_elem = location.find("latitude")
                lon_elem = location.find("longitude")
                if lat_elem is not None:
                    lat_elem.text = str(latitude) if latitude else ""
                if lon_elem is not None:
                    lon_elem.text = str(longitude) if longitude else ""
                indent_xml(root)
                tree.write(
                    str(Path(location_xml_file)), encoding="utf-8", xml_declaration=True
                )
                return

        location_elem = ET.SubElement(root, "location")
        ET.SubElement(location_elem, "name").text = location_name
        ET.SubElement(location_elem, "latitude").text = (
            str(latitude) if latitude else ""
        )
        ET.SubElement(location_elem, "longitude").text = (
            str(longitude) if longitude else ""
        )
        indent_xml(root)
        tree.write(str(Path(location_xml_file)), encoding="utf-8", xml_declaration=True)
    except Exception as e:
        logger.error(f"XML保存エラー: {e}", exc_info=True)


def indent_xml(elem, level=0):
    """XMLツリーにインデントと改行を追加する"""
    i = "\n" + level * "    "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "    "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent_xml(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def find_location_in_html(files):
    """HTML内で地域名を検索し、座標を返す"""
    html_text = files.read_text(encoding="utf-8", errors="ignore")

    soup = BeautifulSoup(html_text, "html.parser")

    def is_japanese_type(word):
        if re.match(r"^[\u3040-\u309F]+$", word):
            return True  # "ひらがな"
        elif re.match(r"^[\u30A0-\u30FF]+$", word):
            return True  # "カタカナ"
        elif re.match(r"^[\u4E00-\u9FFF]+$", word):
            return True  # "漢字"
        else:
            return False  # "混合・その他"

    def split_location_names(text):
        names = re.split(r'[＝ー・＿"\'＆／=\-・_"\'&/\s]+', text)
        return list(dict.fromkeys([name for name in names if name and len(name) > 1]))

    #  地名の抽出（タイトルや見出しから優先的に、記号で分割）
    spot_candidates = []
    if soup.title and soup.title.string:
        spot_candidates.extend(split_location_names(soup.title.string.strip()))
    # h1～h6タグから取得（記号で分割）
    for level in range(1, 7):
        for header in soup.find_all(f"h{level}"):
            spot_candidates.extend(split_location_names(header.get_text(strip=True)))

    # テキストから地名を抽出（Janomeを使用、日本語のみ）
    html_text_for_tokenize = re.sub(
        r"[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\s]", "", html_text
    )
    html_text_for_tokenize = html_text_for_tokenize.replace("　", "")
    t = Tokenizer()
    clean_text = re.sub(r"<[^>]+>", " ", html_text)
    for token in t.tokenize(clean_text):
        if (
            token.part_of_speech.split(",")[0] in ["名詞", "固有名詞"]
            and len(token.surface) >= 2
        ):
            if not is_japanese_type(token.surface):
                continue
            if token.surface not in spot_candidates:
                spot_candidates.append(token.surface)

    # 画像のalt属性から取得（記号で分割）
    for img in soup.find_all("img", alt=True):
        name = img["alt"].strip()
        if name:
            split_names = split_location_names(name)
            for split_name in split_names:
                if split_name not in spot_candidates:
                    spot_candidates.append(split_name)
    # 重複削除
    spot_candidates = list(dict.fromkeys(spot_candidates))

    geolocator = Nominatim(user_agent="shifvet_history_mapper_v1.1")

    find_location = None
    for spot in spot_candidates:
        spot_lower = spot.lower()
        # キャッシュ検索
        if spot_lower in location_cache:
            cached_name, cached_lat, cached_lon = location_cache[spot_lower]
            if cached_lat and cached_lon:
                # キャッシュから取得成功
                logger.info(
                    f"キャッシュから取得: {spot} -> ({cached_lat}, {cached_lon})"
                )
                find_location = (cached_name, cached_lat, cached_lon)
                break
        # ジオコーディング検索
        try:
            for attempt in range(geocode_retries):
                try:
                    logger.info(f"ジオコーディング検索: {spot}")
                    if geocode_debug:
                        logger.debug(
                            f"(デバッグモード) ジオコーディング検索スキップ: {spot}"
                        )
                    else:
                        location = geolocator.geocode(
                            spot, language="ja", timeout=geocode_timeout
                        )
                    time.sleep(geocode_wait)  # Nominatimの利用規約

                    if location:
                        # ジオコーディング検索成功
                        logger.info(
                            f"ジオコーディング成功: {spot} -> ({location.latitude}, {location.longitude})"
                        )
                        # キャッシュ保存
                        save_location_cache(spot, location.latitude, location.longitude)
                        location_cache[spot_lower] = (
                            spot,
                            location.latitude,
                            location.longitude,
                        )
                        # 結果設定
                        find_location = (spot, location.latitude, location.longitude)
                        break
                    # 見つからない（リトライしない）
                    logger.info(f"ジオコーディングなし: {spot} )")
                    save_location_cache(spot, "", "")
                    location_cache[spot_lower] = (spot, "", "")
                    break
                except (
                    GeocoderTimedOut,
                    GeocoderUnavailable,
                    GeocoderQuotaExceeded,
                ) as e:
                    if attempt < geocode_retries - 1:
                        # 指数バックオフ (Exponential Backoff) で待機時間を調整
                        # 試行回数が増えるごとに待機時間を倍にする (例: wait * 1, wait * 2, wait * 4...)
                        backoff_time = geocode_wait * (2**attempt)
                        # 待機時間が長くなりすぎないように上限を設定 (例: 60秒)
                        backoff_time = min(backoff_time, 60)
                        logger.warning(
                            f"ジオコーディング エラー ({spot}): {e} - {backoff_time}秒後にリトライ ({attempt+1}/{geocode_retries})"
                        )
                        time.sleep(backoff_time)
                    else:
                        raise  # 最終試行で失敗した場合、例外を再スロー（タイムアウトまたは利用不可）
            
            # 場所が見つかったら候補のループを抜ける
            if find_location:
                break
        except GeocoderTimedOut:
            logger.warning(f"ジオコーディング リトライタイムアウト: {spot}")
        except GeocoderUnavailable:
            logger.warning(f"ジオコーディング 利用不可応答: {spot}")
        except GeocoderQuotaExceeded:
            logger.warning(f"ジオコーディング API制限超過: {spot}")
        except Exception as e:
            logger.error(f"ジオコーディング 通信エラー ({spot}): {e}")
            if find_location:
                break
    if not find_location:
        return files  # 見つからなかった場合は元のHTMLを返す

    # 既存の 位置 タグを削除
    soup_final = BeautifulSoup(html_text, "html.parser")
    for georss in soup_final.find_all(["latitude", "longitude", "location_name"]):
        georss.decompose()
    html_text = str(soup_final)

    # HTMLに 位置 タグで位置情報を追加
    # <time> タグの次に挿入される
    # <georss> タグを作成（name, point 両方を含む）
    georss_tag = f"<location_name>{find_location[0]}</location_name><latitude>{find_location[1]}</latitude><longitude>{find_location[2]}</longitude>\n"

    # <time> タグを探して、その次の行に挿入
    if re.search(r"</time>", html_text, re.IGNORECASE):
        # </time> の直後に挿入
        html_text = re.sub(
            r"(</time>)", r"\1\n" + georss_tag, html_text, count=1, flags=re.IGNORECASE
        )
    else:
        # <time> がない場合は <title> の後
        if re.search(r"</title>", html_text, re.IGNORECASE):
            html_text = re.sub(
                r"(</title>)",
                r"\1\n" + georss_tag,
                html_text,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            logger.warning(
                f"  -> 警告: <title>, <time> タグが見つかりません。ファイル先頭に追加します。"
            )
            html_text = georss_tag + html_text

    with open(files, "w", encoding="utf-8") as f:
        f.write(html_text)
    return files


def run(result_queue):
    """
    HTMLファイルに地点を追加する。
    """

    # ✅ 地点読み込み（戻り値チェック）
    if not load_cache_location():
        logger.warning("地点読み込みに失敗しました。地点注入をスキップします。")
        return False

    # フォルダがなければ作成。既にあってもエラーにしない。
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    logger.info(f"HTML地点追加処理を開始: {input_dir}")

    files_to_process = [
        p
        for p in Path(input_dir).rglob("*")
        if p.is_file() and p.suffix.lower() in (html_extensions)
    ]

    if not files_to_process:
        logger.warning("地点追加対象のHTMLファイルが見つかりません。")
        return False

    for src_path in files_to_process:
        files = SmartFile(src_path)
        files.status = "⏳"
        files.extensions = "html"
        files.disp_path = files.name
        result_queue.put(files)
        
    pbar = ProgressBar(len(files_to_process), prefix="Add Locations")
    # ディレクトリ内のアイテムを走査
    for src_path in files_to_process:
        files = SmartFile(src_path)
        files = find_location_in_html(files)
        files.status = "✔"
        files.extensions = "html"
        files.disp_path = files.name
        result_queue.put(files)
        pbar.update()
    logger.info(f"完了: HTML地点追加")
    return True


import queue

# --- メイン処理 ---
if __name__ == "__main__":

    result_queue = queue.Queue()
    try:
        run(result_queue)
    except KeyboardInterrupt:
        logger.info("処理が中断されました。")
    except Exception as e:
        logger.critical(f"予期せぬエラーが発生しました: {e}", exc_info=True)

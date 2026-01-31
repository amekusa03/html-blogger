# -*- coding: utf-8 -*-
import os
import time
import re
import logging
from logging.handlers import RotatingFileHandler
import xml.etree.ElementTree as ET
from pathlib import Path
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from janome.tokenizer import Tokenizer

from config import get_config
from utils import ProgressBar
import database

# logging設定
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('location_adder.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING)
logger.addHandler(stream_handler)

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
GEORSS_POINT_FILE = SCRIPT_DIR / get_config('ADD_GEORSS_POINT', 'georss_point_file', 'georss_point.xml')

def load_georss_points(xml_file):
    """georss_point.xmlから地域情報を読み込む"""
    geo_data = {}
    try:
        if not xml_file.exists():
            logger.warning(f"{xml_file} が見つかりません。")
            return geo_data
        
        tree = ET.parse(str(xml_file))
        root = tree.getroot()
        
        for location in root.findall('location'):
            name_elem = location.find('name')
            lat_elem = location.find('latitude')
            lon_elem = location.find('longitude')
            
            if name_elem is not None and name_elem.text is not None:
                name = name_elem.text.strip()
                latitude = lat_elem.text.strip() if lat_elem is not None and lat_elem.text is not None else ""
                longitude = lon_elem.text.strip() if lon_elem is not None and lon_elem.text is not None else ""
                if name:
                    geo_data[name.lower()] = (name, latitude, longitude)
    except Exception as e:
        logger.error(f"XML読み込みエラー: {e}", exc_info=True)
    return geo_data

def save_to_georss_cache(xml_file, location_name, latitude="", longitude=""):
    """georss_point.xmlにキャッシュを保存"""
    try:
        if not xml_file.exists():
            root = ET.Element('root')
            tree = ET.ElementTree(root)
        else:
            tree = ET.parse(str(xml_file))
            root = tree.getroot()
        
        for location in root.findall('location'):
            name_elem = location.find('name')
            if name_elem is not None and name_elem.text == location_name:
                lat_elem = location.find('latitude')
                lon_elem = location.find('longitude')
                if lat_elem is not None: lat_elem.text = str(latitude) if latitude else ""
                if lon_elem is not None: lon_elem.text = str(longitude) if longitude else ""
                indent_xml(root)
                tree.write(str(xml_file), encoding='utf-8', xml_declaration=True)
                return
        
        location_elem = ET.SubElement(root, 'location')
        ET.SubElement(location_elem, 'name').text = location_name
        ET.SubElement(location_elem, 'latitude').text = str(latitude) if latitude else ""
        ET.SubElement(location_elem, 'longitude').text = str(longitude) if longitude else ""
        indent_xml(root)
        tree.write(str(xml_file), encoding='utf-8', xml_declaration=True)
    except Exception as e:
        logger.error(f"XML保存エラー: {e}", exc_info=True)

def indent_xml(elem, level=0):
    """XMLツリーにインデントと改行を追加する"""
    i = "\n" + level*"    "
    if len(elem):
        if not elem.text or not elem.text.strip(): elem.text = i + "    "
        if not elem.tail or not elem.tail.strip(): elem.tail = i
        for elem in elem: indent_xml(elem, level+1)
        if not elem.tail or not elem.tail.strip(): elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()): elem.tail = i

def find_location_in_html(html_text, geo_data):
    """HTML内で地域名を検索し、座標を返す"""
    soup = BeautifulSoup(html_text, 'html.parser')
    
    def split_location_names(text):
        names = re.split(r'[＝ー・＿"\'＆／=\-・_"\'&/\s]+', text)
        return list(dict.fromkeys([name for name in names if name and len(name) > 1]))

    spot_candidates = []
    if soup.title and soup.title.string:
        spot_candidates.extend(split_location_names(soup.title.string.strip()))
    for level in range(1, 7):
        for header in soup.find_all(f'h{level}'):
            spot_candidates.extend(split_location_names(header.get_text(strip=True)))

    t = Tokenizer()
    clean_text = re.sub(r'<[^>]+>', ' ', html_text)
    for token in t.tokenize(clean_text):
        if token.part_of_speech.split(',')[0] in ['名詞', '固有名詞'] and len(token.surface) >= 2:
            spot_candidates.append(token.surface)

    spot_candidates = list(dict.fromkeys(spot_candidates))

    geolocator = Nominatim(user_agent="shifvet_history_mapper_v1.1")

    for spot in spot_candidates:
        spot_lower = spot.lower()
        if spot_lower in geo_data:
            cached_name, cached_lat, cached_lon = geo_data[spot_lower]
            if cached_lat and cached_lon:
                return (cached_name, cached_lat, cached_lon)
            continue

        try:
            # リトライ処理を追加
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"ジオコーディング検索: {spot}")
                    location = geolocator.geocode(spot, language='ja', timeout=10)
                    time.sleep(1.1) # Nominatimの利用規約
                    
                    if location:
                        save_to_georss_cache(GEORSS_POINT_FILE, spot, location.latitude, location.longitude)
                        geo_data[spot_lower] = (spot, location.latitude, location.longitude)
                        return (spot, location.latitude, location.longitude)
                    else:
                        # 見つからない場合はリトライせず次へ
                        save_to_georss_cache(GEORSS_POINT_FILE, spot, "", "")
                        geo_data[spot_lower] = (spot, "", "")
                        break
                except (GeocoderTimedOut, GeocoderUnavailable) as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"ジオコーディング一時エラー ({spot}): {e} - リトライします ({attempt+1}/{max_retries})")
                        time.sleep(2)
                    else:
                        raise # 最終試行で失敗したら外側のexceptへ
        except (GeocoderTimedOut, GeocoderUnavailable):
            logger.warning(f"タイムアウト/接続不可によりスキップ: {spot}")
            save_to_georss_cache(GEORSS_POINT_FILE, spot, "", "")
            geo_data[spot_lower] = (spot, "", "")
        except Exception as e:
            logger.error(f"ジオコーディングエラー ({spot}): {e}")

    return None

def add_georss_tag_to_html(html_text, location_name, latitude, longitude):
    """HTMLに <georss> タグで位置情報を追加"""
    georss_tag = f'<georss><name>{location_name}</name><point>{latitude} {longitude}</point></georss>'
    
    # 既存のgeorssタグがあれば削除
    html_text = re.sub(r'<georss>.*?</georss>', '', html_text, flags=re.DOTALL | re.IGNORECASE)

    if re.search(r'</time>', html_text, re.IGNORECASE):
        return re.sub(r'(</time>)', r'\1\n' + georss_tag, html_text, count=1, flags=re.IGNORECASE)
    elif re.search(r'</title>', html_text, re.IGNORECASE):
        return re.sub(r'(</title>)', r'\1\n' + georss_tag, html_text, count=1, flags=re.IGNORECASE)
    else:
        logger.warning("警告: <title>, <time> タグが見つかりません。ファイル先頭に追加します。")
        return georss_tag + '\n' + html_text

def run_location_addition_pipeline():
    """DBから'keywords_added'ステータスの記事を取得し、位置情報を追加する"""
    logger.info("--- 位置情報追加パイプライン開始 ---")

    geo_data = load_georss_points(GEORSS_POINT_FILE)
    
    articles_to_process = database.get_articles_by_status('keywords_added')
    
    if not articles_to_process:
        logger.info("処理対象の記事はありません。")
        return 0, 0

    logger.info(f"{len(articles_to_process)} 件の記事に位置情報を追加します。")
    success_count, error_count = 0, 0
    pbar = ProgressBar(len(articles_to_process), prefix='GeoRSS')

    for article_data in articles_to_process:
        article_id = article_data['id']
        html_content = article_data['content']
        source_path = Path(article_data['source_path'])

        try:
            location = find_location_in_html(html_content, geo_data)
            
            if location:
                original_name, latitude, longitude = location
                updated_content = add_georss_tag_to_html(html_content, original_name, latitude, longitude)
                database.update_content(article_id, updated_content)
                logger.info(f"成功: {source_path.name} に位置情報 '{original_name}' を追加しました。")
            
            database.update_status(article_id, 'location_added')
            success_count += 1

        except Exception as e:
            error_msg = f"位置情報追加処理失敗: {e}"
            logger.error(f"失敗: {source_path.name} - {error_msg}", exc_info=True)
            database.update_status(article_id, 'error', error_message=error_msg)
            error_count += 1
        finally:
            pbar.update()

    logger.info("--- 位置情報追加パイプライン完了 ---")
    logger.info(f"成功: {success_count}件, 失敗: {error_count}件")
    return success_count, error_count

if __name__ == '__main__':
    try:
        run_location_addition_pipeline()
    except Exception as e:
        logger.critical(f"予期せぬエラーが発生しました: {e}", exc_info=True)
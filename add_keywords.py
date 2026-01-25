# -*- coding: utf-8 -*-
import os
import re
import xml.etree.ElementTree as ET
import shutil
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from config import get_config

def load_keywords(xml_path):
    """XMLからキーワードを読み込む。返却値: (mast_keywords, hit_keywords, success_flag)"""
    try:
        if not os.path.exists(xml_path):
            print(f"エラー: {xml_path} が見つかりません。")
            return [], [], False
        
        tree = ET.parse(xml_path)
        root = tree.getroot()
        mast_keywords = [node.text for node in root.find('Mastkeywords').findall('word') if node.text]
        hit_keywords = [node.text for node in root.find('Hitkeywords').findall('word') if node.text]
        return mast_keywords, hit_keywords, True
    except Exception as e:
        print(f"XML読み込みエラー: {e}")
        return [], [], False

def load_georss_cache(georss_file):
    """
    georss_point.xmlからキャッシュされた位置情報を読み込む
    返却値: {地域名_lower: (地域名, 緯度, 経度), ...}
    """
    geo_cache = {}
    try:
        if not os.path.exists(georss_file):
            return geo_cache
        
        tree = ET.parse(georss_file)
        root = tree.getroot()
        
        for location in root.findall('location'):
            name_elem = location.find('name')
            lat_elem = location.find('latitude')
            lon_elem = location.find('longitude')
            
            if name_elem is not None and lat_elem is not None and lon_elem is not None:
                name = name_elem.text
                if name:
                    geo_cache[name.lower()] = (name, lat_elem.text, lon_elem.text)
    except Exception as e:
        print(f"警告: georss_point.xml 読み込みエラー: {e}")
    
    return geo_cache

def save_to_georss_cache(georss_file, location_name, latitude, longitude):
    """
    位置情報をgeorss_point.xmlに追加（キャッシング）
    """
    try:
        if os.path.exists(georss_file):
            tree = ET.parse(georss_file)
            root = tree.getroot()
        else:
            root = ET.Element('georss_points')
            tree = ET.ElementTree(root)
        
        # 既存の同じ名前のロケーションを削除
        for location in root.findall('location'):
            name_elem = location.find('name')
            if name_elem is not None and name_elem.text and name_elem.text.lower() == location_name.lower():
                root.remove(location)
        
        # 新しいロケーション要素を追加
        location = ET.SubElement(root, 'location')
        name_elem = ET.SubElement(location, 'name')
        name_elem.text = location_name
        lat_elem = ET.SubElement(location, 'latitude')
        lat_elem.text = str(latitude)
        lon_elem = ET.SubElement(location, 'longitude')
        lon_elem.text = str(longitude)
        
        tree.write(georss_file, encoding='utf-8', xml_declaration=True)
    except Exception as e:
        print(f"警告: georss_point.xmlへの保存に失敗: {e}")

def extract_location_names_from_html(html_content):
    """
    HTMLのタイトルと見出しから、記号（=、ー、・、＿、"、'、＆、／）で
    区切られた地域名候補を抽出
    返却値: [地域名, ...]
    """
    candidates = []
    
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # タイトルから抽出
        if soup.title and soup.title.string:
            title_text = soup.title.string.strip()
            candidates.extend(_split_location_names(title_text))
        
        # h1～h9タグから抽出
        for level in range(1, 10):
            for header in soup.find_all(f'h{level}'):
                header_text = header.get_text(strip=True)
                candidates.extend(_split_location_names(header_text))
    except Exception as e:
        print(f"警告: HTMLパース時のエラー: {e}")
    
    # 重複排除、空文字列削除
    candidates = list(dict.fromkeys([c for c in candidates if c.strip()]))
    return candidates

def _split_location_names(text):
    """
    テキストを記号（=、ー、・、＿、"、'、＆、／）で分割し、
    地域名候補を抽出
    """
    if not text:
        return []
    
    # 記号で分割
    parts = re.split(r'[=ー・＿"\'＆／]', text)
    
    # 各パートを正規化、空文字列を除外
    result = []
    for part in parts:
        normalized = unicodedata.normalize('NFKC', part.strip())
        if normalized and len(normalized) > 0:
            result.append(normalized)
    
    return result

def search_location_coordinates(location_name, geo_cache, georss_file):
    """
    地域名をNominatim (OpenStreetMap) で検索して座標を取得
    キャッシュを優先利用、キャッシュにない場合のみNominatimをクエリ
    返却値: (緯度, 経度) または None
    """
    location_name_lower = location_name.lower()
    
    # キャッシュチェック
    if location_name_lower in geo_cache:
        _, latitude, longitude = geo_cache[location_name_lower]
        print(f"  -> キャッシュ: {location_name} -> ({latitude}, {longitude})")
        return (float(latitude), float(longitude))
    
    # Nominatimで検索
    try:
        geolocator = Nominatim(user_agent="htmltobrogger_v1")
        location = geolocator.geocode(location_name)
        
        if location:
            print(f"  -> 検索: {location_name} -> ({location.latitude}, {location.longitude})")
            # キャッシュに保存
            save_to_georss_cache(georss_file, location_name, location.latitude, location.longitude)
            return (location.latitude, location.longitude)
        else:
            print(f"  -> 検索失敗: {location_name} の座標が見つかりません")
            return None
    except GeocoderTimedOut:
        print(f"  -> タイムアウト: {location_name}")
        return None
    except Exception as e:
        print(f"  -> エラー: {location_name} の検索に失敗: {e}")
        return None
    finally:
        # Nominatimのレート制限に従う（1.1秒待機）
        time.sleep(1.1)

def process_html(file_path, mast_keywords, hit_keywords, georss_file=None, geo_cache=None):
    """HTMLファイルにキーワードメタタグを注入。失敗時はバックアップから復元。"""
    
    # ✅ バックアップ作成
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        shutil.copy2(file_path, backup_path)
    except Exception as e:
        print(f"警告: バックアップ作成失敗 {file_path}: {e}")
        backup_path = None
    
    try:
        # ファイル読み込み
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 1. 改行・タブ削除（安定性向上のため）
        html_content = re.sub(r'[\r\n\t]+', '', html_content, flags=re.IGNORECASE)
        
        # B. キーワード作成：地域名抽出とNominatim検索
        if georss_file and geo_cache is not None:
            print(f"  -> 地域名抽出中...")
            location_names = extract_location_names_from_html(html_content)
            for location_name in location_names:
                coords = search_location_coordinates(location_name, geo_cache, georss_file)
                if coords:
                    # 座標が見つかった場合、後続のステージで使用するため記録
                    # （ここではgeotagのmeta注入はしない、add_georss_point.pyで処理）
                    pass
        
        # 2. 既存の全 keywords metaタグを検索してキーワードを回収
        # 様々な書き方（順序入れ替え、/の有無）に対応する正規表現
        pattern = re.compile(r'<meta\s+[^>]*name=["\']keywords["\'][^>]*>', re.IGNORECASE)
        
        current_keywords = []
        
        # 既存タグから content の中身を抽出
        for match in pattern.findall(html_content):
            content_match = re.search(r'content=["\']([^"\']*)["\']', match, re.IGNORECASE)
            if content_match:
                words = [k.strip() for k in content_match.group(1).replace('，', ',').split(',') if k.strip()]
                current_keywords.extend(words)
        
        # 既存のキーワードタグを削除
        html_content = pattern.sub('', html_content)

        # 3. 新しいキーワードリストの作成（重複排除）
        new_keywords_list = []
        # 既存分
        for kw in current_keywords:
            if kw not in new_keywords_list:
                new_keywords_list.append(kw)
        # 必須分
        for kw in mast_keywords:
            if kw not in new_keywords_list:
                new_keywords_list.append(kw)
        # 本文ヒット分
        clean_text = re.sub(r'<[^>]*?>', '', html_content)
        for h_kw in hit_keywords:
            if h_kw in clean_text and h_kw not in new_keywords_list:
                new_keywords_list.append(h_kw)

        # 4. 指定された順序でタグを作成（ここで初めて使用）
        new_tag = f'<meta name="keywords" content="{",".join(new_keywords_list)}">'

        # 5. 挿入処理
        if re.search(r'<head>', html_content, re.IGNORECASE):
            # <head>の直後に挿入
            html_content = re.sub(r'(<head.*?>)', r'\1\n' + new_tag, html_content, flags=re.IGNORECASE)
        else:
            # headがない場合は先頭に挿入
            html_content = new_tag + '\n' + html_content

        # 6. ファイル保存
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"完了: {file_path}")
        return True
        
    except Exception as e:
        print(f"エラー: {file_path} の処理に失敗しました: {e}")
        # ✅ バックアップがあれば復元
        if backup_path and os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, file_path)
                print(f"バックアップから復元しました: {file_path}")
            except Exception as restore_error:
                print(f"復元にも失敗しました！: {restore_error}")
        return False

def main():
    script_dir = Path(__file__).parent.resolve()
    xml_file = script_dir / get_config('ADD_KEYWORDS', 'XML_FILE')
    original_dir = script_dir / get_config('ADD_KEYWORDS', 'ORIGINAL_DIR')
    add_keywords_dir = script_dir / get_config('ADD_KEYWORDS', 'ADD_KEYWORDS_DIR')
    georss_file = script_dir / get_config('ADD_GEORSS_POINT', 'GEORSS_POINT_FILE')

    # ✅ 出力ディレクトリをリセット
    shutil.rmtree(str(add_keywords_dir), ignore_errors=True)
    try:
        shutil.copytree(str(original_dir), str(add_keywords_dir))
    except Exception as e:
        print(f"エラー: ディレクトリコピーに失敗しました: {e}")
        return
    
    # ✅ ファイル存在確認
    if not xml_file.exists():
        print(f"エラー: {xml_file} が見つかりません。")
        return
    if not add_keywords_dir.exists():
        print(f"エラー: {add_keywords_dir} ディレクトリが見つかりません。")
        return

    # ✅ キーワード読み込み（戻り値チェック）
    mast_kws, hit_kws, success = load_keywords(str(xml_file))
    
    if not success:
        print("警告: キーワード読み込みに失敗しました。キーワード注入をスキップします。")
        return
    
    if not mast_kws and not hit_kws:
        print("警告: キーワードが見つかりません。")

    # ✅ B. キーワード作成用：georss_point.xmlをキャッシュとして読み込む
    geo_cache = load_georss_cache(str(georss_file))
    print(f"georss キャッシュ読み込み: {len(geo_cache)}件")

    # ✅ ファイル処理（戻り値チェック）
    processed_count = 0
    failed_count = 0
    
    for entry in add_keywords_dir.iterdir():
        if entry.is_dir():
            for file in entry.iterdir():
                if file.is_file() and file.suffix.lower() in ('.html', '.htm'):
                    success = process_html(str(file), mast_kws, hit_kws, str(georss_file), geo_cache)
                    if success:
                        processed_count += 1
                    else:
                        failed_count += 1
    
    print("-" * 30)
    print(f"【処理完了】")
    print(f"成功: {processed_count} ファイル")
    if failed_count > 0:
        print(f"失敗: {failed_count} ファイル")

if __name__ == "__main__":
    main()

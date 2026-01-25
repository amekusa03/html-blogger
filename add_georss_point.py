# -*- coding: utf-8 -*-
import os
import time
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from janome.tokenizer import Tokenizer
from config import get_config

"""
位置情報追加スクリプト
georss_point.xmlから地域名、緯度、経度を読み込み、
HTML内で地域名が見つかった場合に<georss:point>タグを注入する。
複数見つかった場合は最後に見つかったものを採用。
<head>タグ内に注入される。
"""

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
GEORSS_POINT_FILE = SCRIPT_DIR / get_config('ADD_GEORSS_POINT', 'GEORSS_POINT_FILE')
INPUT_DIR = SCRIPT_DIR / get_config('ADD_GEORSS_POINT', 'INPUT_DIR')
OUTPUT_DIR = SCRIPT_DIR / get_config('ADD_GEORSS_POINT', 'OUTPUT_DIR')

def load_georss_points(xml_file):
    """
    georss_point.xmlから地域情報を読み込む
    戻り値: {地域名: (元の地域名, 緯度, 経度), ...}の辞書
    緯度経度が空文字列の場合は見つからなかったことを意味する
    """
    geo_data = {}
    try:
        if not xml_file.exists():
            print(f"警告: {xml_file} が見つかりません。")
            return geo_data
        
        tree = ET.parse(str(xml_file))
        root = tree.getroot()
        
        for location in root.findall('location'):
            name_elem = location.find('name')
            lat_elem = location.find('latitude')
            lon_elem = location.find('longitude')
            
            if name_elem is not None:
                name = name_elem.text
                latitude = lat_elem.text if lat_elem is not None else ""
                longitude = lon_elem.text if lon_elem is not None else ""
                
                if name:
                    # 大文字小文字を区別しないために小文字に統一してキーにする
                    geo_data[name.lower()] = (name, latitude, longitude)
        
        print(f"位置情報を読み込みました: {len(geo_data)}件")
    except Exception as e:
        print(f"XML読み込みエラー: {e}")
    
    return geo_data

def save_to_georss_cache(xml_file, location_name, latitude="", longitude=""):
    """
    georss_point.xmlにキャッシュを保存
    見つからなかった場合は空文字列で保存（重複クエリ防止）
    """
    try:
        # XMLファイルが存在しない場合は新規作成
        if not xml_file.exists():
            root = ET.Element('locations')
            tree = ET.ElementTree(root)
        else:
            tree = ET.parse(str(xml_file))
            root = tree.getroot()
        
        # 既存エントリをチェック（重複回避）
        for location in root.findall('location'):
            name_elem = location.find('name')
            if name_elem is not None and name_elem.text == location_name:
                # 既に存在する場合は上書き
                lat_elem = location.find('latitude')
                lon_elem = location.find('longitude')
                if lat_elem is not None:
                    lat_elem.text = str(latitude)
                if lon_elem is not None:
                    lon_elem.text = str(longitude)
                tree.write(str(xml_file), encoding='utf-8', xml_declaration=True)
                return
        
        # 新規エントリを追加
        location_elem = ET.SubElement(root, 'location')
        name_elem = ET.SubElement(location_elem, 'name')
        name_elem.text = location_name
        lat_elem = ET.SubElement(location_elem, 'latitude')
        lat_elem.text = str(latitude)
        lon_elem = ET.SubElement(location_elem, 'longitude')
        lon_elem.text = str(longitude)
        
        tree.write(str(xml_file), encoding='utf-8', xml_declaration=True)
        print(f"  -> georss_point.xmlに保存しました: {location_name}")
    except Exception as e:
        print(f"XML保存エラー: {e}")

def find_location_in_html(html_text, geo_data):
    """
    HTML内で地域名を検索する（大文字小文字を区別しない、完全一致）
    複数見つかった場合は最後に見つかったものを返す
    戻り値: (地域名, 緯度, 経度) または None
    """
    # 改行・タブを削除
    html_text_normalized = re.sub(r'[\r\n\t]+', '', html_text)
    
    found_location = None
    soup = BeautifulSoup(html_text, 'html.parser')
    
    def is_japanese_type(word):
        if re.match(r'^[\u3040-\u309F]+$', word):
            return True #"ひらがな"
        elif re.match(r'^[\u30A0-\u30FF]+$', word):
            return True #"カタカナ"
        elif re.match(r'^[\u4E00-\u9FFF]+$', word):
            return True #"漢字"
        else:
            return False #"混合・その他"
    
    def split_location_names(text):
        """記号で分割して地域名を抽出（仕様B準拠）"""
        # 記号：＝、ー、・、＿、"、'、＆、／
        names = re.split(r'[＝ー・＿"\'＆／=\-・_"\'&/\s]+', text)
        # 空文字列と1文字以下を除外、重複削除
        result = []
        for name in names:
            if name and len(name) > 1:
                result.append(name)
        return list(dict.fromkeys(result))
    
    # 2. 地名の抽出（タイトルや見出しから優先的に、記号で分割）
    spot_candidates = []
    
    # タイトルから取得（記号で分割）
    if soup.title and soup.title.string:
        name = soup.title.string.strip()
        if name:
            split_names = split_location_names(name)
            for split_name in split_names:
                if split_name not in spot_candidates:
                    spot_candidates.append(split_name)
                    print(f"タイトル分割: '{name}' -> '{split_name}'")
            
    # h1～h6タグから取得（記号で分割）
    for level in range(1, 7):
        for header in soup.find_all(f'h{level}'):
            name = header.get_text(strip=True)
            if name:
                split_names = split_location_names(name)
                for split_name in split_names:
                    if split_name not in spot_candidates:
                        spot_candidates.append(split_name)
                        print(f"見出し{level}分割: '{name}' -> '{split_name}'")
                       
    # 1. テキストから地名を抽出（Janomeを使用、日本語のみ）
    html_text_for_tokenize = re.sub(r'[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\s]', '', html_text_normalized)
    html_text_for_tokenize = html_text_for_tokenize.replace('　', '')
    
    t = Tokenizer()
    for token in t.tokenize(html_text_for_tokenize):
        pos = token.part_of_speech.split(',')[0]
        # 長さが2文字以上の名詞のみ採用
        if pos in ['名詞', '固有名詞'] and len(token.surface) >= 2:
            if not is_japanese_type(token.surface):
                continue
            if token.surface not in spot_candidates:
                spot_candidates.append(token.surface)
                print(f"Janome抽出: {token.surface} ({pos})")
            
    # 画像のalt属性から取得（記号で分割）
    for img in soup.find_all('img', alt=True):
        name = img['alt'].strip()
        if name:
            split_names = split_location_names(name)
            for split_name in split_names:
                if split_name not in spot_candidates:
                    spot_candidates.append(split_name)
                    print(f"alt属性分割: '{name}' -> '{split_name}'")
            
    # 特定のフォントサイズ指定があるテキストを取得
    for font in soup.find_all('font', size="-1"):
        name = font.get_text(strip=True)
        if name and name not in spot_candidates:
            spot_candidates.append(name)
            print(f"font候補: {name}")

    spot_candidates = list(dict.fromkeys(spot_candidates))  # 重複削除
    print(f"検索候補総数: {len(spot_candidates)}個 -> {spot_candidates}")
    
    # 3. ジオコーディング（地名を座標に変換）
    # user_agentは独自のものを設定
    geolocator = Nominatim(user_agent="shifvet_history_mapper_v1")
    results = []

    for spot in spot_candidates:
        spot_lower = spot.lower()
        
        # まずXMLキャッシュをチェック
        if spot_lower in geo_data:
            cached_name, cached_lat, cached_lon = geo_data[spot_lower]
            if cached_lat and cached_lon:  # 緯度経度がある場合
                found_location = (cached_name, cached_lat, cached_lon)
                print(f"  -> キャッシュから取得: {cached_name} -> ({cached_lat}, {cached_lon})")
                break
            else:
                # 過去に検索して見つからなかったことが記録されている
                print(f"  -> キャッシュ済み（見つかりませんでした）: {spot}")
                continue
        
        # XMLに未登録の場合のみNominatimで検索
        try:
            # 地名をそのまま検索（日本国内外を問わず）
            search_query = spot
            print(f"  Nominatim検索: '{search_query}'")
            
            location = geolocator.geocode(search_query, language='ja')
            if location:
                # 検索結果のアドレスを確認
                address_lower = location.address.lower()
                latitude = location.latitude
                longitude = location.longitude
                print(f"    検索結果: {location.address}")
                print(f"    座標: ({latitude}, {longitude})")
                
                # 検索語が結果のアドレスに含まれているか確認
                if spot_lower not in address_lower:
                    print(f"  -> ×検証失敗: '{spot}' が結果アドレスに含まれていません")
                    save_to_georss_cache(GEORSS_POINT_FILE, spot, "", "")
                else:
                    results.append({
                        "spot": spot,
                        "address": location.address,
                        "latitude": latitude,
                        "longitude": longitude
                    })
                    found_location = (spot, latitude, longitude)
                    print(f"  -> ✓見つかりました: {spot} -> ({latitude}, {longitude})")
                    # XMLに保存
                    save_to_georss_cache(GEORSS_POINT_FILE, spot, latitude, longitude)
                    break  # 最初に見つけたものを採用
            else:
                print(f"  -> ×見つかりませんでした: {spot}")
                # 見つからなかった場合も空文字列でXMLに保存（重複クエリ防止）
                save_to_georss_cache(GEORSS_POINT_FILE, spot, "", "")
            
            # APIへの負荷軽減のため1.1秒待機（Nominatimの利用規約）
            time.sleep(1.1)
            
        except GeocoderTimedOut:
            print(f"タイムアウトしました: {spot}")
            # タイムアウトした場合も空文字列で保存
            save_to_georss_cache(GEORSS_POINT_FILE, spot, "", "")
    
    return found_location

def add_georss_tag_to_html(html_text, location_name, latitude, longitude):
    """
    HTMLの<head>タグ内に<georss:point>と<georss:name>タグを注入
    """
    # 改行・タブを削除（安定性のため）
    html_text = re.sub(r'[\r\n\t]+', '', html_text)
    
    # 地名タグと座標タグを作成
    georss_name_tag = f'<georss:name>{location_name}</georss:name>'
    georss_point_tag = f'<georss:point>{latitude} {longitude}</georss:point>'
    combined_tag = f'{georss_name_tag}{georss_point_tag}'
    
    # </head>タグの前に挿入
    if '</head>' in html_text or '</HEAD>' in html_text:
        # 大文字小文字を区別して置換
        if '</head>' in html_text:
            html_text = html_text.replace('</head>', f'{combined_tag}</head>')
        else:
            html_text = html_text.replace('</HEAD>', f'{combined_tag}</HEAD>')
    else:
        # </head>タグが見つからない場合は警告を出して、タグの末尾に追加
        print(f"  -> 警告: </head>タグが見つかりません。最後に追加します。")
        html_text += combined_tag
    
    return html_text

def process_html_files():
    """
    メイン処理：INPUT_DIR内のすべてのHTMLファイルを処理
    """
    # 出力フォルダを作成
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"作成しました: {OUTPUT_DIR}")
    
    # 位置情報を読み込む
    geo_data = load_georss_points(GEORSS_POINT_FILE)
    
    if not geo_data:
        print("警告: 位置情報が見つかりません。処理をスキップします。")
        return
    
    print("位置情報を追加処理を開始します...")
    
    processed_count = 0
    found_location_count = 0
    
    # 再帰的にHTMLファイルを処理
    for root, dirs, files in os.walk(str(INPUT_DIR)):
        rel_path = os.path.relpath(root, str(INPUT_DIR))
        dest_dir = OUTPUT_DIR / rel_path if rel_path != '.' else OUTPUT_DIR
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        for filename in files:
            src_path = Path(root) / filename
            
            if filename.lower().endswith(('.htm', '.html')):
                processed_count += 1
                
                # ファイルを読み込む（文字コード自動判定）
                content = None
                for encoding in ['utf-8', 'cp932', 'shift_jis']:
                    try:
                        with open(src_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        break
                    except:
                        continue
                
                if content:
                    print(f"[{processed_count}] 処理中: {rel_path}/{filename}")
                    
                    # まずXMLキャッシュから直接マッチする位置情報を探す
                    soup = BeautifulSoup(content, 'html.parser')
                    location = None
                    
                    # タイトルとh1-h6から地域名を抽出してXMLと照合
                    search_texts = []
                    if soup.title and soup.title.string:
                        search_texts.append(soup.title.string.strip())
                    for level in range(1, 7):
                        for header in soup.find_all(f'h{level}'):
                            search_texts.append(header.get_text(strip=True))
                    
                    # XMLキャッシュから検索
                    for text in search_texts:
                        text_lower = text.lower()
                        if text_lower in geo_data:
                            cached_name, cached_lat, cached_lon = geo_data[text_lower]
                            if cached_lat and cached_lon:
                                location = (cached_name, cached_lat, cached_lon)
                                print(f"  -> XMLキャッシュから位置情報を取得: {cached_name}")
                                break
                    
                    # XMLになければNominatimで検索
                    if not location:
                        location = find_location_in_html(content, geo_data)
                    
                    if location:
                        # 位置情報タグを追加
                        original_name, latitude, longitude = location
                        content = add_georss_tag_to_html(content, original_name, latitude, longitude)
                        found_location_count += 1
                        print(f"  -> 位置情報を追加しました: {original_name} ({latitude}, {longitude})")
                    else:
                        print(f"  -> 地域情報が見つかりません")
                    
                    # ファイルを出力
                    dest_path = dest_dir / filename
                    with open(str(dest_path), 'w', encoding='utf-8') as f:
                        f.write(content)
                else:
                    print(f"[{processed_count}] ×失敗(文字コード不明): {rel_path}/{filename}")
            else:
                # HTMLファイル以外はそのままスキップ
                # （入力フォルダと出力フォルダが同じため、コピー不要）
                pass
    
    print("-" * 30)
    print(f"【処理完了】")
    print(f"処理したHTML: {processed_count} 本")
    print(f"位置情報を追加したHTML: {found_location_count} 本")

if __name__ == '__main__':
    process_html_files()

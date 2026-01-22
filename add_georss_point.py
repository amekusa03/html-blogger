# -*- coding: utf-8 -*-
"""
位置情報追加スクリプト
georss_point.xmlから地域名、緯度、経度を読み込み、
HTML内で地域名が見つかった場合に<georss:point>タグを注入する。
複数見つかった場合は最後に見つかったものを採用。
<head>タグ内に注入される。
"""
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from config import get_config

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
GEORSS_POINT_FILE = SCRIPT_DIR / get_config('ADD_GEORSS_POINT', 'GEORSS_POINT_FILE')
INPUT_DIR = SCRIPT_DIR / get_config('ADD_GEORSS_POINT', 'INPUT_DIR')
OUTPUT_DIR = SCRIPT_DIR / get_config('ADD_GEORSS_POINT', 'OUTPUT_DIR')

def load_georss_points(xml_file):
    """
    georss_point.xmlから地域情報を読み込む
    戻り値: {地域名: (緯度, 経度), ...}の辞書
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
            
            if name_elem is not None and lat_elem is not None and lon_elem is not None:
                name = name_elem.text
                latitude = lat_elem.text
                longitude = lon_elem.text
                
                if name and latitude and longitude:
                    # 大文字小文字を区別しないために小文字に統一して保存
                    geo_data[name.lower()] = (name, latitude, longitude)
        
        print(f"位置情報を読み込みました: {len(geo_data)}件")
    except Exception as e:
        print(f"XML読み込みエラー: {e}")
    
    return geo_data

def find_location_in_html(html_text, geo_data):
    """
    HTML内で地域名を検索する（大文字小文字を区別しない、完全一致）
    複数見つかった場合は最後に見つかったものを返す
    戻り値: (地域名, 緯度, 経度) または None
    """
    # 改行・タブを削除
    html_text_normalized = re.sub(r'[\r\n\t]+', '', html_text)
    
    found_location = None
    
    # 各地域名をHTMLから検索
    for geo_name_lower, (original_name, lat, lon) in geo_data.items():
        # 完全一致で検索（大文字小文字を区別しない）
        # 単語境界を考慮した正規表現
        pattern = r'\b' + re.escape(geo_name_lower) + r'\b'
        matches = list(re.finditer(pattern, html_text_normalized, re.IGNORECASE))
        
        if matches:
            # 最後に見つかったものを採用
            found_location = (original_name, lat, lon)
            print(f"  -> 地域名を見つけました: {original_name} ({lat}, {lon})")
    
    return found_location

def add_georss_tag_to_html(html_text, latitude, longitude):
    """
    HTMLの<head>タグ内に<georss:point>タグを注入
    """
    # 改行・タブを削除（安定性のため）
    html_text = re.sub(r'[\r\n\t]+', '', html_text)
    
    georss_tag = f'<georss:point>{latitude} {longitude}</georss:point>'
    
    # </head>タグの前に挿入
    if '</head>' in html_text or '</HEAD>' in html_text:
        # 大文字小文字を区別して置換
        if '</head>' in html_text:
            html_text = html_text.replace('</head>', f'{georss_tag}</head>')
        else:
            html_text = html_text.replace('</HEAD>', f'{georss_tag}</HEAD>')
    else:
        # </head>タグが見つからない場合は警告を出して、タグの末尾に追加
        print(f"  -> 警告: </head>タグが見つかりません。最後に追加します。")
        html_text += georss_tag
    
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
                    
                    # HTML内で地域名を探す
                    location = find_location_in_html(content, geo_data)
                    
                    if location:
                        # 位置情報タグを追加
                        original_name, latitude, longitude = location
                        content = add_georss_tag_to_html(content, latitude, longitude)
                        found_location_count += 1
                        print(f"  -> 位置情報を追加しました")
                    else:
                        print(f"  -> 地域情報が見つかりません")
                    
                    # ファイルを出力
                    dest_path = dest_dir / filename
                    with open(str(dest_path), 'w', encoding='utf-8') as f:
                        f.write(content)
                else:
                    print(f"[{processed_count}] ×失敗(文字コード不明): {rel_path}/{filename}")
            else:
                # HTMLファイル以外はそのままコピー
                dest_path = dest_dir / filename
                import shutil
                shutil.copy2(str(src_path), str(dest_path))
    
    print("-" * 30)
    print(f"【処理完了】")
    print(f"処理したHTML: {processed_count} 本")
    print(f"位置情報を追加したHTML: {found_location_count} 本")

if __name__ == '__main__':
    process_html_files()

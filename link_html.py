# -*- coding: utf-8 -*-
"""
link_html.py
uploader.pyのマッピング機能と同様にready_upload内のhtmlの画像パスを変更する
"""

import os
import re
from pathlib import Path
from bs4 import BeautifulSoup
from config import get_config

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
# ready_uploadフォルダのパス
READY_UPLOAD_DIR = SCRIPT_DIR / get_config('READY_UPLOAD', 'OUTPUT_DIR', './ready_upload').lstrip('./')
# メディアマネージャーファイル
MEDIA_MANAGER_FILE = SCRIPT_DIR / 'Blogger メディア マネージャー_ddd.html'

# 画像サイズマッピング
SIZE_MAP = {
    'landscape': [
        {'w': 640, 'h': 480},
        {'w': 400, 'h': 300},
        {'w': 320, 'h': 240},
        {'w': 200, 'h': 150}
    ],
    'portrait': [
        {'w': 480, 'h': 640},
        {'w': 300, 'h': 400},
        {'w': 240, 'h': 320},
        {'w': 150, 'h': 200}
    ]
}

def load_media_mapping():
    """メディアマネージャーファイルから画像URLをマッピング"""
    mapping = {}
    
    # media-man フォルダ内の Blogger メディア マネージャー_*.html を検索
    media_man_dir = SCRIPT_DIR / 'media-man'
    if not media_man_dir.exists():
        print(f"警告: media-man フォルダが見つかりません。")
        return mapping
    
    media_files = list(media_man_dir.glob('Blogger メディア マネージャー_*.html'))
    
    if len(media_files) == 0:
        print(f"警告: Blogger メディア マネージャー_*.html が見つかりません。")
        return mapping
    elif len(media_files) > 1:
        print(f"エラー: Blogger メディア マネージャー_*.html が複数あります。")
        print("以下のファイルのうち、正しいファイル1つだけを残してください：")
        for f in media_files:
            print(f"  - {f.name}")
        return None
    
    media_file = media_files[0]
    print(f"メディアマネージャーファイルを読み込んでいます: {media_file.name}")
    
    # ファイルをテキストとして読み込み、正規表現でURLを抽出
    with open(str(media_file), 'r', encoding='utf-8') as f:
        content = f.read()
        
        # googleusercontent.com を含むURLを正規表現で抽出
        # URLの末尾にファイル名が含まれているパターンを探す
        pattern = r'https?://[^\s"\'<>]+googleusercontent\.com/[^\s"\'<>]+/([^/\s"\'<>]+\.(?:jpg|jpeg|png|gif))'
        
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            url = match.group(0)
            filename = match.group(1)  # ファイル名部分
            # プロトコル部分を完全に削除（仕様通り）
            url_without_protocol = url.replace('https://', '', 1).replace('http://', '', 1)
            mapping[filename] = url_without_protocol
    
    print(f"画像マッピング: {len(mapping)} 個の画像URLを読み込みました。")
    if mapping:
        print("マッピング例:")
        for i, (filename, url) in enumerate(list(mapping.items())[:3]):
            print(f"  {filename} -> {url[:80]}...")
    return mapping

def resize_logic(w, h):
    """画像サイズを適切なサイズにリサイズ"""
    mode = 'landscape' if w >= h else 'portrait'
    targets = SIZE_MAP[mode]
    if w <= targets[-1]['w']: 
        return targets[-1]['w'], targets[-1]['h']
    for target in targets:
        if w >= target['w']: 
            return target['w'], target['h']
    return targets[-1]['w'], targets[-1]['h']

def process_html_file(html_path, media_map):
    """HTMLファイルの画像パスを変更"""
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # マッピング失敗したファイルを記録
    unmapped_files = []
    updated_count = 0
    
    # 画像処理
    for img in soup.find_all('img'):
        # 1. URL置換
        src_attr = img.get('src', '')
        old_filename = src_attr.split('/')[-1]
        
        if old_filename in media_map:
            img['src'] = media_map[old_filename]
            updated_count += 1
        else:
            # マッピングできないファイルを記録
            if old_filename:
                unmapped_files.append(old_filename)
        
        # 2. リサイズ
        try:
            w, h = int(img.get('width', 0)), int(img.get('height', 0))
            if w > 0 and h > 0:
                new_w, new_h = resize_logic(w, h)
                img['width'], img['height'] = str(new_w), str(new_h)
        except:
            pass
    
    # ファイルに書き戻す
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))
    
    return updated_count, unmapped_files

def link_html():
    """ready_upload内のすべてのHTMLファイルの画像リンクを更新"""
    
    if not READY_UPLOAD_DIR.exists():
        print(f"エラー: フォルダが存在しません: {READY_UPLOAD_DIR}")
        return
    
    # メディアマッピング読み込み
    media_map = load_media_mapping()
    if media_map is None:
        print("エラー: メディアマネージャーファイルが複数あるため処理を中断します。")
        return
    
    if not media_map:
        print("警告: 画像マッピングが空です。処理を続行しますが、画像URLは更新されません。")
    
    print(f"\nready_uploadフォルダのHTMLファイルを処理しています...")
    
    html_files = list(READY_UPLOAD_DIR.glob('*.html')) + list(READY_UPLOAD_DIR.glob('*.htm'))
    
    if not html_files:
        print(f"HTMLファイルが見つかりません: {READY_UPLOAD_DIR}")
        return
    
    total_updated = 0
    all_unmapped = []
    
    for html_file in html_files:
        updated_count, unmapped_files = process_html_file(html_file, media_map)
        total_updated += updated_count
        all_unmapped.extend(unmapped_files)
        print(f"  処理完了: {html_file.name} ({updated_count} 個の画像を更新)")
    
    print("-" * 30)
    print(f"完了しました。合計 {total_updated} 個の画像URLを更新しました。")
    
    # マッピング失敗した画像を一覧表示
    if all_unmapped:
        print(f"\n警告: 以下の {len(all_unmapped)} 個の画像ファイルが紐付けできませんでした:")
        for filename in set(all_unmapped):
            print(f"  - {filename}")
        print("\n対処方法:")
        print("  1. 操作５から やり直す")
        print("  2. アップロード後に手動で修正する")

if __name__ == '__main__':
    link_html()

# -*- coding: utf8 -*-
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from config import get_config

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
INPUT_DIR = SCRIPT_DIR / get_config('READY_UPLOAD', 'OUTPUT_DIR', './ready_upload').lstrip('./')
OUTPUT_DIR = SCRIPT_DIR / get_config('CONVERT_ATOM', 'OUTPUT_DIR', './ready_upload').lstrip('./')
OUTPUT_FILE = OUTPUT_DIR / 'feed.atom'
BLOG_TITLE = get_config('CONVERT_ATOM', 'BLOG_TITLE', 'My Blog')
BLOG_URL = get_config('CONVERT_ATOM', 'BLOG_URL', 'https://example.blogspot.com')

def extract_metadata(html_text, filepath=None):
    """HTML テキストからメタデータを抽出（キーワード、タイトル、日付、位置情報）
    
    プレーンテキスト形式から抽出：
    - 1行目: キーワード,カンマ,区切り
    - TITLE: タイトル文字列
    - DATE: 2002-04-29
    - LOCATION: 地域名 | 緯度 経度
    """
    from bs4 import BeautifulSoup
    
    metadata = {
        'keywords': '',
        'title': '',
        'date': '',
        'content': html_text,
        'location': None  # {'name': '', 'latitude': '', 'longitude': ''}
    }
    
    # 【優先】HTMLタグからメタデータを抽出
    soup = BeautifulSoup(html_text, 'html.parser')
    
    # <title>タグから抽出
    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.get_text(strip=True)
        if title_text:  # 空文字列でない場合のみ設定
            metadata['title'] = title_text
    
    # <title>が空の場合は<h1>〜<h9>からフォールバック
    if not metadata['title']:
        for i in range(1, 10):
            h_tag = soup.find(f'h{i}')
            if h_tag:
                h_text = h_tag.get_text(strip=True)
                if h_text:
                    metadata['title'] = h_text
                    break
    
    # <search>タグから抽出
    search_tag = soup.find('search')
    if search_tag:
        metadata['keywords'] = search_tag.get_text(strip=True)
    
    # <time datetime>属性から抽出
    time_tag = soup.find('time')
    if time_tag and time_tag.get('datetime'):
        metadata['date'] = time_tag.get('datetime')
    
    # <georss>タグから位置情報を抽出
    georss_tag = soup.find('georss')
    if georss_tag:
        name_tag = georss_tag.find('name')
        point_tag = georss_tag.find('point')
        if name_tag and point_tag:
            coords = point_tag.get_text(strip=True).split()
            if len(coords) == 2:
                metadata['location'] = {
                    'name': name_tag.get_text(strip=True),
                    'latitude': coords[0],
                    'longitude': coords[1]
                }
    
    # 【フォールバック】プレーンテキスト形式から抽出（HTMLタグで見つからなかった場合のみ）
    lines = html_text.split('\n')
    remaining_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # タイトル抽出（TITLE: で始まる行）
        if not metadata['title'] and line_stripped.startswith('TITLE:'):
            metadata['title'] = line_stripped[6:].strip()
            continue
        
        # 日付抽出（DATE: で始まる行）
        if not metadata['date'] and line_stripped.startswith('DATE:'):
            metadata['date'] = line_stripped[5:].strip()
            continue
        
        # 位置情報抽出（LOCATION: で始まる行）
        if line_stripped.startswith('LOCATION:'):
            location_text = line_stripped[9:].strip()  # "LOCATION: " の後
            parts = location_text.split('|')
            if len(parts) == 2:
                location_name = parts[0].strip()
                coords = parts[1].strip().split()
                if len(coords) == 2:
                    metadata['location'] = {
                        'name': location_name,
                        'latitude': coords[0],
                        'longitude': coords[1]
                    }
            continue
        
        # メタデータ行でない場合は本文として保持
        remaining_lines.append(line)
    
    # 本文は<body>タグの中身のみを抽出
    body_tag = soup.find('body')
    if body_tag:
        # <body>内のHTMLを文字列として取得（<body>タグ自体は除外）
        metadata['content'] = ''.join(str(child) for child in body_tag.children).strip()
    else:
        # <body>タグがない場合はフォールバック（プレーンテキスト）
        metadata['content'] = '\n'.join(remaining_lines).strip()
    
    return metadata

def html_to_atom_entry(filepath, folder_name):
    """HTML ファイルを Atom エントリに変換"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            html_text = f.read()
    except Exception as e:
        print(f"×エラー: {filepath} を読み込めません: {e}")
        return None
    
    metadata = extract_metadata(html_text, filepath)
    
    # デバッグ出力
    from pathlib import Path
    filepath_obj = Path(filepath)
    print(f"デバッグ: ファイル={filepath_obj.name}, タイトル='{metadata['title']}', キーワード='{metadata['keywords']}'")
    
    # タイトルが見つからない場合はフォルダ名を使用
    if not metadata['title']:
        metadata['title'] = folder_name
    
    # 日付が見つからない場合はファイルの更新日を使用
    if not metadata['date']:
        mtime = os.path.getmtime(filepath)
        metadata['date'] = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
    # 日付形式は YYYY-MM-DD のまま保持（ISO変換しない）
    
    # エントリID生成（一意性を保証）
    entry_id = f"tag:blogger.com,2013:post.{uuid.uuid5(uuid.NAMESPACE_DNS, filepath).hex}"
    
    # コンテンツのエスケープ（CDATA セクションで保護）
    content_escaped = metadata['content']
    
    # Atom エントリを組み立て
    entry = f"""  <entry>
    <id>{entry_id}</id>
    <published>{metadata['date']}T00:00:00+09:00</published>
    <updated>{datetime.now().isoformat()}+09:00</updated>
    <title>{escape_xml(metadata['title'])}</title>
    <content type="html"><![CDATA[{content_escaped}]]></content>
"""
    
    # カテゴリ（キーワード）を追加
    if metadata['keywords']:
        for keyword in metadata['keywords'].split(','):
            keyword = keyword.strip()
            if keyword:
                entry += f'    <category term="{escape_xml(keyword)}" />\n'
    
    # 位置情報を追加（Blogger形式のみ）
    if metadata.get('location'):
        loc = metadata['location']
        if loc.get('name'):
            entry += f"""    <blogger:location>
      <blogger:name>{escape_xml(loc['name'])}</blogger:name>
      <blogger:latitude>{loc['latitude']}</blogger:latitude>
      <blogger:longitude>{loc['longitude']}</blogger:longitude>
    </blogger:location>
"""
    
    entry += """  </entry>
"""
    
    return entry

def escape_xml(text):
    """XML テキストをエスケープ"""
    if not text:
        return text
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&apos;')
    return text

def generate_atom_feed():
    """Atom フィードを生成"""
    
    if not os.path.exists(INPUT_DIR):
        print(f"エラー: {INPUT_DIR} フォルダが見つかりません。")
        return
    
    # 出力フォルダを作成
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    entries = []
    processed_count = 0
    
    print(f"--- Atom フィード生成を開始します (対象フォルダ: {INPUT_DIR}) ---")
    
    # ready_to_upload フォルダ内を再帰的に走査
    for root, dirs, files in os.walk(str(INPUT_DIR)):
        for filename in files:
            if filename.lower().endswith(('.htm', '.html')):
                filepath = Path(root) / filename
                rel_path = filepath.relative_to(INPUT_DIR)
                folder_name = filepath.parent.name
                
                entry = html_to_atom_entry(str(filepath), folder_name)
                if entry:
                    entries.append(entry)
                    processed_count += 1
                    print(f"[{processed_count}] {rel_path} -> エントリ生成")
    
    if not entries:
        print("警告: 処理対象の HTML ファイルが見つかりません。")
        return
    
    # Atom フィードヘッダ
    atom_header = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:blogger="http://www.blogger.com/atom/ns#" xmlns:georss="http://www.georss.org/georss">
  <title>{escape_xml(BLOG_TITLE)}</title>
  <link href="{BLOG_URL}" />
  <id>tag:blogger.com,2013:blog</id>
  <updated>{datetime.now().isoformat()}+09:00</updated>
  <generator uri="https://www.blogger.com" version="1.0">Blogger</generator>
"""
    
    # Atom フィードフッタ
    atom_footer = """</feed>
"""
    
    # ファイルに書き込み
    try:
        with open(str(OUTPUT_FILE), 'w', encoding='utf-8') as f:
            f.write(atom_header)
            for entry in entries:
                f.write(entry)
            f.write(atom_footer)
        
        print("-" * 40)
        print(f"【処理完了】")
        print(f"生成したエントリ数: {processed_count}")
        print(f"出力ファイル: {OUTPUT_FILE}")
    
    except Exception as e:
        print(f"エラー: {OUTPUT_FILE} に書き込めません: {e}")

if __name__ == '__main__':
    generate_atom_feed()

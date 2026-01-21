# -*- coding: utf8 -*-
import os
import re
import uuid
from datetime import datetime
from bs4 import BeautifulSoup

# --- 設定 ---
INPUT_DIR = './ready_to_upload'     # cleaner.py の出力フォルダ
OUTPUT_FILE = 'feed.atom'            # 生成される Atom フィードファイル
BLOG_TITLE = 'My Blog'              # ブログタイトル
BLOG_URL = 'https://example.blogspot.com'  # ブログのURL

def extract_metadata(html_text, filepath=None):
    """HTML テキストからメタデータを抽出"""
    metadata = {
        'keywords': '',
        'title': '',
        'date': '',
        'content': html_text
    }
    
    # キーワード抽出（先頭にある場合）
    kw_match = re.search(r'^([^<\n]+?)(?:\n|$)', html_text)
    if kw_match and ',' in kw_match.group(1):
        metadata['keywords'] = kw_match.group(1).strip()
        # キーワード行を削除
        html_text = html_text[len(kw_match.group(0)):].strip()
    
    # タイトル抽出：reports/ フォルダの元ファイルから優先的に取得
    metadata['title'] = ''
    if filepath:
        reports_filepath = filepath.replace('./ready_to_upload', './reports').replace('.html', '.htm')
        if os.path.exists(reports_filepath):
            try:
                with open(reports_filepath, 'r', encoding='utf-8') as f:
                    reports_html = f.read()
                title_match = re.search(r'<title>(.*?)</title>', reports_html, flags=re.IGNORECASE)
                if title_match:
                    metadata['title'] = title_match.group(1).strip()
            except:
                pass
    
    # reports/ から見つからない場合は ready_to_upload/ から取得
    if not metadata['title']:
        title_match = re.search(r'<title>(.*?)</title>', html_text, flags=re.IGNORECASE)
        if title_match:
            metadata['title'] = title_match.group(1).strip()
    
    # タイトルタグを本文から削除
    html_text = re.sub(r'<title>.*?</title>', '', html_text, flags=re.IGNORECASE)
    
    # 日付抽出
    date_match = re.search(r'<time\s+datetime=["\'](.*?)["\']', html_text, flags=re.IGNORECASE)
    if date_match:
        metadata['date'] = date_match.group(1).strip()
        html_text = re.sub(r'<time\s+datetime=["\'](.*?)["\'].*?</time>', '', html_text, flags=re.IGNORECASE)
    
    metadata['content'] = html_text.strip()
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
    
    # タイトルが見つからない場合はフォルダ名を使用
    if not metadata['title']:
        metadata['title'] = folder_name
    
    # 日付が見つからない場合はファイルの更新日を使用
    if not metadata['date']:
        mtime = os.path.getmtime(filepath)
        metadata['date'] = datetime.fromtimestamp(mtime).isoformat()
    else:
        # YYYY-MM-DD 形式を ISO 形式に変換
        try:
            date_obj = datetime.strptime(metadata['date'], '%Y-%m-%d')
            metadata['date'] = date_obj.isoformat()
        except:
            pass
    
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
    
    entries = []
    processed_count = 0
    
    print(f"--- Atom フィード生成を開始します (対象フォルダ: {INPUT_DIR}) ---")
    
    # ready_to_upload フォルダ内を再帰的に走査
    for root, dirs, files in os.walk(INPUT_DIR):
        for filename in files:
            if filename.lower().endswith(('.htm', '.html')):
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, INPUT_DIR)
                folder_name = os.path.basename(os.path.dirname(filepath))
                
                entry = html_to_atom_entry(filepath, folder_name)
                if entry:
                    entries.append(entry)
                    processed_count += 1
                    print(f"[{processed_count}] {rel_path} -> エントリ生成")
    
    if not entries:
        print("警告: 処理対象の HTML ファイルが見つかりません。")
        return
    
    # Atom フィードヘッダ
    atom_header = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
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
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
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

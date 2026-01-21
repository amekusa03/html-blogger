import os
import pickle
import time
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# --- 設定 ---
BLOG_ID = 'あなたのブログID'
ATOM_FILE = 'feed.atom'
MEDIA_MANAGER_FILE = 'Blogger メディア マネージャー_ddd.html'
LOG_FILE = 'uploaded_atom_ids.txt'
SCOPES = ['https://www.googleapis.com/auth/blogger']
DELAY_SECONDS = 15      # 安全のため15秒
MAX_POSTS_PER_RUN = 5   # 最初は5件でテスト

# 画像サイズ定義 (仕様1)
SIZE_MAP = {
    'landscape': [{'w': 640, 'h': 480}, {'w': 400, 'h': 300}, {'w': 320, 'h': 240}, {'w': 200, 'h': 150}],
    'portrait':  [{'w': 480, 'h': 640}, {'w': 300, 'h': 400}, {'w': 240, 'h': 320}, {'w': 150, 'h': 200}]
}

def get_blogger_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('blogger', 'v3', credentials=creds)

def load_media_mapping():
    mapping = {}
    if not os.path.exists(MEDIA_MANAGER_FILE):
        print(f"警告: {MEDIA_MANAGER_FILE} が見つかりません。")
        return mapping
    with open(MEDIA_MANAGER_FILE, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        for a in soup.find_all('a', href=re.compile(r'googleusercontent\.com')):
            url = a['href']
            filename = url.split('/')[-1]
            mapping[filename] = url
    return mapping

def resize_logic(w, h):
    mode = 'landscape' if w >= h else 'portrait'
    targets = SIZE_MAP[mode]
    if w <= targets[-1]['w']: return targets[-1]['w'], targets[-1]['h']
    for target in targets:
        if w >= target['w']: return target['w'], target['h']
    return targets[-1]['w'], targets[-1]['h']

def process_content(html, media_map):
    """本文の加工：URL置換とリサイズのみ（タイトル挿入は行わない）"""
    soup = BeautifulSoup(html, 'html.parser')

    # 画像処理 (仕様2およびサイズ調整)
    for img in soup.find_all('img'):
        # 1. URL置換
        src_attr = img.get('src', '')
        old_filename = src_attr.split('/')[-1]
        if old_filename in media_map:
            img['src'] = media_map[old_filename]

        # 2. リサイズ (仕様1)
        try:
            w, h = int(img.get('width', 0)), int(img.get('height', 0))
            if w > 0 and h > 0:
                new_w, new_h = resize_logic(w, h)
                img['width'], img['height'] = str(new_w), str(new_h)
        except:
            pass

    return str(soup)

def extract_labels_from_content(content):
    """本文内のコメントからラベルを抽出する"""
    match = re.search(r'', content)
    if match:
        labels_str = match.group(1)
        # カンマで分割してリスト化、前後の空白を削除
        return [l.strip() for l in labels_str.split(',') if l.strip()]
    return []

def upload_from_ready_to_upload():
    media_map = load_media_mapping()
    service = get_blogger_service()

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            uploaded_ids = set(line.strip() for line in f)
    else:
        uploaded_ids = set()

    ns = {'atom': 'http://www.w3.org/2005/Atom', 'blogger': 'http://schemas.google.com/blogger/2018'}
    tree = ET.parse(ATOM_FILE)
    entries = tree.getroot().findall('atom:entry', ns)

    count = 0
    for entry in entries:
        if count >= MAX_POSTS_PER_RUN: break

        eid = entry.find('atom:id', ns).text
        status = entry.find('blogger:status', ns).text if entry.find('blogger:status', ns) is not None else 'LIVE'

        # 既にアップロード済み、または下書き/ゴミ箱のステータスはスキップ
        if eid in uploaded_ids or status == 'SOFT_TRASHED':
            continue

        # Atomから情報を取得
        title = entry.find('atom:title', ns).text or ""
        content = entry.find('atom:content', ns).text or ""
        published = entry.find('atom:published', ns).text

        # 本文の加工 (画像のみ)
        # processed_html = process_content(content, media_map)

        # # Blogger API へのリクエストボディ
        # body = {
        #     'kind': 'blogger#post',
        #     'title': title,           # ここでAtomのタイトルが記事タイトルになります
        #     'content': processed_html, # 本文にはタイトルを含めない
        #     'published': published,    # 当時の日付
        #     'blog': {'id': BLOG_ID},
        # }
        # 本文（content）からラベルを抜き出し
        labels = extract_labels_from_content(content)

        body = {
            'kind': 'blogger#post',
            'title': title,
            'content': content,
            'labels': labels,  # ← ここでラベル（リスト形式）を渡す
            'blog': {'id': BLOG_ID},
        }
    
        try:
            service.posts().insert(blogId=BLOG_ID, body=body, isDraft=True).execute()
            with open(LOG_FILE, 'a') as f:
                f.write(f"{eid}\n")
            count += 1
            print(f"[{count}] 成功: {title if title else '(タイトルなし)'}")
            time.sleep(DELAY_SECONDS)
        except Exception as e:
            print(f"エラー発生: {e}")
            break

if __name__ == '__main__':
    upload_from_atom()

import os
import pickle
import time
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from bs4 import BeautifulSoup
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
BLOG_ID = 'あなたのブログID'
LOG_FILE = SCRIPT_DIR / 'uploaded_atom_ids.txt'
SCOPES = ['https://www.googleapis.com/auth/blogger']
DELAY_SECONDS = 15      # 安全のため15秒
MAX_POSTS_PER_RUN = 5   # 最初は5件でテスト

def get_blogger_service():
    """Google Blogger API サービスオブジェクトを取得"""
    credentials_file = SCRIPT_DIR / 'credentials.json'
    if not credentials_file.exists():
        raise FileNotFoundError('credentials.json が見つかりません。Google Cloud Console から OAuth2 認証情報をダウンロードしてください。')
    
    creds = None
    token_file = SCRIPT_DIR / 'token.pickle'
    if token_file.exists():
        try:
            with open(str(token_file), 'rb') as token:
                creds = pickle.load(token)
        except Exception as e:
            print(f'警告: token.pickle の読み込みエラー: {e}')
            creds = None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print('トークンをリフレッシュしました。')
            except Exception as e:
                print(f'トークンリフレッシュエラー: {e}。新規認証を実施します。')
                creds = None
        
        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(SCRIPT_DIR / 'credentials.json'), SCOPES)
                creds = flow.run_local_server(port=0)
                print('新規認証に成功しました。')
            except Exception as e:
                raise Exception(f'Google 認証に失敗しました: {e}')
        
        try:
            with open(str(SCRIPT_DIR / 'token.pickle'), 'wb') as token:
                pickle.dump(creds, token)
        except Exception as e:
            print(f'警告: token.pickle の保存エラー: {e}')
    
    return build('blogger', 'v3', credentials=creds)

def extract_labels_from_content(content):
    """本文内のメタコメント<!--labels:...-->からラベルを抽出する"""
    # ラベルはHTMLコメント形式: <!--labels:label1,label2,label3-->
    match = re.search(r'<!--\s*labels?\s*:\s*([^-]*?)\s*-->', content, re.IGNORECASE)
    if match:
        labels_str = match.group(1)
        # カンマで分割してリスト化、前後の空白を削除
        return [l.strip() for l in labels_str.split(',') if l.strip()]
    return []

def upload_from_ready_to_upload():
    """Atom形式のフィードファイルから記事を取得して Blogger にアップロード"""
    
    # 【重大エラーチェック】BLOG_ID 設定確認
    if BLOG_ID == 'あなたのブログID' or not BLOG_ID or BLOG_ID.strip() == '':
        error_msg = "エラー: BLOG_ID が設定されていません。uploader.py の BLOG_ID 変数を設定してください。"
        print(error_msg)
        sys.exit(1)
    
    # 【重大エラーチェック】認証情報の事前確認
    try:
        service = get_blogger_service()
    except FileNotFoundError as e:
        error_msg = f"エラー: {e}"
        print(error_msg)
        sys.exit(1)
    except Exception as e:
        error_msg = f"エラー: Google認証に失敗しました: {e}\n認証情報（credentials.json）が有効か確認してください。"
        print(error_msg)
        sys.exit(1)
    
    # Atom ファイルの存在確認
    feed_file = SCRIPT_DIR / 'feed.atom'
    if not feed_file.exists():
        raise FileNotFoundError('feed.atom が見つかりません。Blogger からエクスポートした Atom ファイルを配置してください。')
    
    if LOG_FILE.exists():
        try:
            with open(str(LOG_FILE), 'r') as f:
                uploaded_ids = set(line.strip() for line in f)
        except Exception as e:
            print(f'ログファイル読み込みエラー: {e}')
            uploaded_ids = set()
    else:
        uploaded_ids = set()
        print(f'新規ログファイルを作成します: {LOG_FILE}')

    # Atom ファイル解析
    ns = {'atom': 'http://www.w3.org/2005/Atom', 'blogger': 'http://schemas.google.com/blogger/2018'}
    try:
        tree = ET.parse(str(feed_file))
    except ET.ParseError as e:
        print(f'Atom ファイルのパースエラー: {e}')
        return
    except Exception as e:
        print(f'予期しないエラー: {e}')
        return
    entries = tree.getroot().findall('atom:entry', ns)

    count = 0
    error_count = 0
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
            response = service.posts().insert(blogId=BLOG_ID, body=body, isDraft=True).execute()
            try:
                with open(str(LOG_FILE), 'a') as f:
                    f.write(f"{eid}\n")
            except Exception as log_error:
                print(f'警告: ログ記録エラー: {log_error}')
            count += 1
            post_id = response.get('id', 'N/A')
            print(f"[{count}] 成功 (ID: {post_id}): {title if title else '(タイトルなし)'}")
            time.sleep(DELAY_SECONDS)
        except Exception as e:
            error_count += 1
            error_msg = f"エラー発生 (タイトル: {title}): {e}"
            print(error_msg)
            # 【重大エラー】アップロード失敗時は明示的に中断
            if error_count > 0:
                print("処理を中止します。")
                sys.exit(1)

if __name__ == '__main__':
    upload_from_ready_to_upload()

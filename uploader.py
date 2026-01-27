import os
import pickle
import time
import re
import sys
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from bs4 import BeautifulSoup
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from config import get_config

# --- ロギング設定 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('uploader.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
BLOG_ID = get_config('UPLOADER', 'BLOG_ID')
logger.debug(f"読み込まれたBLOG_ID = {BLOG_ID}")
LOG_FILE = SCRIPT_DIR / get_config('UPLOADER', 'LOG_FILE', 'uploaded_atom_ids.txt')
SCOPES = [get_config('UPLOADER', 'SCOPES', 'https://www.googleapis.com/auth/blogger')]
DELAY_SECONDS = float(get_config('UPLOADER', 'DELAY_SECONDS', '1.1'))
MAX_POSTS_PER_RUN = int(get_config('UPLOADER', 'MAX_POSTS_PER_RUN', '1'))

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
            logger.warning(f'token.pickle の読み込みエラー: {e}')
            creds = None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info('トークンをリフレッシュしました。')
            except Exception as e:
                logger.warning(f'トークンリフレッシュエラー: {e}。新規認証を実施します。')
                creds = None
        
        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(SCRIPT_DIR / 'credentials.json'), SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info('新規認証に成功しました。')
            except Exception as e:
                raise Exception(f'Google 認証に失敗しました: {e}')
        
        try:
            with open(str(SCRIPT_DIR / 'token.pickle'), 'wb') as token:
                pickle.dump(creds, token)
        except Exception as e:
            logger.warning(f'token.pickle の保存エラー: {e}')
    
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
        logger.error("BLOG_ID が設定されていません。config.ini の [UPLOADER] セクションを確認してください。")
        sys.exit(1)
    
    # 【重大エラーチェック】認証情報の事前確認
    try:
        service = get_blogger_service()
    except FileNotFoundError as e:
        logger.error(f"{e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Google認証に失敗しました: {e}")
        logger.error("認証情報（credentials.json）が有効か確認してください。")
        sys.exit(1)
    
    # Atom ファイルの存在確認（ready_upload フォルダ内）
    feed_file = SCRIPT_DIR / get_config('READY_UPLOAD', 'OUTPUT_DIR', './ready_upload').lstrip('./') / 'feed.atom'
    if not feed_file.exists():
        raise FileNotFoundError(f'feed.atom が見つかりません。convert_atom.py を実行して {feed_file} を生成してください。')
    
    if LOG_FILE.exists():
        try:
            with open(str(LOG_FILE), 'r') as f:
                uploaded_ids = set(line.strip() for line in f)
        except Exception as e:
            logger.warning(f'ログファイル読み込みエラー: {e}')
            uploaded_ids = set()
    else:
        uploaded_ids = set()
        logger.info(f'新規ログファイルを作成します: {LOG_FILE}')

    # Atom ファイル解析
    ns = {
        'atom': 'http://www.w3.org/2005/Atom',
        'blogger': 'http://www.blogger.com/atom/ns#',
        'georss': 'http://www.georss.org/georss'
    }
    try:
        tree = ET.parse(str(feed_file))
    except ET.ParseError as e:
        logger.error(f'Atom ファイルのパースエラー: {e}')
        return
    except Exception as e:
        logger.error(f'予期しないエラー: {e}')
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

        # ラベルを<category>タグから抽出（Atom形式）
        labels = []
        for category in entry.findall('atom:category', ns):
            term = category.get('term')
            if term:
                labels.append(term)

        # 位置情報を<blogger:location>から抽出
        location_data = None
        blogger_location = entry.find('blogger:location', ns)
        if blogger_location is not None:
            name_elem = blogger_location.find('blogger:name', ns)
            lat_elem = blogger_location.find('blogger:latitude', ns)
            lng_elem = blogger_location.find('blogger:longitude', ns)
            
            if name_elem is not None and lat_elem is not None and lng_elem is not None:
                location_data = {
                    'name': name_elem.text.strip(),
                    'lat': float(lat_elem.text),
                    'lng': float(lng_elem.text)
                }

        body = {
            'kind': 'blogger#post',
            'title': title,
            'content': content,
            'labels': labels,
            'blog': {'id': BLOG_ID},
            'published': published
        }

        # 位置情報があれば追加
        if location_data:
            body['location'] = location_data

        logger.info("=" * 50)
        logger.info(f"アップロード開始: {title}")
        logger.info(f"公開日: {published}")
        logger.info(f"BLOG_ID: {BLOG_ID}")
        logger.info(f"ラベル: {labels}")
        if location_data:
            logger.info(f"場所: {location_data['name']} ({location_data['lat']}, {location_data['lng']})")
        
        # デバッグ: 送信するbodyデータを全て表示
        import json
        logger.debug("送信するAPIリクエストボディ:")
        logger.debug(json.dumps(body, indent=2, ensure_ascii=False))
        
        try:
            # 【テストモード】Blogger APIにアクセスしない（動作確認用）
            TEST_MODE = True   # Trueに設定するとAPI呼び出しをスキップします
            
            if TEST_MODE:
                logger.warning("【テストモード】API呼び出しをスキップします")
                response = {'id': 'TEST_POST_ID', 'url': 'https://test.url'}
            else:
                response = service.posts().insert(blogId=BLOG_ID, body=body, isDraft=True).execute()
            
            try:
                with open(str(LOG_FILE), 'a') as f:
                    f.write(f"{eid}\n")
            except Exception as log_error:
                logger.warning(f'ログ記録エラー: {log_error}')
            count += 1
            post_id = response.get('id', 'N/A')
            logger.info(f"[{count}] 成功 (ID: {post_id}): {title if title else '(タイトルなし)'}")
            time.sleep(DELAY_SECONDS)
        except Exception as e:
            error_count += 1
            logger.error(f"アップロード失敗 (タイトル: {title}): {e}", exc_info=True)
            # エラーがあっても処理を継続

    # 処理完了サマリー
    logger.info("=" * 50)
    logger.info("処理完了")
    logger.info(f"成功: {count}件")
    logger.info(f"エラー: {error_count}件")
    if error_count > 0:
        logger.warning("エラーが発生したポストがあります。uploader.log を確認してください。")

if __name__ == '__main__':
    upload_from_ready_to_upload()

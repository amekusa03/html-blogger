import time
import json
import logging
from logging.handlers import RotatingFileHandler
import xml.etree.ElementTree as ET
from pathlib import Path
from config import get_config
from utils import ProgressBar

# --- ロギング設定 ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('uploader.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING)
logger.addHandler(stream_handler)

try:
    from google_auth import get_blogger_service
except ImportError:
    logger.error("google_auth.py が見つかりません。")
    get_blogger_service = None

# --- 設定 ---

def upload_from_ready_to_upload():
    """Atom形式のフィードファイルから記事を取得して Blogger にアップロード"""
    
    SCRIPT_DIR = Path(__file__).parent.resolve()
    
    try:
        # デバッグ設定
        DEBUG_LOG = get_config('DEFAULT', 'debug_log', 'false').lower() == 'true'
        if DEBUG_LOG:
            logger.setLevel(logging.DEBUG)

        BLOG_ID = get_config('UPLOADER', 'BLOG_ID')
        logger.debug(f"読み込まれたBLOG_ID = {BLOG_ID}")
        LOG_FILE = SCRIPT_DIR / get_config('UPLOADER', 'LOG_FILE', 'uploaded_atom_ids.txt')
        TEST_MODE = get_config('UPLOADER', 'TEST_MODE', 'false').lower() == 'true'
        READY_UPLOAD_DIR = get_config('READY_UPLOAD', 'OUTPUT_DIR', './ready_upload').lstrip('./')
    except Exception as e:
        logger.error(f"設定の読み込みに失敗しました: {e}")
        return

    try:
        DELAY_SECONDS = float(get_config('UPLOADER', 'DELAY_SECONDS', '1.1'))
        MAX_POSTS_PER_RUN = int(get_config('UPLOADER', 'MAX_POSTS_PER_RUN', '1'))
    except Exception as e:
        logger.warning(f"設定値(DELAY_SECONDS, MAX_POSTS_PER_RUN)の読み込みに失敗しました: {e}。デフォルト値を使用します。")
        DELAY_SECONDS = 1.1
        MAX_POSTS_PER_RUN = 1

    # 【重大エラーチェック】BLOG_ID 設定確認
    if BLOG_ID == 'あなたのブログID' or not BLOG_ID or BLOG_ID.strip() == '':
        logger.error("BLOG_ID が設定されていません。config.ini の [UPLOADER] セクションを確認してください。")
        return
    
    if get_blogger_service is None:
        logger.error("google_authモジュールが読み込めなかったため、処理を中断します。")
        return

    # 【重大エラーチェック】認証情報の事前確認
    try:
        service = get_blogger_service()
    except FileNotFoundError as e:
        logger.error(f"{e}")
        return
    except Exception as e:
        logger.error(f"Google認証に失敗しました: {e}")
        logger.error("認証情報（credentials.json）が有効か確認してください。")
        return
    
    # Atom ファイルの存在確認（ready_upload フォルダ内）
    feed_file = SCRIPT_DIR / READY_UPLOAD_DIR / 'feed.atom'
    if not feed_file.exists():
        logger.error(f'feed.atom が見つかりません。convert_atom.py を実行して {feed_file} を生成してください。')
        return
    
    if LOG_FILE.exists():
        try:
            with open(str(LOG_FILE), 'r', encoding='utf-8') as f:
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
    
    try:
        entries = tree.getroot().findall('atom:entry', ns)
    except Exception as e:
        logger.error(f'Atom エントリの取得に失敗しました: {e}')
        return

    count = 0
    error_count = 0
    pbar = ProgressBar(len(entries), prefix='AtomUpload')

    for entry in entries:
        if count >= MAX_POSTS_PER_RUN: break

        try:
            eid_elem = entry.find('atom:id', ns)
            if eid_elem is None or not eid_elem.text:
                raise AttributeError("atom:id is missing or empty")
            eid = eid_elem.text
            status_elem = entry.find('blogger:status', ns)
            status = status_elem.text if status_elem is not None and status_elem.text else 'LIVE'
        except AttributeError:
            pbar.update()
            continue

        # 既にアップロード済み、または下書き/ゴミ箱のステータスはスキップ
        if eid in uploaded_ids or status == 'SOFT_TRASHED':
            pbar.update()
            continue

        title = "(タイトル取得前)"
        try:
            # Atomから情報を取得
            title_elem = entry.find('atom:title', ns)
            title = title_elem.text if title_elem is not None and title_elem.text else ""
            
            content_elem = entry.find('atom:content', ns)
            content = content_elem.text if content_elem is not None and content_elem.text else ""
            
            published_elem = entry.find('atom:published', ns)
            published = published_elem.text if published_elem is not None and published_elem.text else ""

            # ラベルを<category>タグから抽出（Atom形式）
            labels = []
            for category in entry.findall('atom:category', ns):
                term = category.get('term')
                if term:
                    labels.append(term)

            # 位置情報を<blogger:location>から抽出
            location_data = None
            try:
                blogger_location = entry.find('blogger:location', ns)
                if blogger_location is not None:
                    name_elem = blogger_location.find('blogger:name', ns)
                    lat_elem = blogger_location.find('blogger:latitude', ns)
                    lng_elem = blogger_location.find('blogger:longitude', ns)
                    
                    if name_elem is not None and lat_elem is not None and lng_elem is not None:
                        location_data = {
                            'name': name_elem.text.strip() if name_elem.text else "",
                            'lat': float(lat_elem.text),
                            'lng': float(lng_elem.text)
                        }
            except (ValueError, TypeError):
                logger.warning(f"位置情報の座標変換に失敗しました。位置情報はスキップされます。 (タイトル: {title})")
                location_data = None

            body = {
                'kind': 'blogger#post',
                'title': title,
                'content': content,
                'labels': labels,
                'blog': {'id': BLOG_ID},
                'published': published
            }

            # 公開日時があれば追加
            if published:
                body['published'] = published

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
            logger.debug("送信するAPIリクエストボディ:")
            logger.debug(json.dumps(body, indent=2, ensure_ascii=False))
            
            if TEST_MODE:
                logger.warning("【テストモード】API呼び出しをスキップします")
                response = {'id': 'TEST_POST_ID', 'url': 'https://test.url'}
            else:
                # API呼び出しのリトライ処理
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = service.posts().insert(blogId=BLOG_ID, body=body, isDraft=True).execute()
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 2
                            logger.warning(f"APIエラー (試行 {attempt+1}/{max_retries}): {e} - {wait_time}秒後に再試行します")
                            time.sleep(wait_time)
                        else:
                            raise
            
            try:
                with open(str(LOG_FILE), 'a', encoding='utf-8') as f:
                    f.write(f"{eid}\n")
            except Exception as log_error:
                logger.warning(f'ログ記録エラー: {log_error}')
            count += 1
            post_id = response.get('id', 'N/A')
            logger.info(f"[{count}] 成功 (ID: {post_id}): {title if title else '(タイトルなし)'}")
        except Exception as e:
            error_count += 1
            logger.error(f"アップロード失敗 (タイトル: {title}): {e}", exc_info=True)
            # エラーがあっても処理を継続
        finally:
            time.sleep(DELAY_SECONDS)
            pbar.update()

    # 処理完了サマリー
    logger.info("=" * 50)
    logger.info("処理完了")
    logger.info(f"成功: {count}件")
    logger.info(f"エラー: {error_count}件")
    if error_count > 0:
        logger.warning("エラーが発生したポストがあります。uploader.log を確認してください。")

if __name__ == '__main__':
    try:
        upload_from_ready_to_upload()
    except KeyboardInterrupt:
        logger.info("処理が中断されました。")
    except Exception as e:
        logger.critical(f"予期せぬエラーが発生しました: {e}", exc_info=True)

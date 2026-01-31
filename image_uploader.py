# -*- coding: utf-8 -*-
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import time
import shutil
import re
import json
import html
from urllib.parse import unquote

# 依存モジュール
from config import get_config
from utils import ProgressBar
import database

# --- ロギング設定 ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('image_uploader.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING) # プログレスバー表示のため、コンソールは警告以上のみ表示
logger.addHandler(stream_handler)

# スクリプトのディレクトリを基準にする
SCRIPT_DIR = Path(__file__).parent.resolve()
SESSION_FILE = SCRIPT_DIR / '.img_session.json'

def _get_current_serial():
    """現在のシリアル番号を取得"""
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('last_id', "001A")
        except Exception:
            pass
    return "001A"

def _increment_serial():
    """シリアル番号を更新"""
    current_id = _get_current_serial()
    prefix = current_id[:-1]
    char_code = ord(current_id[-1]) + 1
    if char_code > ord('Z'):
        prefix = f"{int(prefix) + 1:03d}"
        char_code = ord('A')
    new_id = f"{prefix}{chr(char_code)}"
    
    with open(SESSION_FILE, 'w', encoding='utf-8') as f:
        json.dump({'last_id': new_id}, f)

def prepare_manual_upload(images, upload_dir):
    """手動アップロード用に画像を準備する"""
    # コピー元とコピー先が同じ場合は削除・コピーをスキップする（データ消失防止）
    is_same_dir = False
    if images:
        first_src = Path(images[0]['processed_path']).resolve()
        upload_dir_abs = upload_dir.resolve()
        if first_src.parent == upload_dir_abs:
            is_same_dir = True
            logger.warning(f"注意: 画像処理出力先と手動アップロードフォルダが同一です: {upload_dir}")
            # 同一の場合はフォルダ削除を行わず、ファイル生成のみ行う

    if not is_same_dir:
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

    serial = _get_current_serial()
    logger.info(f"現在のシリアル番号: {serial}")

    count = 0
    for img in images:
        src = Path(img['processed_path'])
        if src.exists():
            new_name = f"{serial}_{src.name}"
            dest = upload_dir / new_name
            
            # 同一ファイルへのコピーを防ぐ
            if src.resolve() != dest.resolve():
                shutil.copy2(src, dest)
                
            count += 1
    
    logger.info(f"{count} 枚の画像を {upload_dir} にコピーしました。(シリアル: {serial})")

def extract_blogger_urls(file_content_bytes):
    """貼り付けられたHTMLからBloggerの画像URLを抽出する"""
    url_map = {}
    pattern = re.compile(r'(https?://blogger\.googleusercontent\.com/[^"\'\s<>]+)')

    # テキストとして読み込んで正規表現で抽出 (MHTMLもテキストとして処理)
    try:
        content_str = file_content_bytes.decode('utf-8', errors='ignore')
        
        # MHTML等のQuoted-Printable対策: ソフト改行(=改行)を除去
        content_unfolded = content_str.replace('=\n', '').replace('=\r\n', '')
        
        # HTMLエンティティをデコード
        content_unfolded = html.unescape(content_unfolded)
        
        for match in pattern.finditer(content_unfolded):
            url = match.group(1)
            filename = unquote(url.split('/')[-1].split('?')[0])
            if filename not in url_map:
                url_map[filename] = url
    except Exception as e:
        logger.error(f"テキスト解析中にエラーが発生しました: {e}")

    return url_map

def process_manual_upload(images, paste_file):
    """ペーストファイルを読み込んでDBを更新する"""
    try:
        with open(paste_file, 'rb') as f: # Read as binary for MHTML parsing
            content_bytes = f.read()
    except Exception as e:
        logger.error(f"ペーストファイルの読み込みに失敗: {e}")
        return 0, 0

    url_map = extract_blogger_urls(content_bytes)
    logger.info(f"抽出されたURL数: {len(url_map)}")

    serial = _get_current_serial()
    success_count = 0
    error_count = 0

    for img in images:
        filename = Path(img['processed_path']).name
        serialized_name = f"{serial}_{filename}"
        
        if serialized_name in url_map:
            blogger_url = url_map[serialized_name]
            database.update_image_info(img['id'], status='uploaded', blogger_url=blogger_url)
            logger.info(f"URL解決: {serialized_name} -> {blogger_url}")
            success_count += 1
        else:
            logger.warning(f"URL未解決: {serialized_name} (ペーストファイル内に見つかりません)")
            error_count += 1
            
    if success_count > 0:
        _increment_serial()
        logger.info("シリアル番号を更新しました。")

    return success_count, error_count

def run_image_upload_pipeline():
    """DBから'watermarked'ステータスの画像をBloggerにアップロードするパイプライン"""
    # --- 設定を関数スコープで読み込む ---
    BLOG_ID = get_config('UPLOADER', 'blog_id')
    DELAY_SECONDS = float(get_config('UPLOADER', 'DELAY_SECONDS', '1.1'))
    TEST_MODE = get_config('UPLOADER', 'test_mode', 'false').lower() == 'true'
    DEBUG_LOG = get_config('DEFAULT', 'debug_log', 'false').lower() == 'true'

    # デバッグモードに応じてログレベルを動的に変更
    if DEBUG_LOG:
        logger.setLevel(logging.DEBUG)

    # デバッグ用に現在の設定値をログに出力
    logger.debug(f"Config: BLOG_ID='{BLOG_ID}', DELAY_SECONDS={DELAY_SECONDS}, TEST_MODE={TEST_MODE}")
    
    logger.info("--- 画像アップロードパイプライン開始 ---")

    if not BLOG_ID:
        logger.error("BLOG_IDがconfig.iniに設定されていません。処理を中断します。")
        return 0, 1
    
    # 処理対象の画像を取得
    images_to_upload = database.get_images_by_status('watermarked')
    
    if not images_to_upload:
        logger.info("処理対象の画像はありません。")
        logger.info("--- 画像アップロードパイプライン完了 ---")
        return 0, 0
        
    # 作業用パス
    # WORK_DIR = Path(get_config('CLEANER', 'output_dir', './work')) # workフォルダは使用しない
    UPLOAD_DIR = SCRIPT_DIR / 'processed_images'
    PASTE_DIR = SCRIPT_DIR / 'blogger_html'
    PASTE_DIR.mkdir(exist_ok=True)

    # ペーストファイルが存在するか確認
    paste_files = list(PASTE_DIR.glob('*.html')) + list(PASTE_DIR.glob('*.txt')) + list(PASTE_DIR.glob('*.mhtml'))
    
    if len(paste_files) == 1:
        paste_file = paste_files[0]
        logger.info(f"ペーストファイルが見つかりました: {paste_file}")
        success, error = process_manual_upload(images_to_upload, paste_file)
        # 処理済みファイルはリネーム
        paste_file.rename(paste_file.with_name(paste_file.name + '.processed'))
        logger.info("--- 画像アップロードパイプライン完了 (URL解決) ---")
        return success, error
    elif len(paste_files) > 1:
        logger.error(f"エラー: {PASTE_DIR} に複数のファイル(*.html, *.txt)が見つかりました。1つだけにしてください。")
        return 0, 1
    else:
        logger.info(f"ペーストファイルが見つかりません (検索対象: {PASTE_DIR}/*.html, *.txt)")
        # 手動アップロードの準備
        prepare_manual_upload(images_to_upload, UPLOAD_DIR)
        logger.warning("【重要】画像アップロードは手動で行う必要があります。")
        logger.warning(f"1. '{UPLOAD_DIR}' 内の画像をBloggerにアップロードしてください。")
        logger.warning(f"2. 投稿画面(HTMLビュー)の内容を '{PASTE_DIR}' フォルダに '*.html' として保存してください。")
        logger.warning("3. 保存後、再度このツールを実行してください。")
        
        # パイプラインを中断するためのシグナルを返す
        return 0, 0, 'MANUAL_UPLOAD_REQUIRED'
        
    logger.info("--- 画像アップロードパイプライン完了 ---")
    return 0, 0 # エラーではないが、完了もしていない状態

if __name__ == '__main__':
    try:
        run_image_upload_pipeline()
    except Exception as e:
        logger.critical(f"予期せぬエラーが発生しました: {e}", exc_info=True)
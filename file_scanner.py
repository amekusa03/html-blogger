# -*- coding: utf-8 -*-
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import hashlib

# このスクリプトが依存するモジュール
from config import get_config
from utils import ProgressBar
import database
from bs4 import BeautifulSoup

# --- ロギング設定 ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('file_scanner.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING) # プログレスバー表示のため、コンソールは警告以上のみ表示
logger.addHandler(stream_handler)

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
# どのディレクトリをスキャン対象にするか。
# cleaner.py の出力先である 'work' フォルダを対象とするのが自然なパイプライン。
# config.ini の [CLEANER] セクションから読み込む。
SCAN_DIR = SCRIPT_DIR / get_config('CLEANER', 'output_dir', './work').lstrip('./')

def check_orphaned_files():
    """DB上の処理中レコードと実ファイルの整合性をチェック"""
    logger.info("--- 孤立レコードのチェック ---")
    missing_count = 0
    
    # 記事チェック
    articles = database.get_processing_records('articles')
    for art in articles:
        path = Path(art['source_path'])
        if not path.exists():
            logger.warning(f"記事ファイル消失: {path.name} (ID: {art['id']}) -> status='missing'")
            database.update_status(art['id'], 'missing', 'ソースファイルが見つかりません')
            missing_count += 1
            
    # 画像チェック
    images = database.get_processing_records('images')
    for img in images:
        path = Path(img['source_path'])
        if not path.exists():
            logger.warning(f"画像ファイル消失: {path.name} (ID: {img['id']}) -> status='missing'")
            database.update_image_info(img['id'], status='missing', error_message='ソースファイルが見つかりません')
            missing_count += 1
            
    if missing_count == 0:
        logger.info("孤立レコードはありません。")
    else:
        logger.info(f"{missing_count} 件の孤立レコードを 'missing' に更新しました。")

def calculate_file_hash(filepath):
    """ファイルのSHA256ハッシュを計算する"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def scan_and_register_files():
    """
    指定されたディレクトリを再帰的にスキャンし、
    新しいHTMLファイルをデータベースに登録する。
    """
    # デバッグログ設定の反映
    if get_config('DEFAULT', 'debug_log', 'false').lower() == 'true':
        logger.setLevel(logging.DEBUG)

    logger.info(f"--- ファイルスキャン開始 (対象ディレクトリ: {SCAN_DIR}) ---")

    if not SCAN_DIR.exists():
        logger.error(f"スキャン対象ディレクトリが見つかりません: {SCAN_DIR}")
        return 0, 1

    # データベースとテーブルが存在しない場合は初期化
    database.init_db()

    # 既存レコードの整合性チェック
    check_orphaned_files()

    total_found = 0
    newly_registered_articles = 0
    newly_registered_images = 0
    error_count = 0
    skipped_count = 0

    # 対象ファイルをリストアップ
    target_files = [p for p in SCAN_DIR.rglob('*') if p.is_file() and p.suffix.lower() in ['.html', '.htm']]
    total_found = len(target_files)
    
    # ファイルサイズ制限 (2MB)
    MAX_FILE_SIZE = 2 * 1024 * 1024

    if total_found > 0:
        pbar = ProgressBar(total_found, prefix='Scan')

        for file_path in target_files:
            logger.debug(f"ファイル検査: {file_path.name}")
            # サイズチェック
            if file_path.stat().st_size > MAX_FILE_SIZE:
                logger.warning(f"サイズ超過のためスキップ: {file_path.name} ({file_path.stat().st_size} bytes)")
                pbar.update()
                continue

            # ハッシュ計算と重複チェック
            file_hash = calculate_file_hash(file_path)
            existing = database.check_hash_exists(file_hash)
            if existing:
                # 既に存在する場合でも、ステータスが 'missing' や 'error' なら再処理対象として復活させる
                if existing['status'] in ('missing', 'error'):
                    logger.info(f"再処理対象として復活: {file_path.name} (ID: {existing['id']}, Status: {existing['status']})")
                    database.revive_article(existing['id'], file_path)
                    article_id = existing['id']
                else:
                    logger.info(f"重複コンテンツ検出 (スキップ): {file_path.name} (Status: {existing['status']}) は {Path(existing['source_path']).name} と同一です。")
                    skipped_count += 1
                    pbar.update()
                    continue
            else:
                article_id = database.register_file(file_path, content_hash=file_hash)

            # 新規登録された記事の場合のみ、中の画像をスキャンする
            if article_id is not None:
                newly_registered_articles += 1
                
                # HTMLをパースして画像を探す
                try:
                    # 文字コードを試しながら読み込む
                    content = None
                    for encoding in ['utf-8', 'cp932', 'shift_jis', 'euc-jp']:
                        try:
                            with open(file_path, 'r', encoding=encoding) as f:
                                content = f.read()
                            break
                        except UnicodeDecodeError:
                            continue
                    
                    if not content:
                        logger.warning(f"文字コード不明で画像スキャンをスキップ: {file_path.name}")
                        continue

                    soup = BeautifulSoup(content, 'html.parser')
                    found_imgs = soup.find_all('img')
                    if found_imgs:
                        logger.debug(f"[{file_path.name}] 画像タグ検出数: {len(found_imgs)}")

                    for img_tag in found_imgs:
                        src = img_tag.get('src')
                        logger.debug(f"  - src属性: {src}")
                        if src and not src.startswith(('http://', 'https://')):
                            # ローカル画像パスを解決 (HTMLファイルからの相対パスとして扱う)
                            image_path = file_path.parent / src
                            if image_path.exists():
                                image_id = database.register_image(article_id, image_path.resolve())
                                if image_id is not None:
                                    newly_registered_images += 1
                            else:
                                logger.warning(f"  -> 画像ファイルが見つかりません: {image_path} (in {file_path.name})")

                except Exception as e:
                    logger.error(f"画像スキャン中にエラーが発生しました ({file_path.name}): {e}")
                    error_count += 1
            
            pbar.update()

    logger.info("--- ファイルスキャン完了 ---")
    logger.info(f"発見したHTMLファイル総数: {total_found}")
    logger.info(f"新規にDBへ登録した記事数: {newly_registered_articles}")
    logger.info(f"新規にDBへ登録した画像数: {newly_registered_images}")
    
    return newly_registered_articles + newly_registered_images, error_count, skipped_count

if __name__ == '__main__':
    scan_and_register_files()
# -*- coding: utf-8 -*-
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import shutil
from datetime import datetime

from config import get_config
from utils import ProgressBar
import database

# --- ロギング設定 ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('archiver.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
logger.addHandler(logging.StreamHandler())

def run_archiver_pipeline():
    """
    アップロード済みの記事と関連画像をアーカイブフォルダに移動する
    """
    logger.info("=== アーカイブ処理開始 ===")
    
    SCRIPT_DIR = Path(__file__).parent.resolve()
    ARCHIVE_DIR = SCRIPT_DIR / get_config('ARCHIVER', 'output_dir', './archive').lstrip('./')
    
    articles_to_archive = database.get_articles_by_status('uploaded')
    
    if not articles_to_archive:
        logger.info("アーカイブ対象の記事はありません。")
        logger.info("=== アーカイブ処理完了 ===")
        return 0, 0

    # 実行ごとのタイムスタンプ付きフォルダを作成
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    run_archive_dir = ARCHIVE_DIR / timestamp
    run_archive_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"{len(articles_to_archive)} 件の記事を {run_archive_dir} にアーカイブします。")
    
    success_count, error_count = 0, 0
    pbar = ProgressBar(len(articles_to_archive), prefix='Archive')

    for article in articles_to_archive:
        article_id = article['id']
        source_html_path = Path(article['source_path'])
        
        try:
            # 1. HTMLファイルを移動
            if source_html_path.exists():
                shutil.move(str(source_html_path), str(run_archive_dir / source_html_path.name))

            # 2. 関連画像を移動
            images = database.get_images_by_article_id(article_id)
            for image in images:
                if image['processed_path'] and Path(image['processed_path']).exists():
                    shutil.move(str(image['processed_path']), str(run_archive_dir / Path(image['processed_path']).name))
                database.update_image_info(image['id'], status='archived')

            # 3. 記事のステータスを 'archived' に更新
            database.update_status(article_id, 'archived')
            success_count += 1
        except Exception as e:
            logger.error(f"アーカイブ処理失敗 (ID: {article_id}): {e}", exc_info=True)
            error_count += 1
        finally:
            pbar.update()
            
    logger.info("=== アーカイブ処理完了 ===")
    logger.info(f"成功: {success_count}件, 失敗: {error_count}件")
    return success_count, error_count

if __name__ == '__main__':
    run_archiver_pipeline()
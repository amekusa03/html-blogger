# -*- coding: utf-8 -*-
import logging
from logging.handlers import RotatingFileHandler

import database

# --- ロギング設定 ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('retry_errors.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
logger.addHandler(logging.StreamHandler())

def run_retry_process():
    """status='error' のレコードを、再処理可能な状態に戻す"""
    logger.info("=== エラーステータスのリセット処理開始 ===")
    
    # 記事のエラーをリセット
    error_articles = database.get_articles_by_status('error')
    logger.info(f"{len(error_articles)}件のエラー記事をチェックします。")
    reset_article_count = 0
    for article in error_articles:
        # content の内容を調べて、どの段階まで成功していたかを判断する
        content = article.get('content', '')
        prev_status = 'new' # デフォルト

        if content and '<georss' in content:
            # 位置情報追加までは成功しているので、アップロードで失敗したと判断
            prev_status = 'location_added'
        elif content and '<search' in content:
            # キーワード追加までは成功しているので、位置情報追加で失敗したと判断
            prev_status = 'keywords_added'
        # それ以外の場合は、キーワード追加で失敗したと判断 (デフォルトの 'new' を使用)

        database.reset_article_error(article['id'], prev_status)
        reset_article_count += 1
    
    # 画像のエラーをリセット
    error_images = database.get_images_by_status('error')
    logger.info(f"{len(error_images)}件のエラー画像をチェックします。")
    reset_image_count = 0
    for image in error_images:
        # 画像のエラーも同様に、どの段階で失敗したかを推測する。
        # processed_path があればウォーターマークは成功していると判断できる。
        if image.get('processed_path'):
            # ウォーターマークは終わっているので、アップロードで失敗したと判断
            prev_status = 'watermarked'
        else:
            # ウォーターマーク処理自体で失敗したと判断
            prev_status = 'new'
        database.reset_image_error(image['id'], prev_status)
        reset_image_count += 1

    logger.info("=== エラーステータスのリセット処理完了 ===")
    logger.info(f"リセットした記事数: {reset_article_count}")
    logger.info(f"リセットした画像数: {reset_image_count}")
    if (reset_article_count + reset_image_count) > 0:
        logger.info("リセットが完了しました。次回のパイプライン実行時に再処理されます。")

if __name__ == '__main__':
    print("警告: status='error' の記事と画像が、再処理可能な状態に戻されます。")
    choice = input("実行しますか？ (y/N): ")
    if choice.lower() == 'y':
        run_retry_process()
    else:
        print("キャンセルしました。")
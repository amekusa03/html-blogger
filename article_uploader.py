# -*- coding: utf-8 -*-
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import time
from datetime import datetime
from bs4 import BeautifulSoup
from googleapiclient.errors import HttpError
from PIL import Image
import re

# 依存モジュール
from config import get_config
from utils import ProgressBar
import database

# --- ロギング設定 ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('article_uploader.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING) # プログレスバー表示のため、コンソールは警告以上のみ表示
logger.addHandler(stream_handler)

try:
    # 既存の認証関数を再利用
    from google_auth import get_blogger_service
except ImportError:
    logger.error("エラー: google_auth.py が見つかりません。")
    get_blogger_service = None

def check_duplicate_title(service, blog_id, title):
    """Blogger上に同タイトルの記事が存在するか確認する"""
    try:
        # qパラメータで検索 (posts().list ではなく posts().search を使用)
        request = service.posts().search(blogId=blog_id, q=title, fetchBodies=False)
        response = request.execute()
        items = response.get('items', [])
        
        for item in items:
            if item.get('title', '').strip() == title.strip():
                return item['id']
        return None
    except Exception as e:
        logger.warning(f"重複チェックAPIエラー: {e}")
        return None

def run_article_upload_pipeline():
    """DBから'keywords_added'ステータスの記事をBloggerにアップロードするパイプライン"""
    # --- 設定を関数スコープで読み込む ---
    BLOG_ID = get_config('UPLOADER', 'blog_id')
    DELAY_SECONDS = float(get_config('UPLOADER', 'DELAY_SECONDS', '1.1'))
    TEST_MODE = get_config('UPLOADER', 'TEST_MODE', 'false').lower() == 'true'
    DEBUG_LOG = get_config('DEFAULT', 'debug_log', 'false').lower() == 'true'

    # デバッグモードに応じてログレベルを動的に変更
    if DEBUG_LOG:
        logger.setLevel(logging.DEBUG)

    # デバッグ用に現在の設定値をログに出力
    logger.debug(f"Config: BLOG_ID='{BLOG_ID}', DELAY_SECONDS={DELAY_SECONDS}, TEST_MODE={TEST_MODE}")
    
    logger.info("--- 記事アップロードパイプライン開始 ---")

    if not BLOG_ID:
        logger.error("BLOG_IDがconfig.iniに設定されていません。処理を中断します。")
        return 0, 1

    if get_blogger_service is None:
        logger.error("google_authモジュールが読み込めなかったため、処理を中断します。")
        return 0, 1

    try:
        service = get_blogger_service()
    except Exception as e:
        logger.error(f"Google認証に失敗しました: {e}", exc_info=True)
        return 0, 1

    articles_to_process = database.get_articles_by_status('location_added')
    
    if not articles_to_process:
        logger.info("処理対象の記事はありません。")
        logger.info("--- 記事アップロードパイプライン完了 ---")
        return 0, 0

    logger.info(f"{len(articles_to_process)} 件の記事をアップロードします。")
    success_count, error_count, skipped_count = 0, 0, 0

    pbar = ProgressBar(len(articles_to_process), prefix='ArtUpload')
    for article_data in articles_to_process:
        article_id = article_data['id']
        html_content = article_data['content']
        source_path = Path(article_data['source_path'])

        try:
            logger.info(f"処理中: {source_path.name} (ID: {article_id})")

            # 1. 画像URLの置換と事前チェック
            images_for_article = database.get_images_by_article_id(article_id)
            image_map = {Path(img['source_path']).name: img['blogger_url'] for img in images_for_article if img['blogger_url']}

            soup = BeautifulSoup(html_content, 'html.parser')

            # この記事に含まれるローカル画像タグをすべて見つける
            local_img_tags = [img for img in soup.find_all('img') if img.get('src') and not img.get('src').startswith(('http://', 'https://'))]
            
            # すべての画像がアップロード済みかチェック
            all_images_ready = True
            if local_img_tags:
                for img_tag in local_img_tags:
                    img_filename = Path(img_tag.get('src')).name
                    if img_filename not in image_map:
                        logger.warning(f"  -> スキップ: 記事(ID:{article_id})の画像 {img_filename} がまだアップロードされていません。")
                        all_images_ready = False
                        break # 1つでも見つからなければチェックを中断
            
            if not all_images_ready:
                skipped_count += 1
                continue # この記事の処理をスキップして次の記事へ

            # 画像パスを置換
            for img_tag in local_img_tags:
                img_filename = Path(img_tag.get('src')).name
                blogger_url = image_map[img_filename]

                # 画像サイズマッピング (標準サイズへの調整)
                try:
                    img_local_path = source_path.parent / img_tag.get('src')
                    if img_local_path.exists():
                        with Image.open(img_local_path) as img:
                            w, h = img.size
                        
                        new_w, new_h = w, h
                        # 横長 (Landscape) -> 幅640基準
                        if w > h:
                            if w > 640:
                                new_w = 640
                                new_h = int(h * (640 / w))
                        # 縦長 (Portrait) -> 高さ640基準
                        else:
                            if h > 640:
                                new_h = 640
                                new_w = int(w * (640 / h))
                        
                        img_tag['width'] = new_w
                        img_tag['height'] = new_h
                except Exception as e:
                    logger.warning(f"画像サイズ処理エラー: {e}")

                img_tag['src'] = blogger_url
                
                # 画像をリンクで囲む (Lightbox用)
                parent = img_tag.parent
                if parent.name != 'a':
                    new_a = soup.new_tag('a', href=blogger_url)
                    img_tag.wrap(new_a)
                
                logger.debug(f"  -> 画像リンク生成: <a href='{blogger_url}'><img src='{blogger_url}'></a>")
                logger.info(f"  -> 画像パス置換: {img_filename}")
            # 2. メタデータ抽出
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag and title_tag.get_text(strip=True) else source_path.stem

            search_tag = soup.find('search')
            # 空文字を除去してリスト化 (カンマ、読点などで分割)
            if search_tag:
                search_text = search_tag.get_text(strip=True)
                logger.debug(f"hoge: searchタグ内容: '{search_text}'")
                raw_labels = re.split(r'[,，、]', search_text)
                logger.debug(f"hoge: 分割直後のラベル: {raw_labels}")
                labels = [label.strip() for label in raw_labels if label and label.strip()]
            else:
                labels = []

            time_tag = soup.find('time')
            published_date = time_tag.get('datetime') if time_tag and time_tag.get('datetime') else datetime.now().strftime('%Y-%m-%d')
            published = f"{published_date}T00:00:00+09:00"

            location_data = None
            georss_tag = soup.find('georss')
            if georss_tag:
                name_tag = georss_tag.find('name')
                point_tag = georss_tag.find('point')
                if name_tag and point_tag:
                    coords = point_tag.get_text(strip=True).split()
                    if len(coords) == 2:
                        location_data = {
                            'name': name_tag.get_text(strip=True),
                            'lat': float(coords[0]),
                            'lng': float(coords[1])
                        }

            # 本文は<body>タグの中身
            body_tag = soup.find('body')
            content_to_upload = ''.join(str(child) for child in body_tag.children).strip() if body_tag else str(soup)
            
            # デバッグ: アップロードするコンテンツの先頭を表示して画像タグが含まれているか確認
            logger.debug(f"  -> Upload Content Preview: {content_to_upload[:200]}...")

            # 3. APIリクエストボディ作成
            post_body = {
                'title': title,
                'content': content_to_upload,
                'labels': labels,
                'published': published,
                'blog': {'id': BLOG_ID},
            }
            if location_data:
                post_body['location'] = location_data

            logger.info(f"  -> ラベル: {labels}")
            # 重複チェック (テストモード以外)
            if not TEST_MODE:
                existing_post_id = check_duplicate_title(service, BLOG_ID, title)
                if existing_post_id:
                    logger.warning(f"  -> 重複検出: 既に同じタイトルの記事が存在します (ID: {existing_post_id})")
                    database.set_uploaded(article_id, existing_post_id)
                    skipped_count += 1
                    continue

            # 4. アップロード実行
            logger.info(f"アップロード実行: '{title}'")
            if TEST_MODE:
                logger.warning("【テストモード】API呼び出しをスキップします")
                post_id = f"TEST_POST_ID_{article_id}"
            else:
                # API呼び出しのリトライ処理
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        inserted_post = service.posts().insert(blogId=BLOG_ID, body=post_body, isDraft=True).execute()
                        post_id = inserted_post['id']
                        break
                    except HttpError as e:
                        # レート制限 (403: User Rate Limit Exceeded, 429: Too Many Requests)
                        if e.resp.status in [403, 429]:
                            wait_time = (attempt + 1) * 10 # レート制限時は長めに待機
                            logger.warning(f"APIレート制限検出 (Status {e.resp.status}): {wait_time}秒待機して再試行します...")
                            time.sleep(wait_time)
                        elif attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 2
                            logger.warning(f"API HTTPエラー {e.resp.status} (試行 {attempt+1}/{max_retries}): {e} - {wait_time}秒後に再試行します")
                            time.sleep(wait_time)
                        else:
                            raise
                    except Exception as e:
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 2
                            logger.warning(f"APIエラー (試行 {attempt+1}/{max_retries}): {e} - {wait_time}秒後に再試行します")
                            time.sleep(wait_time)
                        else:
                            raise

            # 5. DB更新
            database.set_uploaded(article_id, post_id)
            logger.info(f"  -> 成功: Blogger Post ID = {post_id}")
            success_count += 1

        except Exception as e:
            error_msg = f"記事アップロード失敗: {e}"
            logger.error(f"失敗: {source_path.name} - {error_msg}", exc_info=True)
            database.update_status(article_id, 'error', error_message=error_msg)
            error_count += 1
        finally:
            time.sleep(DELAY_SECONDS)
            pbar.update()

    logger.info("--- 記事アップロードパイプライン完了 ---")
    logger.info(f"成功: {success_count}件, 失敗: {error_count}件, スキップ: {skipped_count}件")
    return success_count, error_count, skipped_count

if __name__ == '__main__':
    try:
        run_article_upload_pipeline()
    except Exception as e:
        logger.critical(f"予期せぬエラーが発生しました: {e}", exc_info=True)
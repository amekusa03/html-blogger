# -*- coding: utf-8 -*-
import logging
import sys
from pathlib import Path
from PIL import Image

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))

# 必要なモジュールをインポート
from config import get_config
from google_auth import get_blogger_service
from image_uploader import upload_image_to_blogger

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_image_upload_function():
    logger.info("=== 画像アップロード機能の集中検証を開始します ===")

    # 1. 設定の確認
    blog_id = get_config('UPLOADER', 'blog_id')
    if not blog_id:
        logger.error("エラー: config.ini (またはDB) に BLOG_ID が設定されていません。")
        return

    logger.info(f"使用するブログID: {blog_id}")

    # 2. Google認証
    try:
        service = get_blogger_service()
        if not service:
            logger.error("エラー: Google認証サービスを取得できませんでした。")
            return
        logger.info("Google認証: OK")
    except Exception as e:
        logger.error(f"エラー: Google認証中に例外が発生しました: {e}")
        return

    # 3. 検証用画像の生成
    image_path = Path(__file__).parent / 'verify_test_image.jpg'
    try:
        # 赤色の単色画像を作成
        img = Image.new('RGB', (640, 480), color=(255, 100, 100))
        img.save(image_path)
        logger.info(f"検証用画像を作成しました: {image_path.name}")
    except Exception as e:
        logger.error(f"エラー: 画像生成に失敗しました: {e}")
        return

    # 4. アップロード実行
    try:
        logger.info("アップロードを実行中... (Blogger API posts.insert)")
        # test_mode=False を指定して強制的にAPIを叩く
        url = upload_image_to_blogger(service, image_path, blog_id, test_mode=False)
        
        logger.info("-" * 40)
        if url and url.startswith("http"):
            logger.info("【検証結果: 成功】")
            logger.info(f"取得された画像URL: {url}")
            logger.info("※ このURLをブラウザで開き、画像が表示されるか確認してください。")
            logger.info("※ Bloggerの下書き一覧に 'Image Upload Temp...' という記事が残っているはずです。")
        else:
            logger.error("【検証結果: 失敗】")
            logger.error(f"有効なURLが取得できませんでした。戻り値: {url}")

    except Exception as e:
        logger.error("【検証結果: エラー発生】")
        logger.error(f"詳細: {e}")

    finally:
        # 後始末
        if image_path.exists():
            try:
                image_path.unlink()
            except:
                pass

if __name__ == '__main__':
    verify_image_upload_function()

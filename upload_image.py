# -*- coding: utf-8 -*-
"""upload_image.py
画像アップロード用モジュール
"""
import logging
import queue
import shutil
from pathlib import Path

from file_class import SmartFile
from parameter import config

logger = logging.getLogger(__name__)

# --- 設定 ---

# 入力元フォルダ
input_dir = config["upload_image"]["input_dir"].lstrip("./")
# アップロード先フォルダ
upload_dir = config["upload_image"]["upload_dir"].lstrip("./")
# 画像拡張子
image_extensions = config["common"]["image_extensions"]


def move_upload_file(queue_obj):
    """アップロード用に画像を準備する"""
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    count = 0
    # 2. input_dir内を探索
    # rglob('*') を使えばサブフォルダ内も探せます。直下だけなら glob('*')
    if Path(input_dir).resolve() == Path(upload_dir).resolve():
        logger.error(
            "エラー: input_dir と upload_dir が同じフォルダに設定されています。異なるフォルダを指定してください。"
        )
        return False

    for file_path in Path(input_dir).rglob("*"):
        # ファイルであり、かつ拡張子が指定のものに含まれるかチェック
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            dest_path = Path(upload_dir) / file_path.name
            # 3. コピー実行（メタデータも保持するcopy2を推奨）
            shutil.copy2(file_path, dest_path)
            count += 1

            smart_file = SmartFile(dest_path)
            smart_file.status = "⌛"
            smart_file.extensions = "image"
            smart_file.disp_path = dest_path.name
            queue_obj.put(smart_file)
    logger.info("%d 枚の画像を %s にアップロードしました。", count, upload_dir)
    return True


def is_resume():
    """upload_dir (投稿用一時フォルダ) にファイルがあれば、再起動（再開）と判定する"""
    if Path(upload_dir).exists():
        has_image = any(
            p.is_file() and p.suffix.lower() in image_extensions
            for p in Path(upload_dir).rglob("*")
        )
        if has_image:
            logger.info("再起動からの処理を開始します。(ファイルコピーをスキップ)")
            return True
    logger.debug("新規処理を開始します。ファイルを準備します。")
    return False


def run(queue_obj):
    """手動アップロード用に画像を準備する"""
    logger.info("画像アップロード準備開始: %s -> %s", input_dir, upload_dir)
    Path(upload_dir).mkdir(parents=True, exist_ok=True)

    if Path(input_dir).resolve() == Path(upload_dir).resolve():
        logger.error(
            "エラー: INPUT_DIR と UPLOAD_DIR が同じフォルダに設定されています。異なるフォルダを指定してください。"
        )
        return False

    # 新規処理の場合は、input_dir から upload_dir へファイルをコピーして準備する
    if not is_resume():
        logger.debug("新規処理を開始します。ファイルを準備します。")
        if not move_upload_file(queue_obj):
            return False

    # upload_dir 内のファイルを処理対象とする
    files_to_process = sorted(
        [
            p
            for p in Path(upload_dir).rglob("*")
            if p.is_file() and p.suffix.lower() in image_extensions
        ]
    )
    count = 0
    for src_path in files_to_process:
        smart_file = SmartFile(src_path)
        smart_file.status = "✓"  # ここではアップロード準備完了として✓を付ける
        smart_file.extensions = "image"
        smart_file.disp_path = smart_file.name
        queue_obj.put(smart_file)
        count += 1

    logger.info("%d 枚の画像を %s に準備しました。", count, upload_dir)
    return True


def rm():
    """アップロード用一時フォルダを削除する"""
    shutil.rmtree(upload_dir, ignore_errors=True)


# --- メイン処理 ---
if __name__ == "__main__":

    result_queue = queue.Queue()
    try:
        run(result_queue)
    except KeyboardInterrupt:
        logger.info("処理が中断されました。")
    except (IOError, OSError) as e:
        logger.critical("予期せぬエラーが発生しました: %s", e, exc_info=True)

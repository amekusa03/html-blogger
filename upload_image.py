# -*- coding: utf-8 -*-
import logging
import shutil
from logging import config, getLogger
from pathlib import Path

from json5 import load

from file_class import SmartFile
from parameter import config

# logging設定
with open("./data/log_config.json5", "r") as f:
    logging.config.dictConfig(load(f))
logger = getLogger(__name__)

# --- 設定 ---

# 入力元フォルダ
input_dir = config["upload_image"]["input_dir"].lstrip("./")
# アップロード先フォルダ
upload_dir = config["upload_image"]["upload_dir"].lstrip("./")
# 画像拡張子
image_extensions = config["common"]["image_extensions"]

def move_upload_file(result_queue):
    """アップロード用に画像を準備する"""
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    count = 0
    # 2. input_dir内を探索
    # rglob('*') を使えばサブフォルダ内も探せます。直下だけなら glob('*')
    if input_dir == upload_dir:
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
            result_queue.put(smart_file)
    logger.info(f"{count} 枚の画像を {upload_dir} にアップロードしました。")
    return True

def is_resume():
    # upload_dir (投稿用一時フォルダ) にファイルがあれば、再起動（再開）と判定する
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


def run(result_queue):
    """手動アップロード用に画像を準備する"""
    logger.info(f"画像アップロード準備開始: {input_dir} -> {upload_dir}")
    Path(upload_dir).mkdir(parents=True, exist_ok=True)

    if input_dir == upload_dir:
        logger.error(
            "エラー: INPUT_DIR と UPLOAD_DIR が同じフォルダに設定されています。異なるフォルダを指定してください。"
        )
        return False

    # 新規処理の場合は、input_dir から upload_dir へファイルをコピーして準備する
    if not is_resume():
        logger.debug("新規処理を開始します。ファイルを準備します。")
        if not move_upload_file(result_queue):
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
        smart_file.status = "✓"            # ここではアップロード準備完了として✓を付ける
        smart_file.extensions = "image"
        smart_file.disp_path = smart_file.name
        result_queue.put(smart_file)
        count += 1
        
    logger.info(f"{count} 枚の画像を {upload_dir} に準備しました。")
    return True





# def history(result_queue):
#     """手動アップロード用に画像を準備する"""
#     # Path(history_dir).mkdir(parents=True, exist_ok=True)
#     count = 0
#     # 2. INPUT_DIR内を探索
#     # rglob('*') を使えばサブフォルダ内も探せます。直下だけなら glob('*')
#     if upload_dir == history_dir:
#         logger.error(
#             "エラー: UPLOAD_DIR と HISTORY_DIR が同じフォルダに設定されています。異なるフォルダを指定してください。"
#         )
#         return False
#     # HTML内の画像リンクを収集
#     for file_path in Path(upload_dir).rglob("*"):
#         # ファイルであり、かつ拡張子が指定のものに含まれるかチェック
#         if file_path.is_file() and file_path.suffix.lower() in image_extensions:
#             dest_path = Path(history_dir) / file_path.name
#             # 3. コピー実行（メタデータも保持するcopy2を推奨）
#             shutil.copy2(file_path, dest_path)
#             smart_file = SmartFile(dest_path)
#             smart_file.status = "✔"
#             smart_file.extensions = "image"
#             smart_file.disp_path = smart_file.name
#             result_queue.put(smart_file)
#             count += 1

#     logger.info(f"{count} 枚の画像を {history_dir} にアップロードしました。")
#     return True


import queue

# --- メイン処理 ---
if __name__ == "__main__":

    result_queue = queue.Queue()
    try:
        run(result_queue)
    except KeyboardInterrupt:
        logger.info("処理が中断されました。")
    except Exception as e:
        logger.critical(f"予期せぬエラーが発生しました: {e}", exc_info=True)

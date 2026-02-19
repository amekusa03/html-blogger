# -*- coding: utf-8 -*-
import copy
import logging
import queue
import threading
from logging import getLogger

from json5 import load

import clean_html
import find_date
import find_keyword
import find_location

# 既存モジュールのインポート
import import_file
import link_html
import mod_image
import serial_file
import upload_art
import upload_image
from parameter import config

# from check_file import run as check_file_run, input_dir


# logging設定
with open("./data/log_config.json5", "r") as f:
    logging.config.dictConfig(load(f))
logger = getLogger(__name__)


def main_process(command_queue, result_queue):
    while True:
        try:
            command = command_queue.get(timeout=1)  # Wait for data
            if command is None:  # Exit signal
                break
            # Process the data (example: square the number)
            if command == "initial_process":
                # ここで初期処理を行う（処理一覧送信など）
                logger.info(process_def[command]["name"])
                for key in process_def.keys():  # GUIに処理一覧を送る
                    if key == "initial_process":  # mmemo queueの中も参照渡し
                        process_def[key]["status"] = "✔"
                    else:
                        process_def[key]["status"] = "⌛"
                    result_queue.put(process_def[key])
            if command == "check_resume":
                # ここで再開チェックを行う
                logger.info(process_def[command]["name"])
                resume = check_resume()
                if not resume:
                    process_def[command]["status"] = "✔"
                else:                    
                    process_def[command]["status"] = "♻"
                    result_queue.put(resume)
                result_queue.put(process_def[command])
            if command == "import_files":
                logger.info(process_def[command]["name"])
                process_def[command]["status"] = "✔"
                result_queue.put(process_def[command])  # GUIのみ
            if command == "check_files":
                logger.info(process_def[command]["name"])
                import_file.run(result_queue)
                upload_image.rm()  # アップロード用一時フォルダをクリーンアップ
                process_def[command]["status"] = "✔"
                result_queue.put(process_def[command])
            if command == "serialize_files":
                logger.info(process_def[command]["name"])
                serial_file.run(result_queue)
                process_def[command]["status"] = "✔"
                result_queue.put(process_def[command])
            if command == "clean_html":
                logger.info(process_def[command]["name"])
                clean_html.run(result_queue)
                process_def[command]["status"] = "✔"
                result_queue.put(process_def[command])
            if command == "find_keyword":
                logger.info(process_def[command]["name"])
                find_keyword.run(result_queue)
                process_def[command]["status"] = "✔"
                result_queue.put(process_def[command])
            if command == "find_location":
                logger.info(process_def[command]["name"])
                find_location.run(result_queue)
                process_def[command]["status"] = "✔"
                result_queue.put(process_def[command])
            if command == "find_date":
                logger.info(process_def[command]["name"])
                find_date.run(result_queue)
                process_def[command]["status"] = "✔"
                result_queue.put(process_def[command])
            if command == "mod_image":
                logger.info(process_def[command]["name"])
                mod_image.run(result_queue)
                process_def[command]["status"] = "✔"
                result_queue.put(process_def[command])
            if command == "upload_image":
                logger.info(process_def[command]["name"])
                upload_image.run(result_queue)
                process_def[command]["status"] = "✔"
                result_queue.put(process_def[command])
            # if command == "history_image":
            #     logger.info("画像アップロード履歴保存")

            #     result_queue.put("history_image")
            if command == "import_media_manager":
                logger.info(process_def[command]["name"])
                process_def[command]["status"] = "✔"
                result_queue.put(process_def[command])  # GUIのみ
            if command == "link_html":
                logger.info(process_def[command]["name"])
                result = link_html.run(result_queue)
                if result is False:
                    process_def[command]["status"] = "✖"
                    # エラー時は処理を中断（必要に応じてGUIへエラー通知を送る）
                    logger.error("HTMLリンク設定でエラーが発生しました。処理を中断します。")
                # リンクできなかった画像がある場合の判定
                if isinstance(result, list):
                    process_def[command]["status"] = "⚠"
                    logger.warning(f"リンク切れ画像があります: {len(result)}件")
                else:
                    process_def[command]["status"] = "✔"
                result_queue.put(process_def[command])  # GUIのみ
            if command == "upload_art":
                logger.info(process_def[command]["name"])
                result = upload_art.run(result_queue)
                if result is False:
                    process_def[command]["status"] = "✖"
                    # エラー時は処理を中断（必要に応じてGUIへエラー通知を送る）
                    logger.error("記事アップロードでエラーが発生しました。処理を中断します。")
                if isinstance(result, list):
                    process_def[command]["status"] = "⏸️"
                    logger.warning(f"投稿制限に達した記事があります: {len(result)}件")
                else:
                    process_def[command]["status"] = "✔"
                result_queue.put(process_def[command])
            if command == "closing":
                logger.info(process_def[command]["name"])
                process_def[command]["status"] = "✔"
                result_queue.put(process_def[command])  # GUIのみ
            if command is None:  # Exit signal
                break
            # Process the data (example: square the number)
            # result = data * data
            # result_queue.put(result)
        except queue.Empty:
            continue
        except Exception as e:
            result_queue.put(f"Error processing data: {e}")
            logger.error(f"エラー: プロセスエラー: {e}")


def check_resume():
    """再開チェック"""
    if upload_image.is_resume():
        process_def["upload_image"]["status"] = "🔁"
        return process_def["upload_image"]
    if upload_art.is_resume():
        process_def["upload_art"]["status"] = "🔁"
        return process_def["upload_art"]
    return None


def start_thread():
    """スレッドを開始する"""
    q = queue.Queue()
    thread = threading.Thread(target=main_process, args=(q, q))
    thread.start()
    return q, thread


process_def = {
    "initial_process": {
        "key": "initial_process",
        "name": "初期処理",
        "status": "⌛",
        "nextprocess": "check_resume",
    },
    "check_resume": {
        "key": "check_resume",
        "name": "再開チェック",
        "status": "⌛",
        "nextprocess": "import_files",
        "resumeimageprocess": "upload_image",
        "resumeartprocess": "upload_art",
    },
    "import_files": {
        "key": "import_files",
        "name": "ファイル取り込み",
        "status": "⌛",
        "nextprocess": "check_files",
    },
    "check_files": {
        "key": "check_files",
        "name": "ファイルチェック",
        "status": "⌛",
        "nextprocess": "serialize_files",
    },
    "serialize_files": {
        "key": "serialize_files",
        "name": "フォルダ除去、シリアル追加",
        "status": "⌛",
        "nextprocess": "clean_html",
    },
    "clean_html": {
        "key": "clean_html",
        "name": "タグ除去・メタデータ抽出",
        "status": "⌛",
        "nextprocess": "find_keyword",
    },
    "find_keyword": {
        "key": "find_keyword",
        "name": "キーワード自動抽出・注入",
        "status": "⌛",
        "nextprocess": "find_location",
    },
    "find_location": {
        "key": "find_location",
        "name": "地理タグ自動付与",
        "status": "⌛",
        "nextprocess": "find_date",
    },
    "find_date": {
        "key": "find_date",
        "name": "日付付与",
        "status": "⌛",
        "nextprocess": "mod_image",
    },
    "mod_image": {
        "key": "mod_image",
        "name": "画像編集・最適化",
        "status": "⌛",
        "nextprocess": "upload_image",
    },
    "upload_image": {
        "key": "upload_image",
        "name": "画像アップロード",
        "status": "⌛",
        "nextprocess": "import_media_manager",
        "resumeprocess": "upload_image",
    },
    "import_media_manager": {
        "key": "import_media_manager",
        "name": "メディアマネージャーダウンロード",
        "status": "⌛",
        "nextprocess": "link_html",
    },
    "link_html": {
        "key": "link_html",
        "name": "HTMLリンク設定",
        "status": "⌛",
        "nextprocess": "upload_art",
        "retryprocess": "upload_image",
    },
    "upload_art": {
        "key": "upload_art",
        "name": "記事アップロード",
        "status": "⌛",
        "nextprocess": "closing",
        "retryprocess": "upload_art",
        "resumeprocess": "upload_art",
    },
    "closing": {
        "key": "closing",
        "name": "終了",
        "status": "⌛",
        "nextprocess": "import_files",
    },
}

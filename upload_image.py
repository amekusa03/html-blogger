# -*- coding: utf-8 -*-
import os
import re      
from json5 import load    
from pathlib import Path
import xml.etree.ElementTree as ET
import shutil
import logging
from logging import config, getLogger
from parameter import config,update_serial,get_serial
from cons_progressber import ProgressBar
from file_class import SmartFile

# logging設定
with open('./data/log_config.json5', 'r') as f:
  logging.config.dictConfig(load(f)) 
logger = getLogger(__name__)

# --- 設定 ---

# 入力元フォルダ
input_dir = config['upload_image']['input_dir'].lstrip('./')
# アップロード先フォルダ
upload_dir = config['upload_image']['upload_dir'].lstrip('./')
# 履歴フォルダ
history_dir = config['upload_image']['history_dir'].lstrip('./')
# 画像拡張子
image_extensions = config['common']['image_extensions']

def run(result_queue):
    """手動アップロード用に画像を準備する"""
    shutil.rmtree(upload_dir, ignore_errors=True)
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    
    count = 0
    # 2. INPUT_DIR内を探索
    # rglob('*') を使えばサブフォルダ内も探せます。直下だけなら glob('*')
    if input_dir == upload_dir:
        logger.error("エラー: INPUT_DIR と UPLOAD_DIR が同じフォルダに設定されています。異なるフォルダを指定してください。")
        return False
    
    for file_path in Path(input_dir).rglob('*'):
        # ファイルであり、かつ拡張子が指定のものに含まれるかチェック
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            dest_path = Path(upload_dir) / file_path.name
            smart_file = SmartFile(file_path)
            # 3. コピー実行（メタデータも保持するcopy2を推奨）
            shutil.copy2(file_path, dest_path)
            smart_file = SmartFile(dest_path)
            smart_file.status = '⌛'
            smart_file.extensions = 'image'
            smart_file.disp_path = smart_file.name
            result_queue.put(smart_file)
            count += 1

    logger.info(f"{count} 枚の画像を {upload_dir} にアップロードしました。")
    return True   

def history(result_queue):
    """手動アップロード用に画像を準備する"""
    #Path(history_dir).mkdir(parents=True, exist_ok=True)
    count = 0
    # 2. INPUT_DIR内を探索
    # rglob('*') を使えばサブフォルダ内も探せます。直下だけなら glob('*')
    if upload_dir == history_dir:
        logger.error("エラー: UPLOAD_DIR と HISTORY_DIR が同じフォルダに設定されています。異なるフォルダを指定してください。")
        return False
    # HTML内の画像リンクを収集
    for file_path in Path(upload_dir).rglob('*'):
        # ファイルであり、かつ拡張子が指定のものに含まれるかチェック
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            dest_path = Path(history_dir) / file_path.name
            # 3. コピー実行（メタデータも保持するcopy2を推奨）
            shutil.copy2(file_path, dest_path)
            smart_file = SmartFile(dest_path)
            smart_file.status = '✔'
            smart_file.extensions = 'image'
            smart_file.disp_path = smart_file.name
            result_queue.put(smart_file)
            count += 1


    logger.info(f"{count} 枚の画像を {history_dir} にアップロードしました。")
    return True   

import queue

# --- メイン処理 ---
if __name__ == '__main__':
    
    result_queue=queue.Queue()
    try:
        run(result_queue)
    except KeyboardInterrupt:
        logger.info("処理が中断されました。")
    except Exception as e:
        logger.critical(f"予期せぬエラーが発生しました: {e}", exc_info=True)
# -*- coding: utf-8 -*-
import os
import re      
from json5 import load    
from pathlib import Path
import shutil
import logging
from logging import config, getLogger
from parameter import config
from file_class import SmartFile

# logging設定
with open('./data/log_config.json5', 'r') as f:
  logging.config.dictConfig(load(f)) 
logger = getLogger(__name__)

# --- 設定 ---
test_mode = config['common']['test_mode']
# 入力元フォルダ
input_dir = config['import_file']['input_dir']
# 出力先フォルダ
output_dir = config['import_file']['output_dir']
backup = config['import_file']['backup']
# バックアップフォルダ
backup_dir = config['import_file']['backup_dir']
image_extensions = config['common']['image_extensions']
html_extensions = config['common']['html_extensions']

def run(result_queue):
    shutil.rmtree(output_dir, ignore_errors=True)
    """INPUT_DIRからOUTPUT_DIRにファイルを取り込む"""
    for in_file in Path(input_dir).rglob('*'):
        logger.info(f"Importing: {Path(in_file)}")
        if in_file.is_file():
            src_file = import_files(in_file) # 画像またはHTMLファイルのみ対象
            result_queue.put(src_file)
    #削除
    if test_mode == 'false':
        shutil.rmtree(Path(input_dir), ignore_errors=True)
        Path(input_dir).mkdir(parents=True, exist_ok=True)  
    
    return True
def import_files(in_file):            
    """ファイルをINPUT_DIRからOUTPUT_DIRにコピー"""
    # フォルダがなければ作成 (exist_ok=Trueで既存フォルダエラーを回避)
    try:
        # ファイルをバックアップ
        if backup == 'true':
            os.makedirs(Path(backup_dir), exist_ok=True)
            backupfile = Path(backup_dir) / Path(in_file).parent.relative_to(input_dir) / in_file.name
            os.makedirs(Path(backupfile).parent, exist_ok=True)
            shutil.copy(in_file, backupfile)
        # 作業エリアにファイルをコピー
        to = SmartFile(Path(output_dir) / Path(in_file).parent.relative_to(input_dir) / in_file.name)
        os.makedirs(Path(to).parent, exist_ok=True)
        shutil.copy(in_file, to)
        files = SmartFile(to)
        files.disp_path = Path(files).parent.relative_to(output_dir) / files.name
        
        # まず全フォルダをチェック
        if files.suffix.lower() in image_extensions:
            files.extensions = 'image'
        elif files.suffix.lower() in html_extensions:
            files.extensions = 'html'
        else:
            files.status = '✘'
            files.extensions = 'other'
            logger.warning(f"警告: 対応していない拡張子のため取り込みスキップ: {files}")        

        files.status = '✓'    
    except Exception as e:
        files.status = '✘'
        logger.error(f"エラー: 取り込み失敗: {Path(output_dir) / files.name} - {e}")
        return files
    return files

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
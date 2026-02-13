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
        # 安全のため自動削除は無効化（必要に応じて有効化してください）
        # shutil.rmtree(Path(input_dir), ignore_errors=True)
        # Path(input_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"処理完了: 元ファイルは {input_dir} に残っています。")
    
    return True
def import_files(in_file):            
    """ファイルをINPUT_DIRからOUTPUT_DIRにコピー"""
    # フォルダがなければ作成 (exist_ok=Trueで既存フォルダエラーを回避)
    # 転送先パスを事前に計算し、SmartFileオブジェクトを初期化
    try:
        rel_path = Path(in_file).parent.relative_to(input_dir)
    except ValueError:
        rel_path = Path(".")
    
    dest_path = Path(output_dir) / rel_path / in_file.name
    files = SmartFile(dest_path)

    try:
        # ファイルをバックアップ
        if backup == 'true':
            os.makedirs(Path(backup_dir), exist_ok=True)
            backupfile = Path(backup_dir) / rel_path / in_file.name
            os.makedirs(Path(backupfile).parent, exist_ok=True)
            shutil.copy(in_file, backupfile)
            
        # 作業エリアにファイルをコピー
        os.makedirs(files.parent, exist_ok=True)
        shutil.copy(in_file, files)
        files.disp_path = rel_path / files.name
        
        # まず全フォルダをチェック
        if files.suffix.lower() in image_extensions:
            files.extensions = 'image'
            files.status = '✓'
        elif files.suffix.lower() in html_extensions:
            files.extensions = 'html'
            files.status = '✓'
        else:
            files.status = '✘'
            files.extensions = 'other'
            logger.warning(f"警告: 対応していない拡張子のため取り込みスキップ: {files}")        

    except Exception as e:
        files.status = '✘'
        logger.error(f"エラー: 取り込み失敗: {files} - {e}")
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
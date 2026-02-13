# -*- coding: utf-8 -*-
import queue
import threading
from json5 import load    
import logging
from logging import getLogger
from parameter import config

# 既存モジュールのインポート
import import_file
import serial_file
import clean_html
import find_keyword
import find_location
import find_date
import mod_image
import upload_image
import link_html
import upload_art
#from check_file import run as check_file_run, input_dir


# logging設定
with open('./data/log_config.json5', 'r') as f:
  logging.config.dictConfig(load(f)) 
logger = getLogger(__name__)


def main_process(command_queue, result_queue):
    while True:
        try:
            command = command_queue.get(timeout=1)  # Wait for data
            if command is None:  # Exit signal
                break
            # Process the data (example: square the number)
            if command == 'process_list':
                logger.info("プロセス一覧")
                result_queue.put(('process_list', process_def))
            if command == 'import_files':
                logger.info("ファイル取り込み")
                import_file.run(result_queue)
                result_queue.put('import_files' )
            if command == 'serialize_files':
                logger.info("ファイルシリアライズ")
                serial_file.run(result_queue)
                result_queue.put('serialize_files' )                 
            if command == 'clean_html':
                logger.info("HTMLクリーンアップ")
                clean_html.run(result_queue)
                result_queue.put('clean_html')
            if command == 'find_keyword':
                logger.info("キーワード注入")
                find_keyword.run(result_queue)      
                result_queue.put('find_keyword')
            if command == 'find_location':
                logger.info("位置情報付与")
                find_location.run(result_queue)
                result_queue.put('find_location')
            if command == 'find_date':
                logger.info("日付付与")
                find_date.run(result_queue)
                result_queue.put('find_date')                 
            if command == 'mod_image':
                logger.info("画像編集")
                mod_image.run(result_queue)
                result_queue.put('mod_image')
            if command == 'upload_image':
                logger.info("画像アップロード準備")
                upload_image.run(result_queue)
                result_queue.put('upload_image')
            if command == 'history_image':
                logger.info("画像アップロード履歴保存")
                upload_image.history(result_queue)
                result_queue.put('history_image')
            if command == 'import_media_manager':
                logger.info("メディアマネージャーダウンロード")
                result_queue.put('import_media_manager') # GUIのみ
            if command == 'link_html':
                logger.info("HTMLリンク設定")
                link_html.run(result_queue)
                result_queue.put('link_html')
            if command == 'upload_art':
                logger.info("記事アップロード")
                upload_art.run(result_queue)
                result_queue.put('upload_art')
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
def start_thread():
    """スレッドを開始する"""
    q = queue.Queue()
    thread = threading.Thread(target=main_process, args=(q, q))
    thread.start()
    return q, thread            
process_def = {
    'import_files': {
        'name': "ファイルチェック", 
        'status': '⌛', 
        'nextprocess': 'serialize_files'
    },
    'serialize_files': {
        'name': "フォルダ除去、シリアル追加", 
        'status': '⌛', 
        'nextprocess': 'clean_html'
    },
    'clean_html': {
        'name': "タグ除去・メタデータ抽出", 
        'status': '⌛', 
        'nextprocess': 'find_keyword'
    },
    'find_keyword': {
        'name': "キーワード自動抽出・注入", 
        'status': '⌛', 
        'nextprocess': 'find_location'
    },
    'find_location': {
        'name': "地理タグ自動付与", 
        'status': '⌛', 
        'nextprocess': 'find_date'
    },
    'find_date': {
        'name': "日付付与", 
        'status': '⌛', 
        'nextprocess': 'mod_image'
    },
    'mod_image': {
        'name': "画像編集・最適化", 
        'status': '⌛', 
        'nextprocess': 'upload_image'
    },
    'upload_image': {
        'name': "画像アップロード(準備)", 
        'status': '⌛', 
        'nextprocess': 'history_image'
    },
    'history_image': {
        'name': "画像アップロード(完了)", 
        'status': '⌛', 
        'nextprocess': 'import_media_manager'
    },
    'import_media_manager': {
        'name': "メディアマネージャーダウンロード", 
        'status': '⌛', 
        'nextprocess': 'link_html'
    },
    'link_html': {
        'name': "HTMLリンク設定", 
        'status': '⌛', 
        'nextprocess': 'upload_art'
    },
    'upload_art': {
        'name': "記事アップロード", 
        'status': '⌛', 
        'nextprocess': 'import_files'
    }
}
    

# coding: utf-8
import os
import sys
import subprocess
import logging
from logging.handlers import RotatingFileHandler
import database

# --- logging設定 ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('config.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
logger.addHandler(logging.StreamHandler())

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.ini')

def get_config(section, key, default=None):
    """
    設定値を取得する。
    config.ini ではなく database.py 経由で DB から取得する。
    """
    value = database.get_config_value(section, key)
    
    if value is not None:
        return value
    
    # DBに見つからない場合はデフォルト値を返す
    logger.warning(f'[{section}]->[{key}] がDBに見つかりません。デフォルト値 "{default}" を使用します。')
    return default

def open_file_with_default_app(filepath):
    """ファイルパスを受け取り、OSの標準アプリで開く関数"""
    if sys.platform == 'win32': # Windows
        os.startfile(filepath)
    elif sys.platform == 'darwin': # macOS
        subprocess.call(['open', filepath])
    elif sys.platform.startswith('linux'): # Linux
        subprocess.call(['xdg-open', filepath])
    else:
        logger.error(f"未対応のOS: {sys.platform}")

def open_keywords_app():
    """keywords.xml を標準アプリで開く"""
    xml_path = os.path.join(SCRIPT_DIR, get_config('ADD_KEYWORDS', 'XML_FILE', 'keywords.xml'))
    if os.path.exists(xml_path):
        open_file_with_default_app(xml_path)
    else:
        logger.error(f'{xml_path} が見つかりません。')

def open_config_file():
    """config.ini を標準アプリで開く"""
    if os.path.exists(CONFIG_FILE):
        open_file_with_default_app(CONFIG_FILE)
    else:
        logger.error(f'{CONFIG_FILE} が見つかりません。') 
        
def open_folder(path):
    """指定フォルダをファイルマネージャで開く"""
    abs_path = os.path.abspath(path)
    if os.path.exists(abs_path) and os.path.isdir(abs_path):
        open_file_with_default_app(abs_path)
    else:
        logger.error(f'{abs_path} が見つかりません。')
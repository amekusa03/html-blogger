# coding: utf-8
import os
import sys
import datetime
from datetime import datetime
import json5
import subprocess
from pathlib import Path
from logging import getLogger
import logging.config

with open('./data/log_config.json5', 'r') as f:
    log_conf = json5.load(f)

# 初期設定ファイル読み込み
# 使い方　config['SECTION']['KEY']
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
config_json_path = os.path.join(SCRIPT_DIR, './data/config.json5') 
with open(config_json_path, 'r', encoding='utf-8') as f:
    # JSON5ファイルを読み込んで辞書に変換
    config = json5.load(f)

# 初期設定ファイル書き込み
def save_config():
    with open(config_json_path, 'w', encoding='utf-8') as f:
        # JSON5ファイルを書き込んで辞書に変換
        json5.dump(config, f) 



# --- logging設定 ---
# ファイル名をタイムスタンプで作成
log_filename = '../data/logs/{}.logs'.format(datetime.now().strftime("%Y%m%d%H%M%S"))
 # ログ保存先のディレクトリを作成（存在しない場合）
os.makedirs(os.path.dirname(log_filename), exist_ok=True)
log_conf["handlers"]["fileHandler"]["filename"] = log_filename
# パラメータが設定されていればレベルをINFOからDEBUGに置換
log_conf["handlers"]["fileHandler"]["level"] = "DEBUG"
logging.config.dictConfig(log_conf)

# 共通関数
logger = getLogger(__name__)       
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
    xml_path = os.path.abspath(config['find_keyword']['keywords_xml_file'])
    if os.path.exists(xml_path):
        open_file_with_default_app(xml_path)
    else:
        logger.error(f'{xml_path} が見つかりません。')

def open_georss_file():
    """location.xml を標準アプリで開く"""
    xml_path = os.path.abspath(config['find_location']['location_xml_file'])
    if os.path.exists(xml_path):
        open_file_with_default_app(xml_path)
    else:
        logger.error(f'{xml_path} が見つかりません。')

def open_config_file():
    """config.json5 を標準アプリで開く"""
    if os.path.exists(config_json_path):
        open_file_with_default_app(config_json_path)
    else:
        logger.error(f'{config_json_path} が見つかりません。') 
        
def open_folder(path):
    """指定フォルダをファイルマネージャで開く"""
    abs_path = os.path.abspath(path)
    if os.path.exists(abs_path) and os.path.isdir(abs_path):
        open_file_with_default_app(abs_path)
    else:
        logger.error(f'{abs_path} が見つかりません。')


serial = {
    "hex": "0001",
}

serial_json_path = os.path.join(SCRIPT_DIR, './data/serial.json5') 
def load_serial():
    with open(serial_json_path, 'r', encoding='utf-8') as f:
        # JSON5ファイルを読み込んで辞書に変換
        serial = json5.load(f)
    return serial

def save_serial():
    with open(serial_json_path, 'w', encoding='utf-8') as f:
        # JSON5ファイルを書き込んで辞書に変換
        json5.dump(serial, f)
    return serial


def _get_serial_counter():
    """serialから現在のカウンター値を読み込む（16進4桁）"""
    return load_serial()['hex'] 

def get_serial():
    """serialから現在のカウンター値を読み込む（16進4桁）"""
    counter_hex = _get_serial_counter()
    if counter_hex:
        return counter_hex
    else:
        update_serial(reset=True)
    counter_hex = _get_serial_counter()
    return counter_hex

test_mode = config['common']['test_mode']

def update_serial(reset=False):
    """次回用のカウンター値をserialに保存（16進4桁）"""
    current_hex = load_serial()['hex']
    counter = int(current_hex, 16)
    if test_mode == 'false':
        counter += 1
    if counter > 0xFFFF or reset:
        counter = 1  # 16進4桁を超えたら1にリセット
    serial_data = {"hex": f"{counter:04x}"}
    try:
        with open(serial_json_path, 'w', encoding='utf-8') as f:
            json5.dump(serial_data, f)
    except IOError as e:
        logger.warning(f"シリアルの保存に失敗しました: {e}")
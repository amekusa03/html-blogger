# coding: utf-8
"""parameter.py
共通の定数や関数を定義するモジュール
"""
import os
import subprocess
import sys
from datetime import datetime
from logging import getLogger
from pathlib import Path

import json5

# 初期設定ファイル読み込み
# 使い方　config['SECTION']['KEY']
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_JSON_PATH = os.path.join(SCRIPT_DIR, "./data/config.json5")
with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
    # JSON5ファイルを読み込んで辞書に変換
    config = json5.load(f)


# 初期設定ファイル書き込み
def save_config():
    """現在のconfigオブジェクトをファイルに保存する"""
    with open(CONFIG_JSON_PATH, "w", encoding="utf-8") as file:
        # JSON5ファイルを書き込んで辞書に変換
        json5.dump(config, file, indent=4, quote_keys=True)


# 共通関数
logger = getLogger(__name__)


def open_file_with_default_app(filepath):
    """ファイルパスを受け取り、OSの標準アプリで開く関数"""
    filepath_str = str(filepath)
    try:
        if sys.platform == "win32":  # Windows
            os.startfile(filepath_str)
        elif sys.platform == "darwin":  # macOS
            subprocess.run(["open", filepath_str], check=True)
        elif sys.platform.startswith("linux"):  # Linux
            subprocess.run(["xdg-open", filepath_str], check=True)
        else:
            logger.error("未対応のOS: %s", sys.platform)
            return False
        return True
    except FileNotFoundError:
        logger.error(
            "コマンドが見つかりません。'%s' を開けませんでした。", filepath_str
        )
        return False
    except subprocess.CalledProcessError as e:
        logger.error("ファイルを開けませんでした: %s - %s", filepath_str, e)
        return False
    except OSError as e:
        logger.error(
            "予期せぬエラーでファイルを開けませんでした: %s - %s",
            filepath_str,
            e,
            exc_info=True,
        )
        return False


def open_keywords_app():
    """keywords.xml を標準アプリで開く"""
    xml_path = Path(config["find_keyword"]["keywords_xml_file"]).resolve()
    if xml_path.exists():
        open_file_with_default_app(xml_path)
    else:
        logger.error("%s が見つかりません。", xml_path)


def open_georss_file():
    """location.xml を標準アプリで開く"""
    xml_path = Path(config["find_location"]["location_xml_file"]).resolve()
    if xml_path.exists():
        open_file_with_default_app(xml_path)
    else:
        logger.error("%s が見つかりません。", xml_path)


def open_config_file():
    """config.json5 を標準アプリで開く"""
    if os.path.exists(CONFIG_JSON_PATH):
        open_file_with_default_app(CONFIG_JSON_PATH)
    else:
        logger.error("%s が見つかりません。", CONFIG_JSON_PATH)


def open_folder(path):
    """指定フォルダをファイルマネージャで開く"""
    abs_path = os.path.abspath(path)
    if os.path.exists(abs_path) and os.path.isdir(abs_path):
        open_file_with_default_app(abs_path)
    else:
        logger.error("%s が見つかりません。", abs_path)


def to_bool(value):
    """文字列や数値などを柔軟にbool値に変換する"""
    if isinstance(value, str):
        return value.lower() in ("true", "1", "t", "y", "yes", "on")
    return bool(value)


SERIAL_JSON_PATH = os.path.join(SCRIPT_DIR, "./data/serial.json5")


def load_serial():
    """シリアル番号ファイルを読み込む"""
    try:
        with open(SERIAL_JSON_PATH, "r", encoding="utf-8") as file:
            return json5.load(file)
    except (FileNotFoundError, ValueError):
        # ファイルがない、または不正な場合は初期値を返す
        return {"hex": "0001"}


def save_serial(serial):
    """シリアル番号をファイルに保存する"""
    with open(SERIAL_JSON_PATH, "w", encoding="utf-8") as file:
        json5.dump(serial, file, indent=4, quote_keys=True)


def get_serial():
    """serialから現在のカウンター値を読み込む（16進4桁）"""
    serial_data = load_serial()
    return serial_data.get("hex", "0001")


test_mode = to_bool(config["common"]["test_mode"])


def update_serial(reset=False):
    """
    次回用のカウンター値をserial.json5に保存（16進4桁）。
    test_modeがTrueの場合はカウンターをインクリメントしない。
    """
    serial_data = load_serial()
    current_hex = serial_data.get("hex", "0000")
    counter = int(current_hex, 16)

    if reset or counter >= 0xFFFF:
        counter = 1
    elif not test_mode:
        counter += 1

    new_serial_data = {"hex": f"{counter:04x}"}
    save_serial(new_serial_data)

# -*- coding: utf-8 -*-
"""
serializer.py
workフォルダから画像とHTMLを読み込み、
カウンター＋フォルダ名＋ファイル名の形式でserializationフォルダに保存する
HTML内の画像パスも同時に更新する
カウンター管理はこのスクリプトのみが担当
"""

import logging
import os
import queue
import re
import shutil
from pathlib import Path

from file_class import SmartFile
from parameter import config, get_serial, update_serial

logger = logging.getLogger(__name__)
# --- 設定 ---

# 入力フォルダ
input_dir = Path(config["serializer"]["input_dir"].lstrip("./")).resolve()
# シリアライズフォルダ
serialization_dir = Path(config["serializer"]["serialization_dir"].lstrip("./")).resolve()
# 出力フォルダ
output_dir = Path(config["serializer"]["output_dir"].lstrip("./")).resolve() 

image_extensions = config["common"]["image_extensions"]
html_extensions = config["common"]["html_extensions"]


def run(queue_obj):
    """INPUT_DIR内のファイルをシリアライズしてSERIALIZATION_DIRに保存する"""
    logger.info("シリアライズ処理開始: %s", input_dir)
    update_serial()  # シリアル番号更新

    # 1. 作業用ディレクトリ(SERIALIZATION_DIR)の初期化
    if serialization_dir.exists():
        shutil.rmtree(serialization_dir)
    serialization_dir.mkdir(exist_ok=True)

    # 2. ファイル処理
    all_files = sorted(input_dir.rglob("*"))

    # シリアル番号プレフィックスを取得（全ファイルで共通）
    serial_prefix = get_serial()

    for path in all_files:
        if not path.is_file():
            continue

        src_file = SmartFile(path)
        try:
            processed_file = process_file(src_file, serial_prefix)
            if processed_file:
                queue_obj.put(processed_file)
        except (IOError, OSError) as e:
            logger.error("ファイル処理エラー: %s - %s", path, e, exc_info=True)
            src_file.status = "✘"
            queue_obj.put(src_file)

    # 3. 出力ディレクトリへの反映
    finalize_output(serialization_dir, output_dir)
    logger.info("シリアライズ完了")


def get_serialized_name(path, serial_prefix):
    """パスをフラットなシリアル名に変換する"""
    try:
        relative = path.relative_to(input_dir)
    except ValueError:
        # input_dir外のパスの場合（通常は発生しないはずだが安全策）
        relative = Path(path.name)

    flat_name = "".join(relative.parts)
    return f"{serial_prefix}{flat_name}"


def process_file(src_file, serial_prefix):
    """個別のファイルを処理する"""
    new_name = get_serialized_name(src_file, serial_prefix)
    dest_path = serialization_dir / new_name

    # SmartFile作成
    dest_smart_file = SmartFile(dest_path)
    # GUI連携用: 元の相対パスを保存
    try:
        dest_smart_file.old_name = str(src_file.relative_to(input_dir))
    except ValueError:
        dest_smart_file.old_name = src_file.name

    if src_file.suffix.lower() in html_extensions:
        return process_html(src_file, dest_smart_file, serial_prefix)
    elif src_file.suffix.lower() in image_extensions:
        return process_image(src_file, dest_smart_file)

    return None


def process_html(src_file, dest_smart_file, serial_prefix):
    """HTMLファイルのリンクを書き換えて保存"""
    try:
        content = src_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning("エンコーディングエラー、スキップ: %s", src_file.name)
        dest_smart_file.status = "✘"
        return dest_smart_file

    def replace_link(match):
        original_src = match.group(1)
        # 外部リンク等は除外（簡易判定）
        if original_src.startswith(("http://", "https://", "//", "data:")):
            return match.group(0)

        # HTMLファイルからの相対パスを絶対パスに変換して計算
        html_dir = src_file.parent
        link_path = (html_dir / original_src).resolve()

        try:
            # リンク先の新しい名前を計算
            new_link_name = get_serialized_name(link_path, serial_prefix)
            logger.debug("  Rewriting link: %s -> %s", original_src, new_link_name)
            return f'src="{new_link_name}"'
        except ValueError:
            # input_dir 外へのリンクなどはそのままにする
            return match.group(0)

    # imgタグのsrcを置換
    new_content = re.sub(r'src="([^"]+)"', replace_link, content)

    dest_smart_file.write_text(new_content, encoding="utf-8")
    dest_smart_file.extensions = "html"
    dest_smart_file.disp_path = dest_smart_file.name
    dest_smart_file.status = "✓"
    logger.info("[HTML] %s -> %s (リンク更新済)", src_file.name, dest_smart_file.name)

    return dest_smart_file


def process_image(src_file, dest_smart_file):
    """画像ファイルを移動"""
    shutil.move(src_file, dest_smart_file)

    dest_smart_file.extensions = "image"
    dest_smart_file.disp_path = dest_smart_file.name
    dest_smart_file.status = "✓"
    logger.info("[FILE] %s -> %s", src_file.name, dest_smart_file.name)
    return dest_smart_file


def finalize_output(src_dir, dest_dir):
    """出力ディレクトリを更新"""
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)

    try:
        shutil.copytree(src_dir, dest_dir)
        logger.info("コピー: %s -> %s", src_dir, dest_dir)
    except (IOError, OSError) as e:
        logger.error(
            "エラー: ファイルのコピーに失敗しました: %s -> %s (%s)",
            src_dir,
            dest_dir,
            e,
            exc_info=True,
        )


# --- メイン処理 ---
if __name__ == "__main__":
    result_queue = queue.Queue()
    try:
        run(result_queue)
    except KeyboardInterrupt:
        logger.info("処理が中断されました。")
    except (IOError, OSError) as e:
        logger.critical("予期せぬエラーが発生しました: %s", e, exc_info=True)

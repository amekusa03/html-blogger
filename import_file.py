# -*- coding: utf-8 -*-
import logging
import os
import shutil
from datetime import datetime
from logging import config, getLogger
from pathlib import Path

from bs4 import BeautifulSoup
from json5 import load
from PIL import Image

from file_class import SmartFile
from parameter import config, to_bool

# logging設定
with open("./data/log_config.json5", "r") as f:
    logging.config.dictConfig(load(f))
logger = getLogger(__name__)

# --- 設定 ---
backup_enabled = to_bool(config["import_file"]["backup"])
# 入力元フォルダ
input_dir = config["import_file"]["input_dir"]
# 出力先フォルダ
output_dir = config["import_file"]["output_dir"]
# バックアップフォルダ
backup_dir = config["import_file"]["backup_dir"]
image_extensions = config["common"]["image_extensions"]
html_extensions = config["common"]["html_extensions"]


def run(result_queue):
    logger.info(f"ファイル取り込み開始: {input_dir} -> {output_dir}")
    # workフォルダをクリーンアップしてから処理を開始する
    shutil.rmtree(output_dir, ignore_errors=True)

    input_path = Path(input_dir)
    if not input_path.exists():
        logger.warning(f"入力フォルダが見つかりません: {input_dir}")
        return True

    # input_dir 内のファイルを処理対象とする
    files_to_process = sorted([p for p in input_path.rglob("*") if p.is_file()])

    if not files_to_process:
        logger.info("取り込み対象のファイルが見つかりません。")
        return True

    for in_file in files_to_process:
        logger.info(f"Importing: {in_file}")
        imported_file = import_file(in_file)
        result_queue.put(imported_file)

    return True


def import_file(in_file_path: Path):
    """単一のファイルを検証し、作業ディレクトリに移動する"""
    smart_file = SmartFile(in_file_path)
    try:
        rel_path = in_file_path.parent.relative_to(input_dir)
    except ValueError:
        rel_path = Path(".")

    smart_file.disp_path = rel_path / in_file_path.name

    try:
        # --- ファイル検証 ---
        if smart_file.suffix.lower() in image_extensions:
            try:
                with Image.open(in_file_path) as img:
                    img.verify()
                smart_file.extensions = "image"
                smart_file.status = "✓"
            except Exception as e:
                logger.warning(
                    f"警告: 画像ファイルとして開けません: {in_file_path} - {e}"
                )
                smart_file.status = "✘"
                smart_file.extensions = "other"
                return smart_file
        elif smart_file.suffix.lower() in html_extensions:
            try:
                content = None
                for encoding in ["utf-8", "cp932", "shift_jis"]:
                    try:
                        content = in_file_path.read_text(encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                if content is None:
                    raise ValueError("適切なエンコーディングが見つかりません。")
                BeautifulSoup(content, "html.parser")
                smart_file.extensions = "html"
                smart_file.status = "✓"
            except Exception as e:
                logger.warning(
                    f"警告: HTMLファイルとして解析できません: {in_file_path} - {e}"
                )
                smart_file.status = "✘"
                smart_file.extensions = "other"
                return smart_file
        else:
            smart_file.status = "✘"
            smart_file.extensions = "other"
            logger.warning(
                f"警告: 対応していない拡張子のため取り込みスキップ: {smart_file}"
            )
            return smart_file

        # --- ファイル操作 ---
        # 1. バックアップ
        if backup_enabled:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backup_path = Path(backup_dir) / timestamp
            target_backup_dir = backup_path / rel_path
            target_backup_dir.mkdir(parents=True, exist_ok=True)
            backup_file_path = target_backup_dir / in_file_path.name
            shutil.copy2(in_file_path, backup_file_path)
            logger.debug(f"バックアップ作成: {backup_file_path}")

        # 2. 作業エリアにファイルを移動
        dest_path = Path(output_dir) / rel_path / in_file_path.name
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        moved_path_str = shutil.move(in_file_path, dest_path)
        moved_path = Path(moved_path_str)
        logger.info(f"移動: {in_file_path} -> {moved_path}")

        # 3. 移動元のフォルダが空になったら削除
        src_parent = in_file_path.parent
        try:
            # input_dir 自体は削除しない
            if (
                src_parent.is_dir()
                and not any(src_parent.iterdir())
                and src_parent.resolve() != Path(input_dir).resolve()
            ):
                src_parent.rmdir()
                logger.info(f"空になったフォルダを削除しました: {src_parent}")
        except OSError as e:
            logger.debug(
                f"フォルダ削除失敗（空でない可能性があります）: {src_parent} - {e}"
            )

        # 4. 移動後のパスで新しいSmartFileオブジェクトを作成して返す
        final_smart_file = SmartFile(moved_path)
        final_smart_file.status = smart_file.status
        final_smart_file.extensions = smart_file.extensions
        final_smart_file.disp_path = smart_file.disp_path
        return final_smart_file

    except Exception as e:
        smart_file.status = "✘"
        logger.error(
            f"エラー: ファイル操作中にエラーが発生しました: {smart_file} - {e}",
            exc_info=True,
        )
        return smart_file


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

# -*- coding: utf-8 -*-
"""import_media_manager.py
メディアマネージャーフォルダをクリーンアップして再作成する
"""
import logging
import shutil
from pathlib import Path
from parameter import config

logger = logging.getLogger(__name__)
# --- 設定 ---

# メディアマネージャーフォルダ
media_manager_dir = config["link_html"]["media_manager_dir"].lstrip("./")

def run():
    """メディアマネージャーフォルダをクリーンアップして再作成する"""
    shutil.rmtree(media_manager_dir, ignore_errors=True)
    media_manager_path = Path(media_manager_dir)
    media_manager_path.mkdir(parents=True, exist_ok=True)
    logger.info("メディアマネージャーのクリーンアップと再作成: %s", media_manager_dir)
    return True

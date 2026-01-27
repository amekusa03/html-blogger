# -*- coding: utf-8 -*-
"""
delete_ready_upload.py
ready_uploadフォルダ内を全て削除する
"""

import os
import shutil
import logging
from pathlib import Path
from config import get_config

# --- logging設定 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('delete_ready_upload.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
# ready_uploadフォルダのパス
READY_UPLOAD_DIR = SCRIPT_DIR / get_config('READY_UPLOAD', 'OUTPUT_DIR', './ready_upload').lstrip('./')

def delete_ready_upload():
    """ready_uploadフォルダ内のすべてのファイルとサブフォルダを削除"""
    
    if not READY_UPLOAD_DIR.exists():
        logger.warning(f"フォルダが存在しません: {READY_UPLOAD_DIR}")
        return
    
    delete_count = 0
    
    # フォルダ内のすべてのファイルとサブフォルダを削除
    for item in READY_UPLOAD_DIR.iterdir():
        try:
            if item.is_file():
                item.unlink()
                delete_count += 1
            elif item.is_dir():
                shutil.rmtree(item)
                delete_count += 1
        except Exception as e:
            logger.error(f"削除失敗: {item.name} - {e}", exc_info=True)
    
    logger.info(f"完了: ready_upload削除{delete_count}個")

if __name__ == '__main__':
    delete_ready_upload()

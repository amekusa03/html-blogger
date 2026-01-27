# -*- coding: utf-8 -*-
"""
html_preparer.py
serializationフォルダからHTMLファイルのみをready_uploadにコピー
（カウンター式ネーミング済み）
"""

import os
import shutil
from pathlib import Path
from config import get_config
from utils import copy_files_by_extension

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
# 入力元フォルダ（serialization - カウンター式ネーミング済み）
SOURCE_DIR = SCRIPT_DIR / 'serialization'
# 出力先フォルダ（ready_upload）
OUTPUT_DIR = SCRIPT_DIR / get_config('READY_UPLOAD', 'OUTPUT_DIR', './ready_upload').lstrip('./')

def prepare_html_files():
    """serializationフォルダからHTMLファイルのみをready_uploadにコピー"""
    copy_files_by_extension(
        source_dir=SOURCE_DIR,
        output_dir=OUTPUT_DIR,
        extensions=('.html', '.htm'),
        file_type_name='HTMLファイル'
    )

if __name__ == '__main__':
    prepare_html_files()

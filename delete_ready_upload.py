# -*- coding: utf-8 -*-
"""
delete_ready_upload.py
ready_uploadフォルダ内を全て削除する
"""

import os
import shutil
from pathlib import Path
from config import get_config

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
# ready_uploadフォルダのパス
READY_UPLOAD_DIR = SCRIPT_DIR / get_config('READY_UPLOAD', 'OUTPUT_DIR', './ready_upload').lstrip('./')

def delete_ready_upload():
    """ready_uploadフォルダ内のすべてのファイルとサブフォルダを削除"""
    
    if not READY_UPLOAD_DIR.exists():
        print(f"フォルダが存在しません: {READY_UPLOAD_DIR}")
        return
    
    print(f"ready_uploadフォルダの削除を開始します: {READY_UPLOAD_DIR}")
    
    delete_count = 0
    
    # フォルダ内のすべてのファイルとサブフォルダを削除
    for item in READY_UPLOAD_DIR.iterdir():
        try:
            if item.is_file():
                item.unlink()
                delete_count += 1
                print(f"削除しました: {item.name}")
            elif item.is_dir():
                shutil.rmtree(item)
                delete_count += 1
                print(f"削除しました (フォルダ): {item.name}")
        except Exception as e:
            print(f"エラー: {item.name} の削除に失敗しました。 {e}")
    
    print("-" * 30)
    print(f"完了しました。合計 {delete_count} 個のアイテムを削除しました。")

if __name__ == '__main__':
    delete_ready_upload()

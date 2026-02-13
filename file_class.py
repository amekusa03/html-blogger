from pathlib import Path
import os
import shutil
import logging
from logging import config, getLogger
from parameter import config
from json5 import load    

# logging設定
with open('./data/log_config.json5', 'r') as f:
  logging.config.dictConfig(load(f)) 
logger = getLogger(__name__)
# --- 設定 ---

class SmartFile:
    def __init__(self, path_str):
        self._path = Path(path_str)
        self.status = "⌛"
        self.extensions = ['image', 'html', 'other']
        self.disp_path = None
        self.old_name = None

    def __getattr__(self, name):
        # is_file, exists, name などをPathクラスから引き継ぐ
        return getattr(self._path, name)

    def __fspath__(self):
        return os.fspath(self._path)

    def __str__(self):
        return str(self._path)

    def __copy__(self):
        cls = self.__class__
        result = cls.__new__(cls)
        result.__dict__.update(self.__dict__)
        return result

    def read_text(self, *args, **kwargs):
        return self._path.read_text(*args, **kwargs)

    def write_text(self, data, *args, **kwargs):
        return self._path.write_text(data, *args, **kwargs)

    def remove(self):
        """ファイルを安全に削除し、ステータスを更新する"""
        if self.exists():
            if self.is_file():
                self._path.unlink() # 実際の削除処理
                self.status = "🗑️ 削除済み"
                logger.info(f"ファイル {self.name} を削除しました。")
            elif self.is_dir():
                # ディレクトリを削除する場合は rmdir (中身が空である必要あり)
                self._path.rmdir()
                self.status = "🗑️ ディレクトリ削除済み"
                logger.info(f"ディレクトリ {self.name} を削除しました。")
        else:
            logger.error("エラー: 削除対象が存在しません。")

class SmartHtml:
    def __init__(self, path_str):
        self._path = Path(path_str)
        self.status = "⌛"
        self.extensions = ['image', 'html', 'other']
        self.disp_path = None
        self.process = []


# # --- 実行例 ---
# file = SmartFile("temp_data.txt")

# # exists() や is_file() は __getattr__ 経由で動作
# if file.exists():
#     file.remove()
#     print(f"現在のステータス: {file.status}")
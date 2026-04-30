# -*- coding: utf-8 -*-
"""file_class.py
Pathクラスをラップし、処理状態や表示用の属性を追加したクラス
"""
import logging
import os
from pathlib import Path

import parameter

logger = logging.getLogger(__name__)


class SmartFile:
    """Pathクラスをラップし、処理状態や表示用の属性を追加したクラス"""

    def __init__(self, path_str):
        self._path = Path(path_str)
        self.status = "⌛"
        self.extensions = "other"
        self.disp_path = None
        self.old_name = None

    def __getattr__(self, name):
        # is_file, exists, name などをPathクラスから引き継ぐ
        return getattr(self._path, name)

    def __fspath__(self):
        return os.fspath(self._path)

    def __str__(self):
        return str(self._path)

    def read_text(self, *args, **kwargs):
        """Pathクラスのread_textを呼び出す"""
        return self._path.read_text(*args, **kwargs)

    def write_text(self, data, *args, **kwargs):
        """Pathクラスのwrite_textを呼び出す"""
        return self._path.write_text(data, *args, **kwargs)

    def iserror(self):
        """エラー状態かどうかを判定する"""
        return self.status in {"✖", "⚠", "❌", "⛔", "❗", "🚫", "⚠️"}

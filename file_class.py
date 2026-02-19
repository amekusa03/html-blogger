# -*- coding: utf-8 -*-
import logging
import os
from logging import config, getLogger
from pathlib import Path

from json5 import load

from parameter import config

# logging設定
with open("./data/log_config.json5", "r") as f:
    logging.config.dictConfig(load(f))
logger = getLogger(__name__)
# --- 設定 ---


class SmartFile:
    def __init__(self, path_str):
        self._path = Path(path_str)
        self.status = "⌛"
        self.extensions = ["image", "html", "other"]
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
        return self._path.read_text(*args, **kwargs)

    def write_text(self, data, *args, **kwargs):
        return self._path.write_text(data, *args, **kwargs)

    def iserror(self):
        return self.status in {"✖", "⚠", "❌", "⛔", "❗", "🚫", "⚠️"}

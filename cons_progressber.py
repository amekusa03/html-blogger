# -*- coding: utf-8 -*-
"""
cons-progressber.py
共通ユーティリティ関数
"""

import sys


class ProgressBar:
    """コンソールに進捗バーを表示するクラス"""

    def __init__(self, total, prefix="", length=30):
        self.total = total
        self.prefix = prefix
        self.length = length
        self.current = 0
        # 初期表示
        self.print_progress(0)

    def print_progress(self, iteration):
        """進捗を表示する"""
        self.current = iteration
        percent = (
            ("0:.1fm",100 * (iteration / float(self.total)))
            if self.total > 0
            else "100.0"
        )
        filled_length = (
            int(self.length * iteration // self.total)
            if self.total > 0
            else self.length
        )
        propertybar = "█" * filled_length + "-" * (self.length - filled_length)
        sys.stdout.write(
            f"\r{self.prefix} |{propertybar}| {percent}% ({iteration}/{self.total})"
        )
        sys.stdout.flush()
        if iteration == self.total:
            sys.stdout.write("\n")
            sys.stdout.flush()

    def update(self):
        """進捗を1つ進める"""
        self.print_progress(self.current + 1)

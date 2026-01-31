# -*- coding: utf-8 -*-
"""
utils.py
共通ユーティリティ関数
"""

import sys
import shutil
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# logging設定
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('utils.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
logger.addHandler(logging.StreamHandler())


def read_counter(counter_file='counter.txt'):
    """カウンターファイルから現在のカウンター値を読み取る"""
    counter_path = Path(__file__).parent / counter_file
    if counter_path.exists():
        with open(counter_path, 'r') as f:
            return f.read().strip()
    return '0001'


def write_counter(counter_value, counter_file='counter.txt'):
    """カウンターファイルに新しいカウンター値を書き込む"""
    counter_path = Path(__file__).parent / counter_file
    with open(counter_path, 'w') as f:
        f.write(counter_value)


def increment_counter(counter_hex):
    """16進数カウンターをインクリメント（0001→0002）"""
    counter_int = int(counter_hex, 16)
    counter_int += 1
    if counter_int > 0xFFFF:
        counter_int = 1  # オーバーフロー時はリセット
    return f"{counter_int:04X}"


def copy_files_by_extension(source_dir, output_dir, extensions, file_type_name, use_counter=False):
    """
    指定された拡張子のファイルをコピー
    
    Args:
        source_dir (Path): コピー元ディレクトリ
        output_dir (Path): コピー先ディレクトリ
        extensions (tuple): 対象拡張子のタプル (例: ('.jpg', '.png'))
        file_type_name (str): ファイル種類の表示名 (例: '画像', 'HTMLファイル')
        use_counter (bool): カウンター式ネーミングを使用するか
    
    Returns:
        int: コピーしたファイル数
    """
    # 出力フォルダがなければ作成
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"作成しました: {output_dir}")
    
    logger.info(f"{file_type_name}のコピー処理を開始します...")
    
    # 入力フォルダの存在チェック
    if not source_dir.exists():
        logger.error(f"{source_dir} が存在しません。")
        return 0
    
    copy_count = 0
    current_folder = None
    current_counter = None
    
    # サブフォルダごとにグループ化
    folders = {}
    for src_file in source_dir.rglob('*'):
        if src_file.is_file() and src_file.suffix.lower() in extensions:
            # バックアップファイルをスキップ
            if '.backup_' in src_file.name:
                continue
            
            folder_name = src_file.parent.name
            if folder_name not in folders:
                folders[folder_name] = []
            folders[folder_name].append(src_file)
    
    # フォルダごとに処理
    for folder_name in sorted(folders.keys()):
        if use_counter:
            # フォルダの最初のファイル処理時にカウンターを取得
            current_counter = read_counter()
        
        for src_file in sorted(folders[folder_name]):
            if use_counter:
                # カウンター式: {4桁16進}_フォルダ名ファイル名
                new_name = f"{current_counter}_{folder_name}{src_file.name}"
            elif src_file.parent == source_dir:
                # source_dirの直下にある場合（例: serialization/）はそのまま
                new_name = src_file.name
            else:
                # サブフォルダにある場合: フォルダ名ファイル名
                new_name = f"{folder_name}{src_file.name}"
            
            dest_file = output_dir / new_name
            
            try:
                shutil.copy2(str(src_file), str(dest_file))
                copy_count += 1
                logger.info(f"  [{copy_count}] {new_name}")
            except Exception as e:
                logger.error(f"  {new_name} のコピーに失敗しました。 {e}", exc_info=True)
        
        if use_counter:
            # フォルダ処理完了後、カウンターをインクリメント
            current_counter = increment_counter(current_counter)
            write_counter(current_counter)
    
    logger.info("-" * 50)
    logger.info(f"完了しました。合計 {copy_count} 個の{file_type_name}を {output_dir} にコピーしました。")
    
    return copy_count

class ProgressBar:
    """コンソールに進捗バーを表示するクラス"""
    def __init__(self, total, prefix='', length=30):
        self.total = total
        self.prefix = prefix
        self.length = length
        self.current = 0
        # 初期表示
        self.print_progress(0)

    def print_progress(self, iteration):
        self.current = iteration
        percent = ("{0:.1f}").format(100 * (iteration / float(self.total))) if self.total > 0 else "100.0"
        filled_length = int(self.length * iteration // self.total) if self.total > 0 else self.length
        bar = '█' * filled_length + '-' * (self.length - filled_length)
        sys.stdout.write(f'\r{self.prefix} |{bar}| {percent}% ({iteration}/{self.total})')
        sys.stdout.flush()
        if iteration == self.total:
            sys.stdout.write('\n')
            sys.stdout.flush()
            
    def update(self):
        """進捗を1つ進める"""
        self.print_progress(self.current + 1)

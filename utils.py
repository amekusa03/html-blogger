# -*- coding: utf-8 -*-
"""
utils.py
共通ユーティリティ関数
"""

import shutil
from pathlib import Path


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
    print(f"作成しました: {output_dir}")
    
    print(f"{file_type_name}のコピー処理を開始します...")
    
    # 入力フォルダの存在チェック
    if not source_dir.exists():
        print(f"エラー: {source_dir} が存在しません。")
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
                print(f"  [{copy_count}] {new_name}")
            except Exception as e:
                print(f"  エラー: {new_name} のコピーに失敗しました。 {e}")
        
        if use_counter:
            # フォルダ処理完了後、カウンターをインクリメント
            current_counter = increment_counter(current_counter)
            write_counter(current_counter)
    
    print("-" * 50)
    print(f"完了しました。合計 {copy_count} 個の{file_type_name}を {output_dir} にコピーしました。")
    
    return copy_count

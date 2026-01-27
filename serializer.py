# -*- coding: utf-8 -*-
"""
serializer.py
workフォルダから画像とHTMLを読み込み、
カウンター＋フォルダ名＋ファイル名の形式でserializationフォルダに保存する
HTML内の画像パスも同時に更新する
カウンター管理はこのスクリプトのみが担当
"""

import os
import re
import shutil
from pathlib import Path
from config import get_config

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
# 入力元フォルダ（workフォルダ）
SOURCE_DIR = SCRIPT_DIR / get_config('READY_UPLOAD', 'INPUT_DIR', './work').lstrip('./')
# 出力先フォルダ（serialization）
OUTPUT_DIR = SCRIPT_DIR / 'serialization'
# カウンター管理ファイル
COUNTER_FILE = SCRIPT_DIR / 'counter.txt'

def get_current_counter():
    """counter.txtから現在のカウンター値を読み込む（16進4桁）"""
    if COUNTER_FILE.exists():
        try:
            with open(COUNTER_FILE, 'r') as f:
                counter_hex = f.read().strip()
                return int(counter_hex, 16)
        except (ValueError, IOError):
            print(f"警告: {COUNTER_FILE} の読み込みに失敗しました。カウンターを1から開始します。")
            return 1
    return 1

def save_counter(counter_value):
    """次回用のカウンター値をcounter.txtに保存（16進4桁）"""
    try:
        with open(COUNTER_FILE, 'w') as f:
            f.write(f'{counter_value:04X}')
    except IOError as e:
        print(f"警告: カウンターの保存に失敗しました: {e}")

def update_html_image_paths(html_content, counter_str, folder_name):
    """HTML内の画像パスをシリアライズされたファイル名に更新"""
    prefix = f"{counter_str}_{folder_name}"
    image_extensions = r'\.(jpg|jpeg|png|gif|bmp|webp)'
    
    def replace_src(match):
        quote = match.group(1)
        filename = match.group(2)
        
        # パス区切り文字がない場合のみ置換
        if '/' not in filename and '\\' not in filename and 'http' not in filename.lower():
            new_filename = f"{prefix}{filename}"
            return f'src={quote}{new_filename}{quote}'
        return match.group(0)
    
    pattern = r'src=(["\'])([^"\']+' + image_extensions + r')\1'
    return re.sub(pattern, replace_src, html_content, flags=re.IGNORECASE)

def serialize_files():
    # 出力フォルダがなければ作成
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"作成しました: {OUTPUT_DIR}")

    print("ファイルのシリアライズ処理を開始します...")

    # 前回の続きからカウンター開始
    current_counter = get_current_counter()
    print(f"カウンター開始値: {current_counter:04X}")
    
    total_files = 0

    # まず全フォルダを収集
    all_folders = set()
    for src_file in SOURCE_DIR.rglob('*'):
        if src_file.is_file():
            # 画像またはHTMLファイルのみ対象
            if src_file.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.html', '.htm'):
                all_folders.add(src_file.parent)
    
    # フォルダごとに処理（カウンターを順次インクリメント）
    for folder_path in sorted(all_folders):
        folder_name = folder_path.name
        
        # カウンターを使用（前回の続きから）
        counter_str = f'{current_counter:04X}'  # 4桁16進数
        
        print(f"\n--- フォルダ: {folder_name} (カウンタ: {counter_str}) ---")
        
        folder_file_count = 0
        
        # このフォルダ内のファイルをすべて処理
        for src_file in sorted(folder_path.glob('*')):
            if src_file.is_file():
                # 画像またはHTMLファイルのみコピー
                if src_file.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.html', '.htm'):
                    # 新しいファイル名を作成 (カウンタ_フォルダ名+ファイル名)
                    new_filename = f"{counter_str}_{folder_name}{src_file.name}"

                    # コピー先のフルパス
                    new_path = OUTPUT_DIR / new_filename

                    try:
                        # HTMLファイルの場合は画像パスを更新してコピー
                        if src_file.suffix.lower() in ('.html', '.htm'):
                            with open(src_file, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                            updated_html = update_html_image_paths(html_content, counter_str, folder_name)
                            with open(new_path, 'w', encoding='utf-8') as f:
                                f.write(updated_html)
                        else:
                            # 画像ファイルはそのままコピー
                            shutil.copy2(str(src_file), str(new_path))
                        
                        folder_file_count += 1
                        total_files += 1
                        print(f"  [{total_files}] {src_file.name} -> {new_filename}")
                    except Exception as e:
                        print(f"  エラー: {src_file} のコピーに失敗しました。 {e}")
        
        if folder_file_count > 0:
            print(f"  完了: {folder_file_count} 個のファイルを処理しました")
            # 次のフォルダ用にカウンターをインクリメント
            current_counter += 1
        else:
            print(f"  警告: このフォルダに対象ファイルがありません")

    # 次回用のカウンター値を保存
    save_counter(current_counter)
    print(f"次回カウンター値: {current_counter:04X}")
    
    print("-" * 50)
    print(f"完了しました。{len(all_folders)} フォルダ、合計 {total_files} 個のファイルを {OUTPUT_DIR} にシリアライズしました。")

if __name__ == '__main__':
    serialize_files()

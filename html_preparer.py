# -*- coding: utf-8 -*-
"""
html_preparer.py
workフォルダからHTMLファイルを取り出し、
ファイル名をフォルダ名＋ファイル名としてready_uploadにコピーする
（image_preparer.pyの画像版だが、これはHTML用）
HTML内の画像リンクも「フォルダ名+ファイル名」形式に更新する
"""

import os
import re
import shutil
from pathlib import Path
from config import get_config

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
# HTMLが入っているルートフォルダのパス（work フォルダから読み込み）
SOURCE_HTML_DIR = SCRIPT_DIR / get_config('READY_UPLOAD', 'INPUT_DIR', './work').lstrip('./')
# リネーム後のHTMLを保存するフォルダ
OUTPUT_DIR = SCRIPT_DIR / get_config('READY_UPLOAD', 'OUTPUT_DIR', './ready_upload').lstrip('./')

def update_image_paths_in_html(html_content, folder_name):
    """
    HTML内の画像パスを「フォルダ名+ファイル名」形式に更新
    例: <img src="photo01.jpg"> -> <img src="0205taiphoto01.jpg">
    """
    # 画像ファイルの拡張子パターン
    image_extensions = r'\.(jpg|jpeg|png|gif|bmp|webp)'
    
    # src属性の画像パスを置換
    # パターン: src="ファイル名.拡張子" または src='ファイル名.拡張子'
    def replace_src(match):
        quote = match.group(1)  # 引用符の種類（" または '）
        filename = match.group(2)  # ファイル名部分
        
        # パス区切り文字がない場合のみ置換（相対パスのローカルファイル）
        if '/' not in filename and '\\' not in filename and 'http' not in filename.lower():
            new_filename = f"{folder_name}{filename}"
            return f'src={quote}{new_filename}{quote}'
        return match.group(0)  # 変更なし
    
    # src="..." および src='...' パターンをマッチ
    pattern = r'src=(["\'])([^"\']+' + image_extensions + r')\1'
    updated_html = re.sub(pattern, replace_src, html_content, flags=re.IGNORECASE)
    
    return updated_html

def prepare_html_files():
    # 出力フォルダがなければ作成
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"作成しました: {OUTPUT_DIR}")

    print("HTMLファイルのリネーム処理を開始します...")

    copy_count = 0

    # フォルダ内を再帰的に探索
    for src_file in SOURCE_HTML_DIR.rglob('*'):
        if src_file.is_file() and src_file.suffix.lower() in ('.html', '.htm'):
            # 現在のフォルダ名を取得
            folder_name = src_file.parent.name

            # 新しいファイル名を作成 (フォルダ名 + ファイル名)
            new_filename = f"{folder_name}{src_file.name}"

            # コピー先のフルパス
            new_path = OUTPUT_DIR / new_filename

            try:
                # HTMLファイルを読み込み
                with open(src_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # 画像パスを更新
                updated_html = update_image_paths_in_html(html_content, folder_name)
                
                # 更新したHTMLを書き込み
                with open(new_path, 'w', encoding='utf-8') as f:
                    f.write(updated_html)
                
                copy_count += 1
                print(f"[{copy_count}] {src_file} -> {new_filename} (画像パス更新済み)")
            except Exception as e:
                print(f"エラー: {src_file} の処理に失敗しました。 {e}")

    print("-" * 30)
    print(f"完了しました。合計 {copy_count} 個のHTMLファイルを {OUTPUT_DIR} に集約しました。")

if __name__ == '__main__':
    prepare_html_files()

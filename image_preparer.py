import os
import shutil
from pathlib import Path
from config import get_config

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
# 古い写真が入っているルートフォルダのパス（work フォルダから読み込み）
SOURCE_PHOTOS_DIR = SCRIPT_DIR / get_config('READY_UPLOAD', 'INPUT_DIR', './work').lstrip('./')
# リネーム後の画像を保存するフォルダ
OUTPUT_DIR = SCRIPT_DIR / get_config('READY_UPLOAD', 'OUTPUT_DIR', './ready_upload').lstrip('./')

def prepare_images():
    # 出力フォルダがなければ作成
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"作成しました: {OUTPUT_DIR}")

    print("画像のリネーム処理を開始します...")

    copy_count = 0

    # フォルダ内を再帰的に探索
    for src_file in SOURCE_PHOTOS_DIR.rglob('*'):
        if src_file.is_file() and src_file.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif'):
            # 現在のフォルダ名を取得
            folder_name = src_file.parent.name

            # 新しいファイル名を作成 (フォルダ名_ファイル名)
            # 仕様に合わせて区切り文字を調整してください（例: AAA111.jpg なら folder_name + filename）
            new_filename = f"{folder_name}{src_file.name}"

            # コピー先のフルパス
            new_path = OUTPUT_DIR / new_filename

            try:
                # ファイルをコピー
                shutil.copy2(str(src_file), str(new_path))
                copy_count += 1
                print(f"[{copy_count}] {src_file} -> {new_filename}")
            except Exception as e:
                print(f"エラー: {src_file} のコピーに失敗しました。 {e}")

    print("-" * 30)
    print(f"完了しました。合計 {copy_count} 枚の画像を {OUTPUT_DIR} に集約しました。")
    print("このフォルダ内の画像をBloggerにアップロードしてください。")

if __name__ == '__main__':
    prepare_images()

import os
import shutil

# --- 設定 ---
# 古い写真が入っているルートフォルダのパス
SOURCE_PHOTOS_DIR = './ready_to_upload'
# リネーム後の画像を保存するフォルダ
OUTPUT_DIR = './ready_to_upload_images'

def prepare_images():
    # 出力フォルダがなければ作成
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"作成しました: {OUTPUT_DIR}")

    print("画像のリネーム処理を開始します...")

    copy_count = 0

    # フォルダ内を再帰的に探索
    for root, dirs, files in os.walk(SOURCE_PHOTOS_DIR):
        for filename in files:
            # 画像ファイル（jpg, jpeg, png, gifなど）を対象にする
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                # 現在のフォルダ名を取得
                folder_name = os.path.basename(root)

                # 新しいファイル名を作成 (フォルダ名_ファイル名)
                # 仕様に合わせて区切り文字を調整してください（例: AAA111.jpg なら folder_name + filename）
                new_filename = f"{folder_name}{filename}"

                # 元のファイルのフルパス
                old_path = os.path.join(root, filename)
                # コピー先のフルパス
                new_path = os.path.join(OUTPUT_DIR, new_filename)

                try:
                    # ファイルをコピー
                    shutil.copy2(old_path, new_path)
                    copy_count += 1
                    print(f"[{copy_count}] {old_path} -> {new_filename}")
                except Exception as e:
                    print(f"エラー: {old_path} のコピーに失敗しました。 {e}")

    print("-" * 30)
    print(f"完了しました。合計 {copy_count} 枚の画像を {OUTPUT_DIR} に集約しました。")
    print("このフォルダ内の画像をBloggerにアップロードしてください。")

if __name__ == '__main__':
    prepare_images()

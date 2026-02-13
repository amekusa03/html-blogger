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
from json5 import load    
from pathlib import Path
import shutil
import logging
from logging import config, getLogger
from parameter import config,update_serial,get_serial
from file_class import SmartFile

# logging設定
with open('./data/log_config.json5', 'r') as f:
  logging.config.dictConfig(load(f)) 
logger = getLogger(__name__)
# --- 設定 ---

# 入力フォルダ
source_dir = config['serializer']['input_dir'].lstrip('./')
# シリアライズフォルダ                                     
serialization_dir = config['serializer']['serialization_dir'].lstrip('./')
# 出力フォルダ
output_dir = config['serializer']['output_dir'].lstrip('./')

image_extensions = config['common']['image_extensions']
html_extensions = config['common']['html_extensions']

def run(result_queue):
    """source_dir内のファイルをシリアライズしてserialization_dirに保存する"""
    update_serial() # シリアル番号更新
    
    # 1. 出力先を作成
    shutil.rmtree(serialization_dir, ignore_errors=True)
    Path(serialization_dir).mkdir(exist_ok=True)

    # 2. 全ファイルの対応表を作成
    path_map = {} # {元の絶対パス: 新しいファイル名}
    all_files = list(Path(source_dir).rglob('*'))

    for path in all_files:
        src_file = SmartFile(path)
        if src_file.is_file():
            src_file = serialize(src_file)
            result_queue.put(src_file) 
            
    # フォルダが存在する場合のみ処理
    if os.path.exists(output_dir):
        # フォルダ自体と中のファイルをすべて削除
        shutil.rmtree(output_dir)
        # フォルダを再作成
        os.mkdir(output_dir)
    # コピー実行
    try:
        shutil.copytree(serialization_dir, output_dir, dirs_exist_ok=True)
        logger.info(f"コピー: {serialization_dir} -> {output_dir}")
    except Exception:
        logger.error(f"エラー: ファイルのコピーに失敗しました: {serialization_dir} -> {output_dir}")
    logger.info("シリアライズ完了")            
            
def serialize(files):
    
    def get_serial_name(path):
        """パスをフラットなシリアル名に変換する"""
        relative = path.relative_to(source_dir)
        flat_name = "".join(relative.parts)
        logger.debug(f"Serializing {path} ({relative}) -> {flat_name}")
        return f"{get_serial()}{flat_name}"
    
    #path_map = {} # {元の絶対パス: 新しいファイル名}
    new_name = get_serial_name(files)
    # 3. ファイルの移動とHTML内の書き換え
    #for src_file, new_name in Path(path_map).items():
    dest_path = SmartFile(Path(serialization_dir) / new_name)
    # GUIで表示されていた古いパス（work/ からの相対パス）をold_nameに設定する
    # これにより、GUIは更新対象のアイテムを特定できる
    dest_path.old_name = str(files.relative_to(source_dir))
    
    if files.suffix.lower() in html_extensions:
        # HTMLの場合：中身を書き換えて保存
        content = files.read_text(encoding='utf-8')
        
        def replace_link(match):
            
            original_src = match.group(1)
            # HTMLファイルからの相対パスを絶対パスに変換
            html_dir = files.parent
            link_path = html_dir / original_src
            new_name = get_serial_name(link_path)
            logger.debug(f"  Rewriting link: {original_src} -> {new_name}")
            #return get_serial_name(match)
            return f'src="{new_name}"'
            # 対応表にあるか確認
            # if img_abs_path in path_map:
            #     return f'src="{path_map[img_abs_path]}"' 
            # else:
            #     return f'src="{original_src}"' # リンクエラー時はそのまま

        # imgタグのsrcを置換
        new_content = re.sub(r'src="([^"]+)"', replace_link, content)
        dest_path.extensions = 'html'
        dest_path.write_text(new_content, encoding='utf-8')
        dest_path.disp_path = new_name
        dest_path.status = '✓'
        logger.info(f"[HTML] {files.name} -> {new_name} (リンク更新済)")
        
    if files.suffix.lower() in image_extensions:   # 画像：単にコピー（または移動）
        dest_path.extensions = 'image'
        shutil.move(files, dest_path) 
        dest_path.disp_path = new_name
        dest_path.status = '✓'
        logger.info(f"[FILE] {files.name} -> {new_name}")
    return dest_path

    
import queue

# --- メイン処理 ---
if __name__ == '__main__':
    
    result_queue=queue.Queue()
    try:
        run(result_queue)
    except KeyboardInterrupt:
        logger.info("処理が中断されました。")
    except Exception as e:
        logger.critical(f"予期せぬエラーが発生しました: {e}", exc_info=True)

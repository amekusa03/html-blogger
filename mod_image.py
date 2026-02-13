# -*- coding: utf-8 -*-
"""
html_preparer.py
serializationフォルダからHTMLファイルのみをready_uploadにコピー
（カウンター式ネーミング済み）
"""
from json5 import load    
from pathlib import Path
import logging
from logging import config, getLogger
from parameter import config

import concurrent.futures
from PIL import Image, ImageDraw, ImageFont
import piexif
from file_class import SmartFile

# logging設定
with open('./data/log_config.json5', 'r') as f:
  logging.config.dictConfig(load(f)) 
logger = getLogger(__name__)
# --- 設定 ---

# --- 設定 ---
# 入力元フォルダ
input_dir = config['mod_image']['input_dir']
# 出力先フォルダ
output_dir = config['mod_image']['output_dir']
image_extensions = config['common']['image_extensions']

def run(result_queue):
    all_files = list(Path(input_dir).rglob('*'))

    for path in all_files:
        src_file = SmartFile(path)
        if src_file.is_file():
            if src_file.suffix.lower() in image_extensions:
                src_file = image_edit(src_file)
                src_file.status = '✔'
                src_file.extensions = 'image'
                src_file.disp_path = src_file.name
                result_queue.put(src_file) 
            
    
def image_edit(files):
    
    """画像を開き、EXIFを除去し、右下に透かしテキストを追加して保存する。アニメーションGIF対応。"""
    try:
        image = Image.open(Path(files))
    except Exception as e:
        logger.warning(f"画像読み込みエラー: {files} - {e}")
        files.status = '✘'
        return files
    watermark_text = config['mod_image']['watermark_text']
    font, pos = None, None
    if watermark_text:
        font, pos = _prepare_watermark_params(image, watermark_text)
    
    is_animated = hasattr(image, 'n_frames') and image.format == 'GIF' and image.n_frames > 1
    if is_animated:
        # アニメーションGIFの場合
        frames = []
        durations = []
        for frame_num in range(image.n_frames):
            image.seek(frame_num)
            frame = image.convert('RGBA')
            if watermark_text:
                frame = _add_watermark_to_frame(frame, font, watermark_text, pos)
            frames.append(frame.convert('P', palette=Image.ADAPTIVE))
            durations.append(image.info.get('duration', 100))
        
        loop = image.info.get('loop', 0)
        frames[0].save(
            Path(files),
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=loop,
            optimize=False
        )
    else:
        image = image.convert("RGBA")
        if watermark_text:
            image = _add_watermark_to_frame(image, font, watermark_text, pos)
        if files.suffix.lower() == '.gif':
            image = image.convert('P', palette=Image.ADAPTIVE)
            image.save(Path(files), optimize=True)
        else:
            if files.suffix.lower() in ('.jpg', '.jpeg'):
                image = image.convert("RGB")
            image.save(Path(files), quality=90)
    return files
        
def _add_watermark_to_frame(frame, font, text, pos, outline=2):
    """単一フレームにウォーターマークを追加（アルファコンポジット使用で透過を確実にする）"""
    txt_layer = Image.new('RGBA', frame.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)

    # 半透明の黒い縁取り
    for dx in (-outline, outline):
        for dy in (-outline, outline):
            draw.text((pos[0] + dx, pos[1] + dy), text, font=font, fill=(0, 0, 0, 50))
    # 半透明の白い文字
    draw.text(pos, text, font=font, fill=(255, 255, 255, 100))

    return Image.alpha_composite(frame, txt_layer)

def _prepare_watermark_params(image, text):
    """ウォーターマークのフォントと位置を計算する共通関数"""
    w, h = image.size
    font_size = max(16, min(w, h) // 20)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    temp_draw = ImageDraw.Draw(image)
    try:
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError: # 古いPillowバージョン用のフォールバック
        text_w, text_h = temp_draw.textsize(text, font=font)

    padding = max(10, min(w, h) // 50)
    pos = (w - text_w - padding, h - text_h - padding)

    return font, pos


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
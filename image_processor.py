# -*- coding: utf-8 -*-
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import concurrent.futures
import os

from PIL import Image, ImageDraw, ImageFont
import piexif

from config import get_config
from utils import ProgressBar
import database

# --- ロギング設定 ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('image_processor.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING) # プログレスバー表示のため、コンソールは警告以上のみ表示
logger.addHandler(stream_handler)

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = SCRIPT_DIR / get_config('IMAGE_PROCESSOR', 'output_dir', './work/processed_images').lstrip('./')
WATERMARK_TEXT = get_config('IMAGE_PROCESSOR', 'watermark_text', '')

SUPPORTED_EXTS = {'.jpg', '.jpeg', '.png', '.gif'}


def ensure_dir(path: Path) -> None:
    """ディレクトリが存在しない場合に作成する"""
    path.mkdir(parents=True, exist_ok=True)


def add_watermark_to_frame(frame, font, text, pos, outline=2):
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


def process_single_image(src: Path, dest: Path):
    """画像を開き、EXIFを除去し、右下に透かしテキストを追加して保存する。アニメーションGIF対応。"""
    image = Image.open(src)

    font, pos = None, None
    if WATERMARK_TEXT:
        font, pos = _prepare_watermark_params(image, WATERMARK_TEXT)
    
    is_animated_gif = (src.suffix.lower() == '.gif' and getattr(image, 'is_animated', False) and image.n_frames > 1)
    
    if is_animated_gif:
        frames = []
        durations = []
        for frame_num in range(image.n_frames):
            image.seek(frame_num)
            frame = image.convert('RGBA')
            if WATERMARK_TEXT:
                frame = add_watermark_to_frame(frame, font, WATERMARK_TEXT, pos)
            frames.append(frame.convert('P', palette=Image.ADAPTIVE))
            durations.append(image.info.get('duration', 100))
        
        ensure_dir(dest.parent)
        frames[0].save(dest, save_all=True, append_images=frames[1:], duration=durations, loop=image.info.get('loop', 0), optimize=False)
    else:
        image = image.convert("RGBA")
        if WATERMARK_TEXT:
            image = add_watermark_to_frame(image, font, WATERMARK_TEXT, pos)
        
        ensure_dir(dest.parent)
        if src.suffix.lower() == '.gif':
            image = image.convert('P', palette=Image.ADAPTIVE)
            image.save(dest, optimize=True)
        else:
            if dest.suffix.lower() in ('.jpg', '.jpeg'):
                image = image.convert("RGB")
            image.save(dest, quality=90)
            try:
                piexif.remove(str(dest))
            except Exception:
                pass

def _process_wrapper(src, dest):
    """並列処理用のラッパー関数"""
    logger.debug(f"画像処理開始: {src.name}")
    process_single_image(src, dest)
    return src, dest

def run_image_processing_pipeline():
    """DBから新規画像を処理するパイプラインを実行する"""
    # デバッグログ設定の反映
    if get_config('DEFAULT', 'debug_log', 'false').lower() == 'true':
        logger.setLevel(logging.DEBUG)

    logger.info("--- 画像処理パイプライン開始 ---")
    ensure_dir(OUTPUT_DIR)

    images_to_process = database.get_images_by_status('new')
    
    if not images_to_process:
        logger.info("処理対象の新規画像はありません。")
        logger.info("--- 画像処理パイプライン完了 ---")
        return 0, 0

    logger.info(f"{len(images_to_process)} 件の新規画像を処理します。")
    
    # CPUコア数に基づいてワーカー数を決定（最大4）
    max_workers = min(4, os.cpu_count() or 1)
    logger.info(f"並列処理ワーカー数: {max_workers}")

    success_count = 0
    error_count = 0

    pbar = ProgressBar(len(images_to_process), prefix='Watermark')
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Futureと画像ID/パスの紐付け
        future_to_data = {}
        
        for image_data in images_to_process:
            image_id = image_data['id']
            source_path = Path(image_data['source_path'])
            output_path = OUTPUT_DIR / source_path.name

            if not source_path.exists():
                error_msg = f"ソースファイルが見つかりません: {source_path}"
                logger.error(error_msg)
                database.update_image_info(image_id, status='error', error_message=error_msg)
                error_count += 1
                pbar.update()
                continue

            # 処理をサブミット
            future = executor.submit(_process_wrapper, source_path, output_path)
            future_to_data[future] = (image_id, source_path, output_path)

        # 完了したものから順次DB更新（DBロック回避のためメインスレッドで実行）
        for future in concurrent.futures.as_completed(future_to_data):
            image_id, source_path, output_path = future_to_data[future]
            try:
                future.result() # 例外があればここで発生
                database.update_image_info(image_id, status='watermarked', processed_path=output_path)
                logger.info(f"成功: {source_path.name} -> {output_path}")
                success_count += 1
            except Exception as e:
                error_msg = f"ウォーターマーク処理失敗: {e}"
                logger.error(f"失敗: {source_path.name} - {error_msg}", exc_info=True)
                database.update_image_info(image_id, status='error', error_message=error_msg)
                error_count += 1
            pbar.update()

    logger.info("--- 画像処理パイプライン完了 ---")
    logger.info(f"成功: {success_count}件, 失敗: {error_count}件")
    return success_count, error_count

if __name__ == '__main__':
    run_image_processing_pipeline()
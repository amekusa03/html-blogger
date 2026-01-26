# -*- coding: utf-8 -*-
"""画像のEXIF削除とウォーターマーク付与"""
import os
from pathlib import Path

import piexif
from PIL import Image, ImageDraw, ImageFont

from config import get_config

# 設定
SCRIPT_DIR = Path(__file__).parent.resolve()
INPUT_DIR = SCRIPT_DIR / get_config('PHOROS_DELEXIF_ADDWATERMARK', 'INPUT_DIR', './work')
OUTPUT_DIR = SCRIPT_DIR / get_config('PHOROS_DELEXIF_ADDWATERMARK', 'OUTPUT_DIR', './work')
WATERMARK_TEXT = get_config('PHOROS_DELEXIF_ADDWATERMARK', 'WATERMARK', '')

SUPPORTED_EXTS = {'.jpg', '.jpeg', '.png', '.gif'}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def add_watermark_to_frame(frame, font, text, pos, outline=2):
    """単一フレームにウォーターマークを追加"""
    draw = ImageDraw.Draw(frame)
    # 半透明黒縁取り＋白文字で視認性を確保
    for dx in (-outline, outline):
        for dy in (-outline, outline):
            draw.text((pos[0] + dx, pos[1] + dy), text, font=font, fill=(0, 0, 0, 128))
    draw.text(pos, text, font=font, fill=(255, 255, 255))
    return frame


def add_watermark_and_remove_exif(src: Path, dest: Path) -> None:
    """画像を開き、EXIFを除去し、右下に透かしテキストを追加して保存する。アニメーションGIF対応。"""
    image = Image.open(src)
    
    # GIFでアニメーションがあるか確認
    is_animated_gif = (src.suffix.lower() == '.gif' and 
                       getattr(image, 'is_animated', False) and 
                       image.n_frames > 1)
    
    if is_animated_gif:
        # アニメーションGIFの処理
        frames = []
        durations = []
        
        # フォント準備（最初のフレームのサイズで決定）
        w, h = image.size
        font_size = max(16, min(w, h) // 20)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()
        
        # テキストサイズ計算
        if WATERMARK_TEXT:
            temp_draw = ImageDraw.Draw(image)
            try:
                bbox = temp_draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
                text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            except Exception:
                text_w, text_h = temp_draw.textsize(WATERMARK_TEXT, font=font)
            padding = max(10, min(w, h) // 50)
            pos = (w - text_w - padding, h - text_h - padding)
        
        # 各フレームを処理
        for frame_num in range(image.n_frames):
            image.seek(frame_num)
            frame = image.convert('RGBA')
            
            # ウォーターマーク追加
            if WATERMARK_TEXT:
                frame = add_watermark_to_frame(frame, font, WATERMARK_TEXT, pos)
            
            frames.append(frame.convert('P', palette=Image.ADAPTIVE))
            # フレームの表示時間を取得（デフォルト100ms）
            durations.append(image.info.get('duration', 100))
        
        # アニメーションGIFとして保存
        ensure_dir(dest.parent)
        frames[0].save(
            dest,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=image.info.get('loop', 0),
            optimize=False
        )
    else:
        # 静止画の処理（従来通り）
        if src.suffix.lower() == '.gif':
            # 静止画GIFの場合はRGBAで開く
            image = image.convert("RGBA")
        else:
            image = image.convert("RGB")
        
        # ウォーターマーク描画
        if WATERMARK_TEXT:
            draw = ImageDraw.Draw(image)
            w, h = image.size
            # フォントサイズは短辺の1/20程度を目安
            font_size = max(16, min(w, h) // 20)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
            # Pillow 10以降は textsize が廃止されているため textbbox を使用
            try:
                bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
                text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            except Exception:
                # 古いPillow向けフォールバック
                text_w, text_h = draw.textsize(WATERMARK_TEXT, font=font)
            padding = max(10, min(w, h) // 50)
            pos = (w - text_w - padding, h - text_h - padding)
            # 半透明黒縁取り＋白文字で視認性を確保
            outline = 2
            for dx in (-outline, outline):
                for dy in (-outline, outline):
                    draw.text((pos[0] + dx, pos[1] + dy), WATERMARK_TEXT, font=font, fill=(0, 0, 0, 128))
            draw.text(pos, WATERMARK_TEXT, font=font, fill=(255, 255, 255))
        
        # EXIFを除去して保存
        ensure_dir(dest.parent)
        if src.suffix.lower() == '.gif':
            # GIFの場合はPモードに変換して保存
            image = image.convert('P', palette=Image.ADAPTIVE)
            image.save(dest, optimize=True)
        else:
            image.save(dest, quality=90)
            try:
                # 念のためEXIFを削除（Pillow保存時は通常付かないが保険）
                piexif.remove(str(dest))
            except Exception:
                pass


def process_images():
    if not INPUT_DIR.exists():
        print(f"エラー: 入力フォルダが見つかりません: {INPUT_DIR}")
        return

    ensure_dir(OUTPUT_DIR)

    processed = 0
    copied = 0

    print(f"--- EXIF削除＆ウォーターマーク追加を開始します (入力: {INPUT_DIR}, 出力: {OUTPUT_DIR}) ---")

    for root, _, files in os.walk(INPUT_DIR):
        rel = os.path.relpath(root, INPUT_DIR)
        out_dir = OUTPUT_DIR / rel if rel != "." else OUTPUT_DIR
        for name in files:
            src_path = Path(root) / name
            dest_path = out_dir / name
            if src_path.suffix.lower() in SUPPORTED_EXTS:
                try:
                    add_watermark_and_remove_exif(src_path, dest_path)
                    processed += 1
                except Exception as e:
                    print(f"× 失敗: {src_path} -> {e}")
            else:
                # 対象外はコピー
                ensure_dir(dest_path.parent)
                try:
                    dest_path.write_bytes(src_path.read_bytes())
                    copied += 1
                except Exception as e:
                    print(f"× コピー失敗: {src_path} -> {e}")

    print("-" * 30)
    print(f"【処理完了】画像処理: {processed} 件, コピーのみ: {copied} 件")


if __name__ == "__main__":
    process_images()

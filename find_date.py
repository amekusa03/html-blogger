# -*- coding: utf-8 -*-
import os
import re      
from json5 import load    
from pathlib import Path
import unicodedata
import calendar
import logging
from logging import config, getLogger
from parameter import config
from file_class import SmartFile

# logging設定
with open('./data/log_config.json5', 'r') as f:
  logging.config.dictConfig(load(f)) 
logger = getLogger(__name__)

# --- 設定 ---

# 入力元フォルダ
input_dir = config['find_date']['input_dir'].lstrip('./')
# 出力先フォルダ
output_dir = config['find_date']['output_dir'].lstrip('./')
html_extensions = config['common']['html_extensions']

def extract_date_from_html(html_text):
    """HTMLテキストから日付を抽出する"""
    extracted_date = ""
    
    # 1. <time datetime="..."> タグから抽出
    date_match = re.search(r'<time\s+datetime=["\'](.*?)["\']', html_text, flags=re.IGNORECASE | re.DOTALL)
    if date_match:
        for group in date_match.groups():
            if group.strip() != "":
                extracted_date = group.strip()
                return extracted_date
    
    # 2. 本文中の日付パターンを探す（例: 2003年1/18〜20）
    unicode_text = unicodedata.normalize('NFKC', html_text)
    
    # 日付形式の正規化パターン
    # 2002.04.25-29 → 2002年04月25日〜29日
    # 2002/04/25-29 → 2002年04月25日〜29日
    unicode_text = re.sub(r'(\d{4})\.(\d{1,2})\.(\d{1,2})-(\d{1,2})', r'\1年\2月\3日〜\4日', unicode_text)
    unicode_text = re.sub(r'(\d{4})\.(\d{1,2})\.(\d{1,2})', r'\1年\2月\3日', unicode_text)
    unicode_text = re.sub(r'(\d{4})/(\d{1,2})/(\d{1,2})-(\d{1,2})', r'\1年\2月\3日〜\4日', unicode_text)
    unicode_text = re.sub(r'(\d{4})/(\d{1,2})/(\d{1,2})', r'\1年\2月\3日', unicode_text)
    
    def extract_year():
        match = re.search(r'(\d{4})年', unicode_text)
        if not match:
            match = re.search(r'(\d{4})/', unicode_text)
            if not match:
                match = re.search(r'(\d{4}.)', unicode_text)
                if not match:
                    match = re.search(r'(\d{4})', unicode_text)
                    if not match:
                        return None
        year = int(match.group(1))
        if year > 1900 and year < 2100:
            return str(year)
        return None
    
    def extract_month():
        match = re.search(r'(\d{1,2})月', unicode_text)
        if not match:
            match = re.search(r'/(\d{1,2})/', unicode_text)
            if not match:
                match = re.search(r'/(\d{1,2}).', unicode_text)
                if not match:
                    match = re.search(r'/(\d{1,2})', unicode_text)
                    if not match:
                        return None
        month = int(match.group(1))
        if month >= 1 and month <= 12:
            return str(month)
        return None
    
    def extract_start_day():
        match = re.search(r'(\d{1,2})日', unicode_text)
        if not match:
            match = re.search(r'/(\d{1,2})/', unicode_text)
            if not match:
                match = re.search(r'/(\d{1,2}).', unicode_text)
                if not match:
                    match = re.search(r'/(\d{1,2})', unicode_text)
                    if not match:
                        return None
        day = int(match.group(1))
        if day >= 1 and day <= 31:
            return str(day)
        return None
    
    def extract_end_day():
        match = re.search(r'〜\s*(\d{1,2})日', unicode_text)
        if not match:
            match = re.search(r'〜\s*/(\d{1,2})/', unicode_text)
            if not match:
                match = re.search(r'〜\s*/(\d{1,2}).', unicode_text)
                if not match:
                    match = re.search(r'〜\s*/(\d{1,2})', unicode_text)
                    if not match:
                        return None
        day = int(match.group(1))
        if day >= 1 and day <= 31:
            return str(day)
        return None
    
    year = extract_year()
    month = extract_month()
    start_day = extract_start_day()
    end_day = extract_end_day()
    
    # None チェック
    if year is None or month is None:
        return ""
    
    if end_day is None:
        day = start_day
    else:
        day = end_day
    
    # day が None の場合は月の最終日を使用
    if day is None and year is not None and month is not None:
        try:
            day = str(calendar.monthrange(int(year), int(month))[1])
        except (ValueError, TypeError):
            return ""
    
    # すべての必須フィールドがそろった場合のみ日付を確定
    if month is not None and year is not None and day is not None:
        extracted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    return extracted_date

def add_date_to_html(html_path):
    """HTMLファイルに日付情報を追加する"""
    try:
        # ファイル読み込み（複数エンコーディング対応）
        content = None
        with open(html_path, 'r', encoding='utf-8',) as f:
            content = f.read()
        
        if not content:
            logger.error(f"失敗(文字コード不明): {html_path.name}")
            return False
        
        # 日付を抽出
        extracted_date = extract_date_from_html(content)
        
        if extracted_date:
            logger.info(f"Date見つかりました: {extracted_date}")
            
            # 既存の<time>タグがあれば削除（重複防止）
            content = re.sub(r'<time[^>]*>.*?</time>', '', content, flags=re.IGNORECASE | re.DOTALL)
            
            # <time datetime="YYYY-MM-DD"></time> タグを作成
            time_tag = f'<time datetime="{extracted_date}"></time>\n'
            
            # <title>タグの直後に挿入
            if re.search(r'</title>', content, re.IGNORECASE):
                content = re.sub(r'(</title>)', r'\1\n' + time_tag, content, count=1, flags=re.IGNORECASE)
            else:
                # <title>がない場合は先頭に追加
                logger.warning("<title>タグが見つかりません。ファイル先頭に追加します。")
                content = time_tag + content
            
            # ファイル書き込み
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return html_path
        else:
            logger.warning("Dateが見つかりません")
            return html_path  # エラーではないので継続
    
    except Exception as e:
        logger.error(f"エラー: {html_path.name} - {e}", exc_info=True)
        return False

def run(result_queue):
    if not Path(input_dir).exists():
        logger.error(f"{input_dir} が見つかりません")
        return False
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    processed_count = 0
    logger.info(f"--- 日付追加処理を開始します (対象フォルダ: {input_dir}) ---")
    
    for root, dirs, files in os.walk(str(input_dir)):
        for filename in files:
            if filename.lower().endswith(tuple(html_extensions)):
                src_path = Path(root) / filename
                processed_count += 1
                
                logger.info(f"[{processed_count}] {src_path.relative_to(input_dir)}")
                files = SmartFile(add_date_to_html(SmartFile(src_path)))
                files.status = '✔'
                files.extensions = 'html'
                files.disp_path = files.name
                result_queue.put(files)     
    logger.info("-" * 30)
    logger.info("【処理完了】")
    logger.info(f"処理したHTML: {processed_count} 本")

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
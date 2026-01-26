# -*- coding: utf-8 -*-
import os
import re
import unicodedata
import calendar
import sys
from pathlib import Path
from config import get_config

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
INPUT_DIR = SCRIPT_DIR / get_config('ADD_DATE', 'INPUT_DIR', './work')
OUTPUT_DIR = SCRIPT_DIR / get_config('ADD_DATE', 'OUTPUT_DIR', './work')

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
    if start_day is not None and month is not None and year is not None and day is not None:
        extracted_date = f"{year}-{month}-{day}"
    
    return extracted_date

def add_date_to_html(html_path):
    """HTMLファイルに日付情報を追加する"""
    try:
        # ファイル読み込み（複数エンコーディング対応）
        content = None
        for encoding in ['utf-8', 'cp932', 'shift_jis']:
            try:
                with open(html_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except:
                continue
        
        if not content:
            print(f"  ×失敗(文字コード不明): {html_path.name}")
            return False
        
        # 日付を抽出
        extracted_date = extract_date_from_html(content)
        
        if extracted_date:
            print(f"  -> Date見つかりました: {extracted_date}")
            
            # 既存の<time>タグがあれば削除（重複防止）
            content = re.sub(r'<time[^>]*>.*?</time>', '', content, flags=re.IGNORECASE | re.DOTALL)
            
            # <time datetime="YYYY-MM-DD"></time> タグを作成
            time_tag = f'<time datetime="{extracted_date}"></time>\n'
            
            # <title>タグの直後に挿入
            if re.search(r'</title>', content, re.IGNORECASE):
                content = re.sub(r'(</title>)', r'\1\n' + time_tag, content, count=1, flags=re.IGNORECASE)
            else:
                # <title>がない場合は先頭に追加
                print(f"  -> 警告: <title>タグが見つかりません。ファイル先頭に追加します。")
                content = time_tag + content
            
            # ファイル書き込み
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        else:
            print(f"  -> !!!!Dateが見つかりません!!!!")
            return True  # エラーではないので継続
    
    except Exception as e:
        print(f"  ×エラー: {html_path.name} - {e}")
        return False

def main():
    if not INPUT_DIR.exists():
        print(f"エラー: {INPUT_DIR} が見つかりません")
        sys.exit(1)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    processed_count = 0
    print(f"--- 日付追加処理を開始します (対象フォルダ: {INPUT_DIR}) ---")
    
    for root, dirs, files in os.walk(str(INPUT_DIR)):
        for filename in files:
            if filename.lower().endswith(('.htm', '.html')):
                src_path = Path(root) / filename
                processed_count += 1
                
                print(f"[{processed_count}] {src_path.relative_to(INPUT_DIR)}")
                add_date_to_html(src_path)
    
    print("-" * 30)
    print(f"【処理完了】")
    print(f"処理したHTML: {processed_count} 本")

if __name__ == '__main__':
    main()

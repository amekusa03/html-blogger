# -*- coding: utf-8 -*-
import os
import re
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from config import get_config

# logging設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('add_keywords.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_keywords(xml_path):
    """XMLからキーワードを読み込む。返却値: (mast_keywords, hit_keywords, success_flag)"""
    try:
        if not os.path.exists(xml_path):
            logger.error(f"{xml_path} が見つかりません。")
            return [], [], False
        
        tree = ET.parse(xml_path)
        root = tree.getroot()
        mast_keywords = [node.text for node in root.find('Mastkeywords').findall('word') if node.text]
        hit_keywords = [node.text for node in root.find('Hitkeywords').findall('word') if node.text]
        return mast_keywords, hit_keywords, True
    except Exception as e:
        logger.error(f"XML読み込みエラー: {e}", exc_info=True)
        return [], [], False

def process_html(file_path, mast_keywords, hit_keywords):
    """HTMLファイルにキーワードを<search>タグで注入。"""
    
    try:
        # ファイル読み込み
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 1. 既存の <search> タグからキーワードを抽出
        current_keywords = []
        search_match = re.search(r'<search>([^<]*)</search>', html_content, re.IGNORECASE)
        if search_match:
            keywords_str = search_match.group(1).strip()
            words = [k.strip() for k in keywords_str.replace('，', ',').split(',') if k.strip()]
            current_keywords.extend(words)
            # 既存の <search> タグを削除
            html_content = re.sub(r'<search>[^<]*</search>', '', html_content, flags=re.IGNORECASE)

        # 2. 新しいキーワードリストの作成（重複排除）
        new_keywords_list = []
        # 既存分
        for kw in current_keywords:
            if kw not in new_keywords_list:
                new_keywords_list.append(kw)
        # 必須分
        for kw in mast_keywords:
            if kw not in new_keywords_list:
                new_keywords_list.append(kw)
        # 本文ヒット分
        clean_text = re.sub(r'<[^>]*?>', '', html_content)
        for h_kw in hit_keywords:
            if h_kw in clean_text and h_kw not in new_keywords_list:
                new_keywords_list.append(h_kw)

        # 3. <search> タグを作成
        search_tag = f'<search>{",".join(new_keywords_list)}</search>'

        # 4. <head>内の<title>の後に挿入
        if re.search(r'</title>', html_content, re.IGNORECASE):
            html_content = re.sub(r'(</title>)', r'\1\n' + search_tag, html_content, count=1, flags=re.IGNORECASE)
        elif re.search(r'<head>', html_content, re.IGNORECASE):
            # <title>がない場合は<head>の直後
            html_content = re.sub(r'(<head[^>]*>)', r'\1\n' + search_tag, html_content, count=1, flags=re.IGNORECASE)
        else:
            # <head>もない場合は先頭
            html_content = search_tag + '\n' + html_content

        # 5. ファイル保存
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"完了: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"{file_path} の処理に失敗しました: {e}", exc_info=True)
        return False

def main():
    script_dir = Path(__file__).parent.resolve()
    xml_file = script_dir / get_config('ADD_KEYWORDS', 'XML_FILE')
    add_keywords_dir = script_dir / get_config('ADD_KEYWORDS', 'ADD_KEYWORDS_DIR')
    
    # ✅ ファイル存在確認
    if not xml_file.exists():
        logger.error(f"{xml_file} が見つかりません。")
        return
    if not add_keywords_dir.exists():
        logger.error(f"{add_keywords_dir} ディレクトリが見つかりません。")
        return

    # ✅ キーワード読み込み（戻り値チェック）
    mast_kws, hit_kws, success = load_keywords(str(xml_file))
    
    if not success:
        logger.warning("キーワード読み込みに失敗しました。キーワード注入をスキップします。")
        return
    
    if not mast_kws and not hit_kws:
        logger.warning("キーワードが見つかりません。")

    # ✅ ファイル処理（戻り値チェック）
    processed_count = 0
    failed_count = 0
    
    for entry in add_keywords_dir.iterdir():
        if entry.is_dir():
            for file in entry.iterdir():
                if file.is_file() and file.suffix.lower() in ('.html', '.htm'):
                    success = process_html(str(file), mast_kws, hit_kws)
                    if success:
                        processed_count += 1
                    else:
                        failed_count += 1
    
    logger.info("-" * 30)
    logger.info("【処理完了】")
    logger.info(f"成功: {processed_count} ファイル")
    if failed_count > 0:
        logger.warning(f"失敗: {failed_count} ファイル")

if __name__ == "__main__":
    main()

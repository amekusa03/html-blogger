# -*- coding: utf-8 -*-
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from config import get_config
from utils import ProgressBar
import database

# --- ロギング設定 ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('keyword_adder.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING) # プログレスバー表示のため、コンソールは警告以上のみ表示
logger.addHandler(stream_handler)

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
XML_FILE = SCRIPT_DIR / get_config('ADD_KEYWORDS', 'xml_file', 'keywords.xml')

def load_keywords(xml_path):
    """XMLからキーワードを読み込む。"""
    try:
        if not xml_path.exists():
            logger.error(f"{xml_path} が見つかりません。")
            return None, None
        
        tree = ET.parse(str(xml_path))
        root = tree.getroot()
        mast_keywords = [node.text.strip() for node in root.find('Mastkeywords').findall('word') if node.text and node.text.strip()]
        hit_keywords = [node.text.strip() for node in root.find('Hitkeywords').findall('word') if node.text and node.text.strip()]
        return mast_keywords, hit_keywords
    except Exception as e:
        logger.error(f"XML読み込みエラー: {e}", exc_info=True)
        return None, None

def add_keywords_to_content(html_content, mast_keywords, hit_keywords):
    """HTMLコンテンツにキーワードを<search>タグで注入する。"""
    
    # 1. 既存の <search> タグからキーワードを抽出
    current_keywords = []
    search_match = re.search(r'<search[^>]*>([^<]*)</search>', html_content, re.IGNORECASE)
    if search_match:
        keywords_str = search_match.group(1).strip()
        words = [k.strip() for k in keywords_str.replace('，', ',').split(',') if k.strip()]
        current_keywords.extend(words)
        # 既存の <search> タグを削除
        html_content = re.sub(r'<search[^>]*>[^<]*</search>', '', html_content, flags=re.IGNORECASE)

    # 1.5 本文中の「キーワード: ...」から抽出
    body_keywords = []
    # タグを改行に置換してテキスト抽出（行単位での解析のため）
    text_for_parsing = re.sub(r'<[^>]+>', '\n', html_content)
    # 「キーワード: A, B」パターンを検索
    kw_matches = re.finditer(r'キーワード[:：]\s*([^\n\r]+)', text_for_parsing)
    for match in kw_matches:
        kw_str = match.group(1).strip()
        # カンマ、読点などで分割
        words = [k.strip() for k in re.split(r'[,，、]', kw_str) if k.strip()]
        body_keywords.extend(words)
    
    # 抽出元の行を削除 (空行が残らないように改行もケア)
    # 本文からキーワード行を削除すると空のタグが残る場合があるため、削除処理をスキップします
    # html_content = re.sub(r'キーワード[:：]\s*[^\n\r]+[\r\n]*', '', html_content)

    # 2. キーワードをすべて集める
    all_keywords = []
    all_keywords.extend(mast_keywords) # 必須キーワード
    clean_text = re.sub(r'<[^>]*?>', '', html_content) # 本文からヒットキーワード
    for h_kw in hit_keywords:
        if h_kw in clean_text:
            all_keywords.append(h_kw)
    all_keywords.extend(current_keywords) # 既存キーワード
    all_keywords.extend(body_keywords)    # 本文から抽出したキーワード

    # 3. 重複を削除しつつ、順序を維持
    # 空文字とカンマを除外
    cleaned_keywords = []
    for k in all_keywords:
        if k:
            k_clean = k.strip().strip(',').strip()
            if k_clean:
                cleaned_keywords.append(k_clean)
    new_keywords_list = list(dict.fromkeys(cleaned_keywords))

    if new_keywords_list:
        logger.debug(f"hoge: 最終的なキーワードリスト: {new_keywords_list}")

        # 念のため、結合後の文字列からも前後のカンマを削除
        search_tag = f'<search>{",".join(new_keywords_list).strip(",")}</search>'

        # 4. <head>内の<title>の後に挿入
        if re.search(r'</title>', html_content, re.IGNORECASE):
            html_content = re.sub(r'(</title>)', r'\1\n' + search_tag, html_content, count=1, flags=re.IGNORECASE)
        elif re.search(r'<head>', html_content, re.IGNORECASE):
            html_content = re.sub(r'(<head[^>]*>)', r'\1\n' + search_tag, html_content, count=1, flags=re.IGNORECASE)
        else:
            html_content = search_tag + '\n' + html_content
    
    return html_content

def run_keyword_addition_pipeline():
    """DBから'new'ステータスの記事を取得し、キーワードを追加するパイプライン"""
    logger.info("--- キーワード追加パイプライン開始 ---")

    mast_kws, hit_kws = load_keywords(XML_FILE)
    if mast_kws is None or hit_kws is None:
        logger.error("キーワードの読み込みに失敗したため、処理を中断します。")
        return 0, 1

    articles_to_process = database.get_articles_by_status('new')
    
    if not articles_to_process:
        logger.info("処理対象の新規記事はありません。")
        logger.info("--- キーワード追加パイプライン完了 ---")
        return 0, 0

    logger.info(f"{len(articles_to_process)} 件の新規記事を処理します。")
    success_count, error_count = 0, 0

    pbar = ProgressBar(len(articles_to_process), prefix='Keyword')
    for article_data in articles_to_process:
        article_id = article_data['id']
        source_path = Path(article_data['source_path'])

        try:
            if not source_path.exists():
                raise FileNotFoundError(f"ソースファイルが見つかりません: {source_path}")

            with open(source_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()

            updated_content = add_keywords_to_content(html_content, mast_kws, hit_kws)
            
            database.update_content(article_id, updated_content)
            database.update_status(article_id, 'keywords_added')
            
            logger.info(f"成功: {source_path.name} (ID: {article_id})")
            success_count += 1
        except Exception as e:
            error_msg = f"キーワード追加処理失敗: {e}"
            logger.error(f"失敗: {source_path.name} - {error_msg}", exc_info=True)
            database.update_status(article_id, 'error', error_message=error_msg)
            error_count += 1
        pbar.update()

    logger.info("--- キーワード追加パイプライン完了 ---")
    logger.info(f"成功: {success_count}件, 失敗: {error_count}件")
    return success_count, error_count

if __name__ == '__main__':
    run_keyword_addition_pipeline()
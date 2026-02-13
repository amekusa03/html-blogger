# -*- coding: utf-8 -*-
import os
import re      
from json5 import load    
from pathlib import Path
import xml.etree.ElementTree as ET
import shutil

import html
from bs4 import BeautifulSoup
import logging
from logging import config, getLogger
from parameter import config,update_serial,get_serial
from cons_progressber import ProgressBar
from urllib.parse import unquote
from file_class import SmartFile

# logging設定
with open('./data/log_config.json5', 'r') as f:
  logging.config.dictConfig(load(f)) 
logger = getLogger(__name__)
# --- 設定 ---

# 入力元フォルダ
input_dir = config['link_html']['input_dir'].lstrip('./')
# アップロード先フォルダ
upload_dir = config['link_html']['upload_dir'].lstrip('./')
# メディアマネージャーフォルダ
media_manager_dir = config['link_html']['media_manager_dir'].lstrip('./')
# 画像拡張子
image_extensions = config['common']['image_extensions']
# html拡張子
html_extensions = config['common']['html_extensions']
# イメージリストファイル
link_list_file = config['link_html']['link_list_file']
link_list_file_html = config['link_html']['link_list_file_html']

def run(result_queue):
    """メディアマネージャーファイルを読み込む"""
    if not import_media_manager(result_queue):
        return False
    """HTMLファイル内の画像リンクをアップロード先に書き換える"""
    if not link_html(result_queue):
        return False
    return True


def import_media_manager(result_queue):
    
    """メディアマネージャーファイルを読み込む"""

    media_manager_files = list(Path(media_manager_dir).glob('*.*')) 
    if len(media_manager_files) > 1:
        logger.error(f"エラー: {media_manager_dir} に複数のファイルが見つかりました")
        return False
    elif len(media_manager_files) == 0:
        logger.error(f"メディアマネージャーファイルが見つかりません (検索対象: {media_manager_dir}/*.*")
        return False

    media_manager_filename = media_manager_files[0]
    try:
        with open(media_manager_filename, 'rb') as f: # Read as binary for MHTML parsing
            content_bytes = f.read()
    except Exception as e:
        logger.error(f"メディアマネージャーファイルの読み込みに失敗: {e}")
        return False   
        
    """メディアマネージャーファイルからBloggerの画像URLを抽出する"""
    image_url_list = {}
    pattern = re.compile(r'(https?://blogger\.googleusercontent\.com/[^"\'\s<>]+)')
    # テキストとして読み込んで正規表現で抽出 (MHTMLもテキストとして処理)
    try:
        content_str = content_bytes.decode('utf-8', errors='ignore')
        
        # MHTML等のQuoted-Printable対策: ソフト改行(=改行)を除去
        content_unfolded = content_str.replace('=\n', '').replace('=\r\n', '')
        
        # HTMLエンティティをデコード
        content_unfolded = html.unescape(content_unfolded)
        
        for match in pattern.finditer(content_unfolded):
            url = match.group(1)
            filename = unquote(url.split('/')[-1].split('?')[0])
            if filename not in image_url_list and filename.lower().endswith(tuple(image_extensions)):
                image_url_list[filename] = url
    except Exception as e:
        logger.error(f"テキスト解析中にエラーが発生しました: {e}")

    with open(link_list_file, 'w', encoding='utf-8') as f, \
        open(link_list_file_html, 'w', encoding='utf-8') as fh:
            fh.write('<html><body><h2>画像アップロードリスト</h2><ul>\n')
            for filename, url in image_url_list.items():
                f.write(f"{filename} : {url}\n")
                fh.write(f"<li>{filename} : <a href='{url}' target='_blank'>{url}</a></li>\n")
            fh.write('</ul></body></html>\n')       
        
    logger.info(f"イメージリストを {link_list_file}完了")
    return True

def link_html(result_queue):
    """HTMLファイル内の画像リンクをアップロード先に書き換える"""

    media_manager_link_list = {}
    with open(link_list_file, 'r', encoding='utf-8') as f:
        for line in f:
            filename, url = line.strip().split(' : ', 1)
            media_manager_link_list[filename] = url
            logger.debug(f"読み込み: {filename} -> {url}")
            
    html_unlink_list = []
    html_link_list = []
    for file_path in Path(input_dir).rglob('*'):
        # ファイルであり、かつ拡張子が指定のものに含まれるかチェック
        if file_path.is_file() and file_path.suffix.lower() in html_extensions:

            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, 'html.parser')
            # この記事に含まれるローカル画像タグをすべて見つける
            local_img_tags = [img for img in soup.find_all('img') if img.get('src') and not img.get('src').startswith(('http://', 'https://'))]

            # 画像パスを置換
            for img_tag in local_img_tags:
                img_filename = Path(img_tag.get('src')).name
                #blogger_url = unlink_list[img_filename]
                blogger_url = media_manager_link_list.get(img_filename)
                if not blogger_url:
                    html_unlink_list.append(img_filename)
                    continue
                img_tag['src'] = blogger_url
                html_link_list.append(img_filename)
                # 画像をリンクで囲む (Lightbox用)
                parent = img_tag.parent
                if parent.name != 'a':
                    new_a = soup.new_tag('a', href=blogger_url)
                    img_tag.wrap(new_a)
                
                logger.debug(f"  -> 画像リンク生成: <a href='{blogger_url}'><img src='{blogger_url}'></a>")
                logger.info(f"  -> 画像パス置換: {img_filename}")
            # 変更を保存
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(str(soup))
            sf = SmartFile(file_path)
            sf.status = '✔'
            sf.extensions = 'html'
            sf.disp_path = sf.name
            result_queue.put(sf)
            logger.info(f"HTMLファイルを更新しました: {file_path}")
    # 重複排除とソート
    html_link_list = list(set(html_link_list))   
    if html_link_list:
        logger.info("以下の画像リンクが更新されました:")
        for img_filename in html_link_list:
            logger.info(f" - {img_filename}")
    html_unlink_list = list(set(html_unlink_list))   
    if html_unlink_list:
        logger.warning("以下の画像リンクが見つかりませんでした:")
        for img_filename in html_unlink_list:
            logger.warning(f" - {img_filename}")
    return True


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
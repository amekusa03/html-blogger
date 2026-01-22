# -*- coding: utf-8 -*-
import os
import re
import xml.etree.ElementTree as ET
import shutil
from datetime import datetime
from pathlib import Path
from config import get_config

def load_keywords(xml_path):
    """XMLからキーワードを読み込む。返却値: (mast_keywords, hit_keywords, success_flag)"""
    try:
        if not os.path.exists(xml_path):
            print(f"エラー: {xml_path} が見つかりません。")
            return [], [], False
        
        tree = ET.parse(xml_path)
        root = tree.getroot()
        mast_keywords = [node.text for node in root.find('Mastkeywords').findall('word') if node.text]
        hit_keywords = [node.text for node in root.find('Hitkeywords').findall('word') if node.text]
        return mast_keywords, hit_keywords, True
    except Exception as e:
        print(f"XML読み込みエラー: {e}")
        return [], [], False

def process_html(file_path, mast_keywords, hit_keywords):
    """HTMLファイルにキーワードメタタグを注入。失敗時はバックアップから復元。"""
    
    # ✅ バックアップ作成
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        shutil.copy2(file_path, backup_path)
    except Exception as e:
        print(f"警告: バックアップ作成失敗 {file_path}: {e}")
        backup_path = None
    
    try:
        # ファイル読み込み
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 1. 改行・タブ削除（安定性向上のため）
        html_content = re.sub(r'[\r\n\t]+', '', html_content, flags=re.IGNORECASE)
        
        # 2. 既存の全 keywords metaタグを検索してキーワードを回収
        # 様々な書き方（順序入れ替え、/の有無）に対応する正規表現
        pattern = re.compile(r'<meta\s+[^>]*name=["\']keywords["\'][^>]*>', re.IGNORECASE)
        
        current_keywords = []
        
        # 既存タグから content の中身を抽出
        for match in pattern.findall(html_content):
            content_match = re.search(r'content=["\']([^"\']*)["\']', match, re.IGNORECASE)
            if content_match:
                words = [k.strip() for k in content_match.group(1).replace('，', ',').split(',') if k.strip()]
                current_keywords.extend(words)
        
        # 既存のキーワードタグを削除
        html_content = pattern.sub('', html_content)

        # 3. 新しいキーワードリストの作成（重複排除）
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

        # 4. 指定された順序でタグを作成（ここで初めて使用）
        new_tag = f'<meta name="keywords" content="{",".join(new_keywords_list)}">'

        # 5. 挿入処理
        if re.search(r'<head>', html_content, re.IGNORECASE):
            # <head>の直後に挿入
            html_content = re.sub(r'(<head.*?>)', r'\1\n' + new_tag, html_content, flags=re.IGNORECASE)
        else:
            # headがない場合は先頭に挿入
            html_content = new_tag + '\n' + html_content

        # 6. ファイル保存
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"完了: {file_path}")
        return True
        
    except Exception as e:
        print(f"エラー: {file_path} の処理に失敗しました: {e}")
        # ✅ バックアップがあれば復元
        if backup_path and os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, file_path)
                print(f"バックアップから復元しました: {file_path}")
            except Exception as restore_error:
                print(f"復元にも失敗しました！: {restore_error}")
        return False

def main():
    script_dir = Path(__file__).parent.resolve()
    xml_file = script_dir / get_config('ADD_KEYWORDS', 'XML_FILE')
    original_dir = script_dir / get_config('ADD_KEYWORDS', 'ORIGINAL_DIR')
    add_keywords_dir = script_dir / get_config('ADD_KEYWORDS', 'ADD_KEYWORDS_DIR')

    # ✅ 出力ディレクトリをリセット
    shutil.rmtree(str(add_keywords_dir), ignore_errors=True)
    try:
        shutil.copytree(str(original_dir), str(add_keywords_dir))
    except Exception as e:
        print(f"エラー: ディレクトリコピーに失敗しました: {e}")
        return
    
    # ✅ ファイル存在確認
    if not xml_file.exists():
        print(f"エラー: {xml_file} が見つかりません。")
        return
    if not add_keywords_dir.exists():
        print(f"エラー: {add_keywords_dir} ディレクトリが見つかりません。")
        return

    # ✅ キーワード読み込み（戻り値チェック）
    mast_kws, hit_kws, success = load_keywords(str(xml_file))
    
    if not success:
        print("警告: キーワード読み込みに失敗しました。キーワード注入をスキップします。")
        return
    
    if not mast_kws and not hit_kws:
        print("警告: キーワードが見つかりません。")

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
    
    print("-" * 30)
    print(f"【処理完了】")
    print(f"成功: {processed_count} ファイル")
    if failed_count > 0:
        print(f"失敗: {failed_count} ファイル")

if __name__ == "__main__":
    main()

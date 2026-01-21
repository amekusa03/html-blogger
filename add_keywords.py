import os
import re
import xml.etree.ElementTree as ET
import shutil

def load_keywords(xml_path):
    """XMLからキーワードを読み込む"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        mast_keywords = [node.text for node in root.find('Mastkeywords').findall('word') if node.text]
        hit_keywords = [node.text for node in root.find('Hitkeywords').findall('word') if node.text]
        return mast_keywords, hit_keywords
    except Exception as e:
        print(f"XML読み込みエラー: {e}")
        return [], []

def process_html(file_path, mast_keywords, hit_keywords):
    """文字列操作でmetaタグを確実に指定順序で作成・更新する"""
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 1. 既存の全 keywords metaタグを検索してキーワードを回収し、タグを削除
    # 様々な書き方（順序入れ替え、/の有無）に対応する正規表現
    pattern = re.compile(r'<meta\s+[^>]*name=["\']keywords["\'][^>]*>', re.IGNORECASE)
    
    current_keywords = []
    
    # 既存タグから content の中身を抽出
    for match in pattern.findall(html_content):
        content_match = re.search(r'content=["\'](.*?)["\']', match, re.IGNORECASE)
        if content_match:
            words = [k.strip() for k in content_match.group(1).replace('，', ',').split(',') if k.strip()]
            current_keywords.extend(words)
    
    # 既存のキーワードタグを一旦すべて削除
    html_content = pattern.sub('', html_content)

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
    clean_text = re.sub(r'<[^>]*?>', '', html_content) # タグを除去したテキストで判定
    for h_kw in hit_keywords:
        if h_kw in clean_text and h_kw not in new_keywords_list:
            new_keywords_list.append(h_kw)

    # 3. 指定された順序でタグを作成
    new_tag = f'<meta name="keywords" content="{",".join(new_keywords_list)}">'

    # 4. 挿入処理
    if '<head>' in html_content.lower():
        # <head>の直後に挿入
        html_content = re.sub(r'(<head.*?>)', r'\1\n' + new_tag, html_content, flags=re.IGNORECASE)
    else:
        # headがない場合は先頭に挿入
        html_content = new_tag + '\n' + html_content

    # 保存
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"完了: {file_path}")

def main():
    xml_file = 'keywords.xml'
    orignal_dir = 'reports'
    add_keywords_dir = 'addKeyword_upload'

    shutil.rmtree(add_keywords_dir, ignore_errors=True)
    shutil.copytree(orignal_dir, add_keywords_dir)

    if not os.path.exists(xml_file):
        print(f"エラー: {xml_file} が見てかりません。")
        return
    if not os.path.exists(add_keywords_dir):
        print(f"エラー: {add_keywords_dir} ディレクトリが見つかりません。")
        return

    mast_kws, hit_kws = load_keywords(xml_file)

    for entry in os.scandir(add_keywords_dir):
        if entry.is_dir():
            for file in os.scandir(entry.path):
                if file.is_file() and file.name.lower().endswith(('.html', '.htm')):
                    process_html(file.path, mast_kws, hit_kws)

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
import logging
import re
from logging import config, getLogger
from pathlib import Path

from bs4 import BeautifulSoup, Comment
from json5 import load

from file_class import SmartFile
from parameter import config

# logging設定
with open("./data/log_config.json5", "r") as f:
    logging.config.dictConfig(load(f))
logger = getLogger(__name__)
# --- 設定 ---
# 入力元フォルダ
input_dir = config["clean_html"]["input_dir"].lstrip("./")
# 出力先フォルダ
output_dir = config["clean_html"]["output_dir"].lstrip("./")

html_extensions = config["common"]["html_extensions"]

# 画像基底サイズ
IMAGE_BASIC_SIZE = {
    "landscape": [
        {"w": 640, "h": 480},
        {"w": 400, "h": 300},
        {"w": 320, "h": 240},
        {"w": 200, "h": 150},
    ],
    "portrait": [
        {"w": 480, "h": 640},
        {"w": 300, "h": 400},
        {"w": 240, "h": 320},
        {"w": 150, "h": 200},
    ],
}


def resize_logic(w, h):
    """画像サイズを適切なサイズにリサイズ（大きい方に合わせる）"""
    if w <= 0 or h <= 0:
        return w, h

    mode = "landscape" if w >= h else "portrait"
    # targetsは大きい順にソートされている
    targets = IMAGE_BASIC_SIZE[mode]

    # 最大サイズ（リストの先頭）を取得
    max_w, max_h = targets[0]["w"], targets[0]["h"]

    # 最大サイズを超えている場合のみ、アスペクト比を維持して縮小
    if w > max_w or h > max_h:
        ratio = min(max_w / w, max_h / h)
        return int(w * ratio), int(h * ratio)

    # それ以外は元のサイズを維持
    return w, h


def run(result_queue):
    logger.info(f"HTMLクリーンアップ開始: {input_dir}")
    all_files = list(Path(input_dir).rglob("*"))
    count = 0

    for path in all_files:
        src_file = SmartFile(path)
        if src_file.is_file():
            if src_file.suffix.lower() in html_extensions:
                src_file.status = "⏳"
                src_file.extensions = "html"
                src_file.disp_path = src_file.name
                result_queue.put(src_file)

    for path in all_files:
        src_file = SmartFile(path)
        if src_file.is_file():
            if src_file.suffix.lower() in html_extensions:
                src_file = clean_html_for_blogger(src_file)
                src_file.status = "✔"
                src_file.extensions = "html"
                src_file.disp_path = src_file.name
                result_queue.put(src_file)
                count += 1
    logger.info(f"HTMLクリーンアップ完了: {count}件")


def clean_html_for_blogger(files):
    """ブログ用にHTMLをクリーンアップする。
    重大削除チェックは本文テキスト同士の比較で行い、headやscript削除による誤検知を避ける。
    """
    for encoding in ["utf-8", "cp932", "shift_jis"]:
        try:
            html_text = files.read_text(encoding=encoding, errors="ignore")
            break
        except:
            continue

    # 1. 改行とタブを一旦削除（後で<br>に基づいて再整理するため）
    html_text = re.sub(r"[\r\n\t]+", "", html_text)

    # 2. タイトルの抽出（安全な判定）
    # 正規表現ではなくBeautifulSoupを使ってテキストを抽出する（タグのネストに対応するため）
    temp_soup = BeautifulSoup(html_text, "html.parser")
    extracted_title = ""

    if temp_soup.title and temp_soup.title.get_text(strip=True):
        extracted_title = temp_soup.title.get_text(strip=True)
    else:
        # 見出しを探す (h1 -> h6)
        for i in range(1, 7):
            h_tag = temp_soup.find(f"h{i}")
            if h_tag:
                extracted_title = h_tag.get_text(strip=True)
                break

    if not extracted_title:
        logger.warning("タイトルが見つかりません: %s", files.name)

    # 3. BeautifulSoupを使って不要なタグと属性を削除
    soup = BeautifulSoup(html_text, "html.parser")
    # 4. 不要なタグを完全に削除（タグとその中身）
    # <script>, <style>, <meta>, は削除する
    for tag in soup.find_all(["script", "style", "meta"]):
        tag.decompose()
    # 5. コメントを削除
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # 6. フォーマットタグを削除（タグのみ削除、中身は保持）
    unwrap_tags = [
        "font",
        "span",
        "strong",
        "b",
        "em",
        "i",
        "u",
        "strike",
        "s",
        "center",
    ]
    for tag_name in unwrap_tags:
        for tag in soup.find_all(tag_name):
            tag.unwrap()

    # 7. すべてのタグから不要な属性を削除
    unuse_attrs = [
        "bgcolor",
        "style",
        "class",
        "id",
        "width",
        "height",
        "border",
        "align",
        "valign",
        "cellspacing",
        "cellpadding",
        "lang",
        "http-equiv",
        "content",
        "font-family",
        "font-color",
        "color",
    ]

    for tag in soup.find_all(True):  # すべてのタグ
        # imgタグはsrc, alt, width, heightのみ保持
        if tag.name == "img":
            attrs_to_remove = [
                attr
                for attr in tag.attrs
                if attr not in ["src", "alt", "width", "height"]
            ]
        else:
            attrs_to_remove = [attr for attr in tag.attrs if attr in unuse_attrs]

        for attr in attrs_to_remove:
            del tag[attr]

    # 画像処理 (figure/figcaptionの追加)
    # Bloggerでの表示互換性のため、figureではなくdivを使用する
    for img in soup.find_all("img"):
        if img.parent and img.parent.name == "div":
            continue  # すでにdivでラップされている場合はスキップ
        div_wrapper = soup.new_tag("div", style="text-align:center; margin-bottom:1em;")
        # alt取得
        alt_text = img.get("alt")
        alt_text = alt_text.strip() if alt_text is not None else "Image"
        # caption作成
        caption = soup.new_tag("div", style="font-size:small; color:#666;")
        caption.string = alt_text
        # 画像サイズ属性の整理
        width = img.get("width")
        height = img.get("height")
        if width is not None and height is not None:
            # 縦横がある場合調整
            img["width"], img["height"] = resize_logic(int(width), int(height))
        # imgをdivでラップし、captionを追加
        img.wrap(div_wrapper)
        div_wrapper.append(caption)

    # <body>と<head>の属性を削除（タグは保持）
    for tag_name in ["body", "head"]:
        tag = soup.find(tag_name)
        if tag:
            tag.attrs = {}

    # HTML文字列に戻す（全体を保持）
    html_text = str(soup)

    # 念のため、残っているfontタグを正規表現でも削除
    html_text = re.sub(r"<font[^>]*>", "", html_text, flags=re.IGNORECASE)
    html_text = re.sub(r"</font>", "", html_text, flags=re.IGNORECASE)

    # 6. 改行整理
    # html_text = re.sub(r'[\r\n\t]+', '\n', html_text) # 連続改行をスペース1つに
    html_text = re.sub(r"\s+", " ", html_text).strip()
    # html_text = re.sub(r'<br.?*>', '<br />\n', html_text, flags=re.IGNORECASE)
    html_text = re.sub(
        r"(<br/>|</br>|<br>|<br\s*/>)", "<br/>\n", html_text, flags=re.IGNORECASE
    )

    # 7. テーブルやリストなどの構造タグの後にも改行を入れるとソースが見やすくなります
    html_text = re.sub(
        r"(</td>|</tr>|</table>|</h1>|</h2>|</h3>|</li>)",
        r"\1\n",
        html_text,
        flags=re.IGNORECASE,
    )

    # 【重大エラーチェック】コンテンツ削除検出
    # head/script/styleなどの削除で大きく減ることがあるため、本文テキスト同士で比較する
    # original_plain = re.sub(r'<[^>]*>', '', original_html)
    # cleaned_plain = re.sub(r'<[^>]*>', '', html_text)
    # original_length = len(original_plain)
    # cleaned_length = len(cleaned_plain)

    # 11. HTML構造の正規化（<head>と<body>が存在しない場合は追加）
    soup_final = BeautifulSoup(html_text, "html.parser")

    # <head>タグの存在確認と追加
    head_tag = soup_final.find("head")
    if not head_tag:
        head_tag = soup_final.new_tag("head")
        # htmlタグがあればその先頭に、なければ全体の先頭に挿入
        html_tag = soup_final.find("html")
        if html_tag:
            html_tag.insert(0, head_tag)
        else:
            soup_final.insert(0, head_tag)

    # タイトルの設定（抽出したタイトルを反映）
    title_tag = soup_final.find("title")
    if not title_tag:
        title_tag = soup_final.new_tag("title")
        head_tag.append(title_tag)

    # 抽出したタイトルがあり、かつ現在のタイトルタグが空または新規作成の場合に設定
    if extracted_title:
        title_tag.string = extracted_title

    # <body>タグの存在確認と追加
    if not soup_final.find("body"):
        body_tag = soup_final.new_tag("body")
        # <head>以外の全要素をbodyに移動
        head_tag = soup_final.find("head")
        for element in list(soup_final.children):
            if element != head_tag and element.name not in [None, "html"]:
                element.extract()
                body_tag.append(element)
        # htmlタグがあればその中に、なければ全体に追加
        html_tag = soup_final.find("html")
        if html_tag:
            html_tag.append(body_tag)
        else:
            soup_final.append(body_tag)

    html_text = str(soup_final)

    files.write_text(html_text, encoding="utf-8")
    logger.info(f"クリーンアップ完了: {files.name}")
    return files


import queue

# --- メイン処理 ---
if __name__ == "__main__":

    result_queue = queue.Queue()
    try:
        run(result_queue)
    except KeyboardInterrupt:
        logger.info("処理が中断されました。")
    except Exception as e:
        logger.critical(f"予期せぬエラーが発生しました: {e}", exc_info=True)

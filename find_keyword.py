# -*- coding: utf-8 -*-
"""find_keyword.py
HTMLファイルからキーワードを抽出し、<search>タグを追加するモジュール
"""
import logging
import queue
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from file_class import SmartFile
from parameter import config

logger = logging.getLogger(__name__)

# 入力元フォルダ
input_dir = config["find_keyword"]["input_dir"].lstrip("./")
# 出力先フォルダ
output_dir = config["find_keyword"]["output_dir"].lstrip("./")
html_extensions = config["common"]["html_extensions"]

xml_file = config["find_keyword"]["keywords_xml_file"]


class KeywordManager:
    """キーワードマップを管理するクラス"""

    def __init__(self):
        self.mast_keyword_map = None
        self.hit_keyword_map = None

    def load_keywords(self):
        """XMLからキーワードを読み込み、検索/登録マップを作成する。"""
        self.mast_keyword_map = {}
        self.hit_keyword_map = {}

        try:
            if not Path(xml_file).exists():
                logger.error("%s が見つかりません。", xml_file)
                return False
            tree = ET.parse(str(Path(xml_file)))
            root = tree.getroot()

            # Mastkeywords
            mast_node = root.find("Mastkeywords")
            if mast_node is not None:
                for node in mast_node.findall("word"):
                    _create_keyword_map(node.text, self.mast_keyword_map)

            # Hitkeywords
            hit_node = root.find("Hitkeywords")
            if hit_node is not None:
                for node in hit_node.findall("word"):
                    _create_keyword_map(node.text, self.hit_keyword_map)

        except (FileNotFoundError, ET.ParseError) as e:
            logger.error("XML読み込みエラー: %s", e, exc_info=True)
            return False
        return True


keyword_manager = KeywordManager()


def run(queue_obj):
    """HTMLファイルにキーワードを注入するメイン関数"""
    logger.info("キーワード注入開始: %s -> %s", input_dir, output_dir)
    all_files = list(Path(input_dir).rglob("*"))
    count = 0

    for path in all_files:
        src_file = SmartFile(path)
        if src_file.is_file():
            if src_file.suffix.lower() in html_extensions:
                src_file.status = "⏳"
                src_file.extensions = "html"
                src_file.disp_path = src_file.name
                queue_obj.put(src_file)

    for path in all_files:
        src_file = SmartFile(path)
        if src_file.is_file():
            if src_file.suffix.lower() in html_extensions:
                src_file = add_keywords_to_content(src_file)
                src_file.status = "✔"
                src_file.extensions = "html"
                src_file.disp_path = src_file.name
                queue_obj.put(src_file)
                count += 1
    logger.info("キーワード注入完了: %d件", count)


def _create_keyword_map(text, target_map):
    """キーワードテキストを解析し、検索/登録マップに追加するヘルパー関数"""
    if not text or not text.strip():
        return

    text = text.strip()

    # `Python(パイソン,py)` の形式を `Python:パイソン,py` に正規化
    text = re.sub(r"\(([^)]+)\)", r":\1", text)

    if ":" in text:
        parts = text.split(":", 1)
        register_word = parts[0].strip()
        aliases_str = parts[1]
    else:
        register_word = text
        aliases_str = ""

    # 登録ワード自体も検索対象に含める
    search_words = [register_word]

    # エイリアスをカンマ(全角/半角)で分割して追加
    aliases = [
        alias.strip() for alias in re.split(r"[,，]", aliases_str) if alias.strip()
    ]
    search_words.extend(aliases)

    # 重複を削除しつつ順序を維持
    unique_search_words = list(dict.fromkeys(search_words))

    for search_word in unique_search_words:
        if search_word:  # 空文字は登録しない
            target_map[search_word] = register_word


def add_keywords_to_content(files):
    """HTMLコンテンツにキーワードを<search>タグで注入する。"""
    if (
        keyword_manager.mast_keyword_map is None
        or keyword_manager.hit_keyword_map is None
    ):
        if not keyword_manager.load_keywords():
            logger.warning(
                "登録キーワード読み込みに失敗しました。キーワード注入をスキップします。"
            )
            return files

    if not keyword_manager.mast_keyword_map and not keyword_manager.hit_keyword_map:
        logger.warning("登録キーワードが見つかりません。")

    html_content = files.read_text(encoding="utf-8", errors="ignore")

    # 1. 既存の <search> タグからキーワードを抽出
    current_keywords = []
    search_match = re.search(
        r"<search[^>]*>([^<]*)</search>", html_content, re.IGNORECASE
    )
    if search_match:
        keywords_str = search_match.group(1).strip()
        words = [
            k.strip() for k in keywords_str.replace("，", ",").split(",") if k.strip()
        ]
        current_keywords.extend(words)
        # 既存の <search> タグを削除
        html_content = re.sub(
            r"<search[^>]*>[^<]*</search>", "", html_content, flags=re.IGNORECASE
        )

    # 1.5 本文中の「キーワード: ...」から抽出
    body_keywords = []
    # タグを改行に置換してテキスト抽出（行単位での解析のため）
    text_for_parsing = re.sub(r"<[^>]+>", "\n", html_content)
    # 「キーワード: A, B」パターンを検索
    kw_matches = re.finditer(r"キーワード[:：]\s*([^\n\r]+)", text_for_parsing)
    for match in kw_matches:
        kw_str = match.group(1).strip()
        # カンマ、読点などで分割
        words = [k.strip() for k in re.split(r"[,，、]", kw_str) if k.strip()]
        body_keywords.extend(words)

    # 抽出元の行を削除 (空行が残らないように改行もケア)
    # 本文からキーワード行を削除すると空のタグが残る場合があるため、削除処理をスキップします
    # html_content = re.sub(r'キーワード[:：]\s*[^\n\r]+[\r\n]*', '', html_content)

    # 2. キーワードをすべて集める
    all_keywords = []

    # 必須キーワード (mast_keywords)
    all_keywords.extend(list(keyword_manager.mast_keyword_map.values()))

    clean_text = re.sub(r"<[^>]*?>", "", html_content)  # 本文からヒットキーワード
    for search_word, register_word in keyword_manager.hit_keyword_map.items():
        if search_word in clean_text:
            all_keywords.append(register_word)

    all_keywords.extend(current_keywords)  # 既存キーワード
    all_keywords.extend(body_keywords)  # 本文から抽出したキーワード

    # 3. 重複を削除しつつ、順序を維持
    # 空文字とカンマを除外
    cleaned_keywords = []
    for k in all_keywords:
        if k:
            k_clean = k.strip().strip(",").strip()
            if k_clean:
                cleaned_keywords.append(k_clean)
    new_keywords_list = list(dict.fromkeys(cleaned_keywords))

    if new_keywords_list:
        logger.debug("最終的なキーワードリスト: %s", new_keywords_list)

        search_tag = "".join([f"<search>{kw}</search>" for kw in new_keywords_list])
        # 4. <head>内の<title>の後に挿入
        if re.search(r"</title>", html_content, re.IGNORECASE):
            html_content = re.sub(
                r"(</title>)",
                r"\1\n" + search_tag,
                html_content,
                count=1,
                flags=re.IGNORECASE,
            )
        elif re.search(r"<head>", html_content, re.IGNORECASE):
            html_content = re.sub(
                r"(<head[^>]*>)",
                r"\1\n" + search_tag,
                html_content,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            html_content = search_tag + "\n" + html_content

    with open(files, "w", encoding="utf-8") as file:
        file.write(html_content)
    logger.info("キーワード追加: %s", files.name)
    return files


# --- メイン処理 ---
if __name__ == "__main__":

    result_queue = queue.Queue()
    try:
        run(result_queue)
    except KeyboardInterrupt:
        logger.info("処理が中断されました。")
    except (OSError, IOError, ET.ParseError) as e:
        logger.critical("予期せぬエラーが発生しました: %s", e, exc_info=True)

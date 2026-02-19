# -*- coding: utf-8 -*-
import html
import logging
import re
import shutil
from logging import config, getLogger
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup
from json5 import load

from file_class import SmartFile
from parameter import config

# logging設定
with open("./data/log_config.json5", "r") as f:
    logging.config.dictConfig(load(f))
logger = getLogger(__name__)
# --- 設定 ---

# 入力元フォルダ
input_dir = config["link_html"]["input_dir"].lstrip("./")
# 履歴フォルダ
history_dir = config["link_html"]["history_dir"].lstrip("./")
# アップロードフォルダ（リンクできれば画像アップロード成功とみなす）
upload_dir = config["upload_image"]["upload_dir"].lstrip("./")
# メディアマネージャーフォルダ
media_manager_dir = config["link_html"]["media_manager_dir"].lstrip("./")
# 画像拡張子
image_extensions = config["common"]["image_extensions"]
# html拡張子
html_extensions = config["common"]["html_extensions"]
# イメージリストファイル
link_list_file = config["link_html"]["link_list_file"]
link_list_file_html = config["link_html"]["link_list_file_html"]

unlink_image_list = []
link_image_list = []


def run(result_queue):
    global unlink_image_list, link_image_list
    unlink_image_list = []
    link_image_list = []

    """メディアマネージャーファイルを読み込む"""
    if not import_media_manager():
        return False
    """HTMLファイル内の画像リンクをアップロード先に書き換える"""
    if not link_html(result_queue):
        return False
    """HTML内の画像リンクを履歴フォルダに移動する"""
    if not history(result_queue):
        return False
    if len(unlink_image_list) > 0:
        return unlink_image_list
    return True


def import_media_manager():
    """メディアマネージャーファイルを読み込む"""

    media_manager_files = list(Path(media_manager_dir).glob("*.*"))
    if len(media_manager_files) > 1:
        logger.error(f"エラー: {media_manager_dir} に複数のファイルが見つかりました")
        return False
    elif len(media_manager_files) == 0:
        logger.error(
            f"メディアマネージャーファイルが見つかりません (検索対象: {media_manager_dir}/*.*"
        )
        return False

    media_manager_filename = media_manager_files[0]
    try:
        with open(
            media_manager_filename, "rb"
        ) as f:  # Read as binary for MHTML parsing
            content_bytes = f.read()
    except Exception as e:
        logger.error(f"メディアマネージャーファイルの読み込みに失敗: {e}")
        return False

    """メディアマネージャーファイルからBloggerの画像URLを抽出する"""
    image_url_list = {}
    pattern = re.compile(r'(https?://blogger\.googleusercontent\.com/[^"\'\s<>]+)')
    # テキストとして読み込んで正規表現で抽出 (MHTMLもテキストとして処理)
    try:
        content_str = content_bytes.decode("utf-8", errors="ignore")

        # MHTML等のQuoted-Printable対策: ソフト改行(=改行)を除去
        content_unfolded = content_str.replace("=\n", "").replace("=\r\n", "")

        # HTMLエンティティをデコード
        content_unfolded = html.unescape(content_unfolded)

        for match in pattern.finditer(content_unfolded):
            url = match.group(1)
            filename = unquote(url.split("/")[-1].split("?")[0])
            if filename not in image_url_list and filename.lower().endswith(
                tuple(image_extensions)
            ):
                image_url_list[filename] = url
    except Exception as e:
        logger.error(f"テキスト解析中にエラーが発生しました: {e}")

    # フォルダがなければ作成
    link_list_file_path = Path(link_list_file)
    link_list_file_path.parent.mkdir(parents=True, exist_ok=True)
    link_list_file_html_path = Path(link_list_file_html)
    link_list_file_html_path.parent.mkdir(parents=True, exist_ok=True)

    with open(link_list_file, "w", encoding="utf-8") as f, open(
        link_list_file_html,
        "w",
        encoding="utf-8",  # link_list_file_htmlは確認用（なくても問題ない）
    ) as fh:
        fh.write("<html><body><h2>画像アップロードリスト</h2><ul>\n")
        for filename, url in image_url_list.items():
            f.write(f"{filename} : {url}\n")
            fh.write(
                f'<li>{filename} : <a href="{url}" target="_blank">{url}</a></li>\n'
            )
        fh.write("</ul></body></html>\n")

    logger.info(f"イメージリストを {link_list_file}完了")
    return True


def link_html(result_queue):
    """HTMLファイル内の画像リンクをアップロード先に書き換える"""
    global unlink_image_list, link_image_list

    media_manager_link_list = {}
    with open(link_list_file, "r", encoding="utf-8") as f:
        for line in f:
            filename, url = line.strip().split(" : ", 1)
            media_manager_link_list[filename] = url
            logger.debug(f"読み込み: {filename} -> {url}")

    for file_path in Path(input_dir).rglob("*"):
        # ファイルであり、かつ拡張子が指定のものに含まれるかチェック
        if file_path.is_file() and file_path.suffix.lower() in html_extensions:

            in_html_unlink_image_list = []
            in_html_link_image_list = []
            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, "html.parser")
            # この記事に含まれるローカル画像タグをすべて見つける
            local_img_tags = [
                img
                for img in soup.find_all("img")
                if img.get("src")
                and not img.get("src").startswith(("http://", "https://"))
            ]

            # html内の画像パスを置換
            for img_tag in local_img_tags:
                img_filename = Path(img_tag.get("src")).name
                # blogger_url = unlink_list[img_filename]
                blogger_url = media_manager_link_list.get(img_filename)
                sf = SmartFile(img_filename)
                sf.disp_path = img_filename
                sf.extensions = "image"
                if blogger_url:
                    sf.status = "✔"
                    in_html_link_image_list.append(sf)
                else:
                    sf.status = "✖"
                    in_html_unlink_image_list.append(sf)
                if not blogger_url:
                    continue
                img_tag["src"] = blogger_url
                # 画像をリンクで囲む (Lightbox用)
                parent = img_tag.parent
                if parent.name != "a":
                    new_a = soup.new_tag("a", href=blogger_url)
                    img_tag.wrap(new_a)

                logger.debug(
                    f'  -> 画像リンク生成: <a href="{blogger_url}"><img src="{blogger_url}"></a>'
                )
                logger.info(f"  -> 画像パス置換: {img_filename}")
            # 変更を保存
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(soup))
            sf = SmartFile(file_path.name)
            sf.disp_path = file_path.name
            if in_html_unlink_image_list:
                sf.status = "✖"
            else:
                sf.status = "✔"
            sf.extensions = "html"
            result_queue.put(sf)
            logger.info(f"HTMLファイルを更新しました: {file_path}")
            if in_html_unlink_image_list:
                unlink_image_list.extend(in_html_unlink_image_list)
            if in_html_link_image_list:
                link_image_list.extend(in_html_link_image_list)
    return True


def history(result_queue):
    """手動アップロード用に画像を準備する"""
    global unlink_image_list, link_image_list
    # 重複排除とソート
    unlink_image_list = list(set(unlink_image_list))
    link_image_list = list(set(link_image_list))

    if upload_dir == history_dir:
        logger.error(
            "エラー: UPLOAD_DIR と HISTORY_DIR が同じフォルダに設定されています。異なるフォルダを指定してください。"
        )
        return False
    # メディアマネージャー内の画像アンリンクを収集
    for sf in unlink_image_list:
        file_path = Path(input_dir) / sf.name  # GUIに表示はinput(work)ココ
        smart_file = SmartFile(
            file_path
        )  # Link画像は履歴移動後にアップロードされるため、ここではSmartFileを作成しない
        smart_file.status = "✖"
        smart_file.extensions = "image"
        smart_file.disp_path = smart_file.name
        result_queue.put(smart_file)
        if sf.name in link_image_list:
            logger.error(
                f"画像リンクの状態が矛盾しています: {sf.name} はリンクありとなし両方に存在します。"
            )
    if unlink_image_list:
        logger.warning("以下の画像リンクが見つかりませんでした:")
        for sf in unlink_image_list:
            logger.warning(f" - {sf.name}")
    # メディアマネージャー内の画像リンクを収集
    count = 0
    for sf in link_image_list:
        # 履歴に移動実行
        file_path = Path(upload_dir) / sf.name  # アップロードの完了を見たいのでココ
        dest_path = Path(history_dir) / sf.name  # アップロードの完了を見たいのでココ
        if (
            file_path.exists()
        ):  # アップロード前にファイルが存在する場合は移動する（もう履歴済みはない）
            shutil.move(file_path, dest_path)
        # GUI用
        file_path = Path(input_dir) / sf.name  # GUIに表示はinput(work)ココ
        smart_file = SmartFile(
            file_path
        )  # Link画像は履歴移動後にアップロードされるため、ここではSmartFileを作成しない
        smart_file.status = "✔"
        smart_file.extensions = "image"
        smart_file.disp_path = smart_file.name
        result_queue.put(smart_file)
        count += 1
    logger.info(f"{count} 枚の画像を {history_dir} に移動しました。")
    # unlink_image_list link_image_list両方にないものはどうでも良いファイルと判断して無視する
    return True


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

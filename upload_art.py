# -*- coding: utf-8 -*-
import logging
import queue
import random
import shutil
import time
from datetime import datetime, timedelta, timezone
from logging import config, getLogger
from pathlib import Path

from bs4 import BeautifulSoup
from googleapiclient.errors import HttpError
from json5 import load

from auth_google import get_blogger_service
from cons_progressber import ProgressBar
from file_class import SmartFile
from parameter import config, get_serial, to_bool, update_serial

# --- ロギング設定 ---
# logging設定
with open("./data/log_config.json5", "r") as f:
    logging.config.dictConfig(load(f))
logger = getLogger(__name__)


# --- 設定 ---

# 入力元フォルダ
input_dir = config["upload_art"]["input_dir"].lstrip("./")
# アップロード先フォルダ
upload_dir = config["upload_art"]["upload_dir"].lstrip("./")
# 履歴フォルダ
history_dir = config["upload_art"]["history_dir"].lstrip("./")
# html拡張子
html_extensions = config["common"]["html_extensions"]

blog_id = config["upload_art"]["blog_id"]
delay_seconds = float(config["upload_art"]["delay_seconds"])
max_posts_per_run = int(config["upload_art"]["max_posts_per_run"])
max_retries = int(config["upload_art"]["max_retries"])

test_mode = to_bool(config["common"]["test_mode"])

# 日本時間 (JST) の設定
JST = timezone(timedelta(hours=9))
service = None
last_execution_time = 0


def move_upload_file(result_queue):
    """アップロード用にHTMLを準備する"""
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    count = 0
    # 2. input_dir内を探索
    # rglob('*') を使えばサブフォルダ内も探せます。直下だけなら glob('*')
    if input_dir == upload_dir:
        logger.error(
            "エラー: input_dir と upload_dir が同じフォルダに設定されています。異なるフォルダを指定してください。"
        )
        return False

    for file_path in Path(input_dir).rglob("*"):
        # ファイルであり、かつ拡張子が指定のものに含まれるかチェック
        if file_path.is_file() and file_path.suffix.lower() in html_extensions:
            dest_path = Path(upload_dir) / file_path.name
            # 3. コピー実行（メタデータも保持するcopy2を推奨）
            shutil.copy2(file_path, dest_path)
            count += 1

            smart_file = SmartFile(dest_path)
            smart_file.status = "⌛"
            smart_file.extensions = "html"
            smart_file.disp_path = dest_path.name
            result_queue.put(smart_file)
    logger.info(f"{count} 枚のhtmlを {upload_dir} にアップロードしました。")
    return True


def move_history_file(src_path):
    """履歴用にHTMLを準備する"""
    Path(history_dir).mkdir(parents=True, exist_ok=True)

    try:
        dest_path = Path(history_dir) / src_path.name
        # 3. コピー実行（メタデータも保持するcopy2を推奨）
        shutil.move(src_path, dest_path)
        logger.info(f"履歴移動: {src_path.name}")
        return True
    except Exception as e:
        logger.error(f"履歴移動失敗: {src_path.name} - {e}")
        return False


def ready_upload():
    """アップロード準備チェック"""

    # 【重大エラーチェック】BLOG_ID 設定確認
    if blog_id == "あなたのブログID" or not blog_id:
        logger.error(
            "BLOG_ID が設定されていません。config.json5 の [UPLOAD_ART] セクションを確認してください。"
        )
        return False

    # 【重大エラーチェック】認証情報の事前確認
    global service

    if service is None:
        try:
            service = get_blogger_service()
        except FileNotFoundError as e:
            logger.error(f"{e}")
            return False
        except Exception as e:
            logger.error(f"Google認証に失敗しました: {e}")
            logger.error("認証情報（credentials.json）が有効か確認してください。")
            return False
    return True


def upload_art(art_html):
    """Blogger にアップロード"""
    try:
        # htnlファイル（ready_upload フォルダ内）
        if not art_html:
            logger.info(f"アップロードする記事が見つかりません。")
            return True

        # pbar = ProgressBar(count, prefix='Upload art')

        global last_execution_time
        elapsed_time = time.time() - last_execution_time

        # ゆらぎを追加 (0.5秒〜3.0秒)
        jitter = random.uniform(0.5, 3.0)

        if elapsed_time < delay_seconds:
            wait_time = delay_seconds - elapsed_time + jitter
            logger.info(f"待機中... ({wait_time:.1f}秒)")
            time.sleep(wait_time)
        elif last_execution_time > 0:
            # 規定時間を経過していても、機械的な動作を避けるためランダムに待機
            logger.info(f"待機中... ({jitter:.1f}秒)")
            time.sleep(jitter)

        # タイトルは<title>タグから抽出
        soup = BeautifulSoup(art_html, "html.parser")
        title_tag = soup.find("title")
        title = (
            title_tag.get_text(strip=True)
            if title_tag and title_tag.get_text(strip=True)
            else ""
        )

        # 公開日時を<time>タグから抽出
        # published_date の取得
        # time_tagがない場合は、現在時刻をタイムゾーン付きで取得
        # 公開日時を<time>タグから抽出
        time_tag = soup.find("time")
        date_part = (
            time_tag.get("datetime")[:10]
            if (time_tag and time_tag.get("datetime"))
            else datetime.now(JST).strftime("%Y-%m-%d")
        )
        published = f"{date_part}T00:00:00+09:00"

        # ラベルを<category>タグから抽出
        labels_tags = soup.find_all("search")
        labels = ",".join([tag.get_text(strip=True) for tag in labels_tags])

        # 位置情報を<blogger:location>から抽出
        location_name_tag = soup.find("location_name")
        latitude_tag = soup.find("latitude")
        longitude_tag = soup.find("longitude")

        if (
            location_name_tag is not None
            and latitude_tag is not None
            and longitude_tag is not None
        ):
            try:
                location_data = {
                    "name": (
                        location_name_tag.text.strip() if location_name_tag.text else ""
                    ),
                    "lat": float(latitude_tag.text),
                    "lng": float(longitude_tag.text),
                }
            except ValueError:
                logger.warning(
                    f"位置情報の座標変換に失敗しました。位置情報はスキップされます。 (タイトル: {title})"
                )
                location_data = None
        else:
            location_data = None
        # 本文は<body>タグの中身
        body_tag = soup.find("body")
        content = (
            "".join(str(child) for child in body_tag.children).strip()
            if body_tag
            else str(soup)
        )

        body = {
            "kind": "blogger#post",
            "title": title,
            "content": content,
            "labels": labels,
            "blog": {"id": blog_id},
            "published": published,
        }

        # 公開日時があれば追加
        if published:
            body["published"] = published

        # 位置情報があれば追加
        if location_data:
            body["location"] = location_data

        logger.info("=" * 50)
        logger.info(f"アップロード開始: {title}")
        logger.info(f"公開日: {published}")
        logger.info(f"BLOG_ID: {blog_id}")
        logger.info(f"ラベル: {labels}")

        global service
        # API呼び出しのリトライ処理
        success = False
        for attempt in range(max_retries):
            try:
                if not test_mode:
                    # 投稿
                    response = (
                        service.posts()
                        .insert(blogId=blog_id, body=body, isDraft=True)
                        .execute()
                    )
                    logger.info(f"投稿ID: {response.get('id')}")
                else:
                    logger.info("【テストモード】API呼び出しをスキップします")

                logger.info(f" 投稿完了 : {title if title else '(タイトルなし)'}")
                success = True
                break
            except Exception as e:
                # HttpErrorの場合、ステータスコードを確認
                if isinstance(e, HttpError):
                    # 400番台（クライアントエラー）は429（Too Many Requests）以外リトライしない
                    if 400 <= e.resp.status < 500 and e.resp.status != 429:
                        logger.error(
                            f"APIクライアントエラー (ステータス: {e.resp.status}): {e} - 再試行を中止します"
                        )
                        break

                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(
                        f"APIエラー (試行 {attempt+1}/{max_retries}): {e} - {wait_time}秒後に再試行します"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"アップロード失敗 (タイトル: {title}): {e}", exc_info=True
                    )
            finally:
                last_execution_time = time.time()
        return success
    except Exception as e:
        logger.error(f"記事処理中に予期せぬエラーが発生しました: {e}", exc_info=True)
        return False

def is_resume():
    # upload_dir (投稿用一時フォルダ) にファイルがあれば、再起動（再開）と判定する
    if Path(upload_dir).exists():
        has_html = any(
            p.is_file() and p.suffix.lower() in html_extensions
            for p in Path(upload_dir).rglob("*")
        )
        if has_html:
            logger.info("再起動からの処理を開始します。(ファイルコピーをスキップ)")
            return True
    logger.debug("新規処理を開始します。ファイルを準備します。")
    return False    

def run(result_queue):
    """input_dir フォルダからアップロードを実行"""
    if service is None:
        logger.info("サービス開始")
        if not ready_upload():
            logger.error("アップロード準備に失敗しました。処理を中断します。")
            return False
    
    # 新規処理の場合は、input_dir から upload_dir へファイルをコピーして準備する
    if not is_resume():
        logger.debug("新規処理を開始します。ファイルを準備します。")
        if not move_upload_file(result_queue):
            return False

    # 処理対象のファイルを upload_dir から取得し、名前順でソート
    files_to_process = sorted(
        [
            p
            for p in Path(upload_dir).rglob("*")
            if p.is_file() and p.suffix.lower() in html_extensions
        ]
    )
    if not files_to_process:
        logger.info("アップロード対象のHTMLファイルが見つかりません。")
        return True

    # まず全ファイルを「待機中（砂時計）」としてGUIに通知
    for src_path in files_to_process:
        file = SmartFile(src_path)
        file.status = "⏳"
        file.extensions = "html"
        file.disp_path = file.name
        result_queue.put(file)

    pbar = ProgressBar(len(files_to_process), prefix="Art HTML")
    processed_count = 0
    wait_posts_list = []
    for src_path in files_to_process:

        if processed_count >= max_posts_per_run:
            file = SmartFile(src_path)
            file.status = "⏸️"
            file.extensions = "html"
            file.disp_path = file.name
            result_queue.put(file)
            pbar.update()            
            wait_posts_list.append(file)
            logger.info(f"実行上限に達しました: {file.name}")
            continue  # 以降のファイルはスキップして処理を続行する場合は continue を使用

        file = SmartFile(src_path)
        file.status = "▶"  # 処理中ステータスをGUIに通知
        file.extensions = "html"
        file.disp_path = file.name
        result_queue.put(file)

        try:
            art_html = src_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"ファイル読み込み失敗: {src_path.name} - {e}")
            file.status = "✘"
            result_queue.put(file)
            continue

        if upload_art(art_html):
            if move_history_file(src_path):
                file.status = "✔"
                processed_count += 1
            else:
                file.status = "⚠️"
                logger.error(
                    f"履歴保存失敗のため、元ファイルを残します: {src_path.name}"
                )
            result_queue.put(file)
        else:
            file.status = "✘"
            result_queue.put(file)
            logger.error(f"記事のアップロードに失敗しました: {src_path.name}")
            # 失敗しても次のファイルの処理を継続する場合はここでのreturnは不要
        pbar.update()
    if wait_posts_list:
        logger.info(f"{len(wait_posts_list)} 件の記事が上限に達したため、翌日以降の実行で処理されます。")
        return wait_posts_list
    # 全て成功
    return True


if __name__ == "__main__":

    result_queue = queue.Queue()
    move_upload_file(result_queue)
    try:
        run(result_queue)
    except KeyboardInterrupt:
        logger.info("処理が中断されました。")
    except Exception as e:
        logger.critical(f"予期せぬエラーが発生しました: {e}", exc_info=True)

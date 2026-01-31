# -*- coding: utf-8 -*-
import logging
from logging.handlers import RotatingFileHandler
import traceback
import argparse
from datetime import datetime
from pathlib import Path
import shutil
import platform
import subprocess

# 設定とパイプラインモジュールをインポート
from config import get_config
import cleaner
import add_date
import file_scanner
import image_processor
import keyword_adder
import location_adder
import image_uploader
import article_uploader
import archiver
import database
import retry_errors

# --- ロギング設定 ---
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('main.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger("Orchestrator")
logger.setLevel(logging.INFO) # デフォルトはINFOレベル
logger.addHandler(log_handler)
logger.addHandler(logging.StreamHandler())

# --- パイプラインの各ステップを定義 ---
# 構造: (表示名, 実行する関数, config.iniのセクション名)
# config.iniにセクションやENABLEDキーがなくても、デフォルトで実行されます。
PIPELINE_STEPS = [
    ("0. データ準備 (クリーニング)", cleaner.run_cleaning, "CLEANER"),
    ("0.5. 日付追加", add_date.run_add_date_pipeline, "ADD_DATE"),
    ("1. ファイルスキャン", file_scanner.scan_and_register_files, "FILE_SCANNER"),
    ("2. 画像処理 (ウォーターマーク)", image_processor.run_image_processing_pipeline, "IMAGE_PROCESSOR"),
    ("3. キーワード追加", keyword_adder.run_keyword_addition_pipeline, "ADD_KEYWORDS"),
    ("3.5. 位置情報追加", location_adder.run_location_addition_pipeline, "ADD_GEORSS_POINT"),
    ("4. 画像アップロード", image_uploader.run_image_upload_pipeline, "IMAGE_UPLOADER"),
    ("5. 記事アップロード", article_uploader.run_article_upload_pipeline, "UPLOADER"),
    ("6. アーカイブ", archiver.run_archiver_pipeline, "ARCHIVER"),
]

# 処理中断用フラグ
STOP_REQUESTED = False

def validate_prerequisites(dry_run=False):
    """実行前の前提条件チェック"""
    logger.info("--- 環境チェック ---")
    errors = []
    warnings = []
    
    # 1. 認証ファイル (credentials.json)
    # アップロード工程が有効か確認
    uploaders_enabled = False
    for name, _, section in PIPELINE_STEPS:
        if section in ['UPLOADER', 'IMAGE_UPLOADER']:
             if get_config(section, 'enabled', 'true').lower() == 'true':
                uploaders_enabled = True
                break
    
    if uploaders_enabled:
        creds_path = Path(__file__).parent / 'credentials.json'
        if not creds_path.exists():
            errors.append(f"認証ファイルが見つかりません: {creds_path.name} (アップロード工程に必要です)")
        
        blog_id = get_config('UPLOADER', 'blog_id')
        if not blog_id:
            errors.append("Blog IDが設定されていません (config.ini [UPLOADER] blog_id)")
        else:
            logger.info(f"使用するBlog ID: {blog_id}")

    # 2. 入力ディレクトリの確認 (cleanerが有効な場合)
    if get_config('CLEANER', 'enabled', 'true').lower() == 'true':
        reports_dir = Path(__file__).parent / get_config('DEFAULT', 'reports_dir', './reports')
        if not reports_dir.exists():
            warnings.append(f"入力ディレクトリが見つかりません: {reports_dir} (クリーニング対象なし)")

    # 3. API接続テスト (アップロード有効時かつエラーがない場合)
    if uploaders_enabled and not errors:
        logger.info("API接続テストを実行中...")
        try:
            from google_auth import get_blogger_service
            service = get_blogger_service()
            # ブログ情報の取得を試みることで接続確認
            service.blogs().get(blogId=blog_id).execute()
            logger.info("API接続テスト OK")
        except Exception as e:
            msg = f"API接続テスト失敗: {e} (認証情報またはBlog IDを確認してください)"
            if dry_run:
                logger.warning(f"警告: {msg}")
                logger.warning("Dry-Runモードのため、APIエラーを無視して続行します。")
            else:
                errors.append(msg)

    # 4. ディスク容量チェック (最低500MB)
    try:
        total, used, free = shutil.disk_usage(".")
        min_free_bytes = 500 * 1024 * 1024 # 500MB
        if free < min_free_bytes:
            errors.append(f"ディスク空き容量が不足しています: 残り {free / (1024*1024):.1f}MB (推奨: 500MB以上)")
    except Exception as e:
        warnings.append(f"ディスク容量の確認に失敗しました: {e}")

    # 5. 入力データの健全性チェック (Pre-flight Check)
    # ロボティクスにおけるセンサーチェックと同様、入力データが読み取り可能か事前に全数検査します。
    if get_config('CLEANER', 'enabled', 'true').lower() == 'true':
        reports_dir = Path(__file__).parent / get_config('DEFAULT', 'reports_dir', './reports')
        if reports_dir.exists():
            logger.info("入力データの健全性チェック(Pre-flight Check)を実行中...")
            files = list(reports_dir.rglob('*.html')) + list(reports_dir.rglob('*.htm'))
            # 対応するエンコーディング
            encodings = ['utf-8', 'cp932', 'shift_jis', 'euc-jp']
            failed_files = []
            
            for f in files:
                is_ok = False
                for enc in encodings:
                    try:
                        with open(f, 'r', encoding=enc) as fp:
                            fp.read() # 全読み込みしてエラーが出ないか確認
                        is_ok = True
                        break
                    except:
                        continue
                if not is_ok:
                    failed_files.append(f.name)
            
            if failed_files:
                msg = f"読み込み不可能なファイルが {len(failed_files)} 件検出されました (文字コード不明): {', '.join(failed_files[:3])}..."
                # Dry-Runや診断モードなら警告にとどめるが、本番ならエラー扱いも検討
                if dry_run:
                    logger.warning(f"警告: {msg}")
                else:
                    # 堅牢性のため、読めないファイルがある場合は警告リストに入れる（処理自体はスキップされるので続行可能だが、ユーザーに知らせる）
                    warnings.append(msg)
            else:
                logger.info(f"入力データチェック OK: {len(files)} ファイル")

    for w in warnings:
        logger.warning(f"警告: {w}")

    if errors:
        logger.error("=== 環境チェックエラー ===")
        for err in errors:
            logger.error(f"- {err}")
        return False
    
    logger.info("環境チェック OK")
    return True

def generate_report(results, has_critical_error):
    """Markdownレポート生成"""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        report_dir = Path(__file__).parent / 'logs'
        report_dir.mkdir(exist_ok=True)
        report_file = report_dir / f"report_{timestamp}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# HTML to Blogger パイプライン実行レポート\n\n")
            f.write(f"**実行日時**: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}\n\n")
            
            if has_critical_error:
                f.write("## ⚠️ 状態: 致命的なエラー発生\n\n")
            else:
                f.write("## ✅ 状態: 完了\n\n")
            
            f.write("## ステップ別結果\n\n")
            f.write("| ステップ | 成功 | 失敗 | スキップ |\n")
            f.write("| :--- | :---: | :---: | :---: |\n")
            
            for name, result in results:
                step_name = name.split('. ', 1)[1] if '. ' in name else name
                success, errors, *skips = result
                skipped = skips[0] if skips else 0
                
                if skipped == 'MANUAL_UPLOAD_REQUIRED':
                    f.write(f"| {step_name} | {success} | {errors} | 待機中 |\n")
                else:
                    f.write(f"| {step_name} | {success} | {errors} | {skipped} |\n")
            
            f.write("\n## エラー詳細 (DB抜粋)\n\n")
            
            # DBからエラー取得
            error_articles = database.get_articles_by_status('error')
            if error_articles:
                f.write("### 記事エラー\n\n")
                for art in error_articles:
                    f.write(f"- **{Path(art['source_path']).name}**\n")
                    f.write(f"  - {art['error_message']}\n")
            
            error_images = database.get_images_by_status('error')
            if error_images:
                f.write("### 画像エラー\n\n")
                for img in error_images:
                    f.write(f"- **{Path(img['source_path']).name}**\n")
                    f.write(f"  - {img['error_message']}\n")
            
            if not error_articles and not error_images:
                f.write("エラーはありませんでした。\n")

        logger.info(f"実行レポートを作成しました: {report_file}")
    except Exception as e:
        logger.error(f"レポート生成に失敗しました: {e}")

def send_notification(title, message):
    """OSネイティブの通知を送信する"""
    system = platform.system()
    try:
        if system == 'Darwin': # macOS
            subprocess.run(['osascript', '-e', f'display notification "{message}" with title "{title}"'], check=False)
        elif system == 'Linux':
            # notify-sendがある場合のみ実行
            if shutil.which('notify-send'):
                subprocess.run(['notify-send', title, message], check=False, stderr=subprocess.DEVNULL)
    except Exception as e:
        logger.debug(f"通知送信エラー: {e}")

def run_maintenance():
    """メンテナンスモード: DB最適化とログのアーカイブ"""
    logger.info("=== メンテナンスモード開始 ===")
    
    # 1. DB最適化
    logger.info("データベースのバックアップと最適化を実行中...")
    database.backup_db()
    database.optimize_db()
    
    # 2. ログのアーカイブ
    logger.info("古いログファイルのアーカイブを実行中...")
    log_dir = Path(__file__).parent
    archive_dir = log_dir / 'logs' / 'archive' / datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # .log.1, .log.2 などのローテーションされた古いログを移動
    moved_count = 0
    for log_file in log_dir.glob('*.log.*'):
        if log_file.is_file():
            if not archive_dir.exists():
                archive_dir.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(log_file), str(archive_dir / log_file.name))
                moved_count += 1
            except Exception as e:
                logger.warning(f"ログアーカイブ失敗 ({log_file.name}): {e}")
    
    logger.info(f"メンテナンス完了: {moved_count}個のログをアーカイブしました。")

def print_summary(results, critical_error_occured):
    """
    処理完了後に、結果のサマリーをコンソールに表示する。
    """
    logger.info("\n========================================")
    if critical_error_occured:
        logger.warning("=== 統合処理パイプライン完了 (致命的なエラーあり) ===")
    else:
        logger.info("=== 統合処理パイプライン完了 ===")
    logger.info("========================================")

    # 1. 各ステップの結果を表示
    total_success = 0
    total_errors = 0
    logger.info("\n--- 各ステップの処理結果 ---")
    for name, result in results:
        # "1. ファイルスキャン" -> "ファイルスキャン"
        step_name = name.split('. ', 1)[1] if '. ' in name else name
        success, errors, *skips = result # skips will be a list (empty or with one element)
        skipped = skips[0] if skips else 0
        
        if skipped == "Dry-Run":
            logger.info(f"  - {step_name:<25}: [Dry-Run] 実行予定")
            continue

        if skipped == 'MANUAL_UPLOAD_REQUIRED':
            logger.info(f"  - {step_name:<25}: 手動アップロード待ち (一時停止)")
            continue

        total_success += success
        total_errors += errors
        if isinstance(skipped, int) and skipped > 0:
            logger.info(f"  - {step_name:<25}: 成功 {success}件, 失敗 {errors}件, スキップ {skipped}件")
        else:
            logger.info(f"  - {step_name:<25}: 成功 {success}件, 失敗 {errors}件")

        # クリーニングエラー時の案内
        if "クリーニング" in step_name and errors > 0:
            logger.warning(f"    ※ クリーニング失敗ファイルは 'cleaning_errors' フォルダに退避されました。")

    # 2. データベースからエラー内容の要約を表示
    error_articles = database.get_articles_by_status('error')
    error_images = database.get_images_by_status('error')
    db_total_errors = len(error_articles) + len(error_images)

    if db_total_errors > 0:
        logger.warning("\n--- エラー内容の要約 ---")
        error_summary = {}
        all_errors = error_articles + error_images
        for error_item in all_errors:
            msg = error_item.get('error_message')
            if not msg:
                msg = '不明なエラー'
            simple_msg = msg.split(':')[0].strip()
            error_summary[simple_msg] = error_summary.get(simple_msg, 0) + 1

        for msg, count in sorted(error_summary.items()):
            logger.warning(f"  - {msg}: {count}件")

        logger.warning("\n詳細は各ログファイル、または `python retry_errors.py` を実行して確認してください。")

    # 通知送信
    title = "HTML to Blogger パイプライン"
    if critical_error_occured:
        msg = "処理が完了しましたが、エラーが発生しています。"
    else:
        msg = "すべての処理が正常に完了しました。"
    send_notification(title, msg)

def main(dry_run=False, auto_retry=False):
    """
    パイプライン全体を制御するメイン関数。
    """
    global STOP_REQUESTED
    STOP_REQUESTED = False

    # デバッグログ設定の反映
    if get_config('DEFAULT', 'debug_log', 'false').lower() == 'true':
        logger.setLevel(logging.DEBUG)
        logger.info("Debug log enabled.")

    logger.info("========================================")
    logger.info("=== 統合処理パイプライン開始 ===")
    logger.info("========================================")

    pipeline_results = []
    has_critical_error = False

    # 自動リトライ処理
    # 引数で指定されているか、設定ファイル(DEFAULTセクションのauto_retry)で有効になっている場合に実行
    config_auto_retry = get_config('DEFAULT', 'auto_retry', 'false').lower() == 'true'
    if auto_retry or config_auto_retry:
        logger.info("--- 自動リトライ処理を実行します ---")
        try:
            retry_errors.run_retry_process()
        except Exception as e:
            logger.error(f"リトライ処理中にエラーが発生しました: {e}")

    if dry_run:
        logger.info("!!! DRY-RUN MODE: 実際の処理はスキップされます !!!")

    # 環境チェック (Dry-Run時はスキップしても良いが、設定確認のため実行する)
    if not validate_prerequisites(dry_run=dry_run):
        logger.error("環境チェックに失敗したため、処理を中断します。")
        return 1, False # エラーあり、手動アップロード要求なし

    for name, function, config_section in PIPELINE_STEPS:
        # 中断チェック
        if STOP_REQUESTED:
            logger.warning("\n!!! ユーザーによって処理が中断されました !!!")
            break

        # config.iniから有効/無効をチェック
        # get_configの第3引数でデフォルト値を'true'に設定
        is_enabled_str = get_config(config_section, 'enabled', 'true')
        is_enabled = is_enabled_str.lower() == 'true'
        logger.debug(f"DEBUG: Checking step '{name}'. Section='{config_section}', Key='enabled', Value='{is_enabled_str}', Enabled={is_enabled}")

        if is_enabled:
            if dry_run:
                logger.info(f"\n--- [DRY-RUN] {name} を実行する予定です ---")
                pipeline_results.append((name, (0, 0, "Dry-Run")))
                continue

            logger.info(f"\n--- {name} を実行します ---")
            try:
                result = function()
                if result and isinstance(result, tuple) and len(result) in [2, 3]:
                    pipeline_results.append((name, result))
                    
                    # 手動アップロード待ちなど、中断要求がある場合はループを抜ける
                    if len(result) == 3 and result[2] == 'MANUAL_UPLOAD_REQUIRED':
                        logger.warning(f"--- {name}: 手動操作が必要なため、パイプラインを一時停止します ---")
                        break
                # 各モジュールのログで完了メッセージが出る
            except Exception as e:
                logger.error(f"--- {name}: パイプラインの実行中に致命的なエラーが発生しました ---")
                # tracebackを使用して、エラーの詳細なスタックトレースをログに出力
                logger.error(f"エラー概要: {e}")
                logger.error(traceback.format_exc())
                has_critical_error = True
                # エラーが発生しても次のステップに進む
        else:
            logger.warning(f"\n--- {name}: スキップされました (DB設定で無効、またはセクション/キー未定義) ---")

    print_summary(pipeline_results, has_critical_error)
    generate_report(pipeline_results, has_critical_error)

    # GUIに結果を返すためのエラーカウント
    total_errors = 0
    manual_upload_required = False
    for name, result in pipeline_results:
        # result は (success, error, skip) のタプル
        if len(result) >= 2 and isinstance(result[1], int):
            total_errors += result[1]
        if len(result) >= 3 and result[2] == 'MANUAL_UPLOAD_REQUIRED':
            manual_upload_required = True
    
    if has_critical_error:
        total_errors += 1
        
    return total_errors, manual_upload_required

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='HTML to Blogger Pipeline Orchestrator')
    parser.add_argument('--dry-run', action='store_true', help='処理を実行せず、パイプラインの流れを確認します')
    parser.add_argument('--retry', action='store_true', help='エラーとなった記事・画像をリセットして再試行対象にします')
    parser.add_argument('--maintenance', action='store_true', help='メンテナンスモード（DB最適化・ログ整理）を実行します')
    args = parser.parse_args()

    try:
        if args.maintenance:
            # メンテナンスモード実行
            database.init_db() # DB接続確保のため
            run_maintenance()
        else:
            # 通常パイプライン実行
            # データベースのバックアップを作成
            database.backup_db()
            
            # データベースの初期化を最初に実行
            database.init_db()
            
            main(dry_run=args.dry_run, auto_retry=args.retry)
    except KeyboardInterrupt:
        logger.warning("\nユーザーによって処理が中断されました。")
    except Exception as e:
        logger.critical(f"予期せぬエラーが発生しました: {e}", exc_info=True)
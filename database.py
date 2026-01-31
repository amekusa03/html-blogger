# -*- coding: utf-8 -*-
import sqlite3
import os
import shutil
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path
import configparser

# ロギング設定
logger = logging.getLogger(__name__)
if not logger.handlers:
    # basicConfigは他のロガー設定と競合するため避ける
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    log_handler = RotatingFileHandler('database.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
    log_handler.setFormatter(log_formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(log_handler)
    logger.addHandler(logging.StreamHandler())

# データベースファイルのパス設定
SCRIPT_DIR = Path(__file__).parent.resolve()
DB_FILE = SCRIPT_DIR / 'articles.db'

def get_connection():
    """データベース接続を取得する（Rowファクトリ付き）"""
    # timeoutを設定して、GUIとバックグラウンド処理の競合によるロックエラーを防ぐ(デフォルトは5秒)
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.row_factory = sqlite3.Row  # カラム名でアクセス可能にする
    return conn

def backup_db():
    """データベースファイルのバックアップを作成する"""
    if not DB_FILE.exists():
        return

    # バックアップ用ディレクトリ
    backup_dir = SCRIPT_DIR / 'backups'
    backup_dir.mkdir(exist_ok=True)

    # タイムスタンプ付きファイル名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f"articles_{timestamp}.db"

    try:
        shutil.copy2(DB_FILE, backup_path)
        logger.info(f"データベースのバックアップを作成しました: {backup_path.name}")
        
        # ローテーション: 古いバックアップを削除 (最新5件を残す)
        backups = sorted(backup_dir.glob('articles_*.db'), key=lambda p: p.stat().st_mtime, reverse=True)
        for old_backup in backups[5:]:
            try:
                old_backup.unlink()
                logger.info(f"古いバックアップを削除しました: {old_backup.name}")
            except Exception as e:
                logger.warning(f"バックアップ削除失敗: {e}")

    except Exception as e:
        logger.error(f"データベースバックアップ失敗: {e}")

def optimize_db():
    """データベースの最適化（VACUUM, ANALYZE）を行う"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        logger.info("データベースの最適化(VACUUM)を開始します...")
        cursor.execute("VACUUM")
        cursor.execute("ANALYZE")
        conn.commit()
        logger.info("データベースの最適化が完了しました。")
    except Exception as e:
        logger.error(f"データベース最適化エラー: {e}")
    finally:
        conn.close()

def init_db():
    """
    データベースとテーブルの初期化を行う。
    アプリケーション起動時に一度呼び出すことを推奨。
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # articles テーブル作成
        # status: 処理の進行状況（new, keywords_added, uploaded, error など）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT NOT NULL UNIQUE,
                title TEXT,
                content TEXT,
                labels TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                blogger_post_id TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # content_hash カラムが存在しない場合は追加 (マイグレーション)
        try:
            cursor.execute("SELECT content_hash FROM articles LIMIT 1")
        except sqlite3.OperationalError:
            logger.info("articlesテーブルに content_hash カラムを追加します。")
            cursor.execute("ALTER TABLE articles ADD COLUMN content_hash TEXT")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_content_hash ON articles (content_hash)")
        
        # images テーブル作成
        # article_id: どの記事に属するか
        # source_path: 元の画像ファイルのパス
        # status: 処理の進行状況 (new, watermarked, uploaded, error など)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                source_path TEXT NOT NULL,
                processed_path TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                blogger_url TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles (id) ON DELETE CASCADE
            )
        ''')
        # 複合ユニークインデックス: 同じ記事に同じ画像パスが重複登録されるのを防ぐ
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_images_article_id_source_path ON images (article_id, source_path)')
        # 外部キーで検索することが多いため、インデックスを貼っておく
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_article_id ON images (article_id)')

        # configurations テーブル作成 (config.ini の代替)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configurations (
                section TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (section, key)
            )
        ''')

        # config.ini の内容でデータベースの設定を更新（同期）
        # これにより、config.ini を編集して再起動すれば設定が反映されるようになります
        _migrate_config_ini(conn)

        conn.commit()
        logger.info(f"データベース初期化完了: {DB_FILE}")
    except Exception as e:
        logger.error(f"データベース初期化エラー: {e}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()

def _migrate_config_ini(conn):
    """config.ini の内容を configurations テーブルに移行する"""
    config_path = SCRIPT_DIR / 'config.ini'
    if not config_path.exists():
        return

    logger.info("config.ini から設定をデータベースに移行します...")
    config = configparser.ConfigParser()
    config.read(config_path, encoding='utf-8')
    cursor = conn.cursor()

    defaults = config.defaults()

    # DEFAULTセクションの処理
    for key, value in defaults.items():
        _insert_config(cursor, 'DEFAULT', key, value)

    # 各セクションの処理
    for section in config.sections():
        for key, value in config.items(section): # itemsはDEFAULTも含むが、上書き保存で対応
            # デフォルト値と同じ場合は、DB容量節約とフォールバック動作のためにスキップする
            # if key in defaults and defaults[key] == value:
            #     continue
            _insert_config(cursor, section, key, value)

def _insert_config(cursor, section, key, value):
    """設定値をクリーニングしてDBに挿入"""
    if '#' in value: value = value.split('#', 1)[0].strip()
    if ';' in value: value = value.split(';', 1)[0].strip()
    value = value.strip().strip("'").strip('"')
    cursor.execute('INSERT OR REPLACE INTO configurations (section, key, value) VALUES (?, ?, ?)',
                   (section, key, value))

def register_file(source_path, content_hash=None):
    """
    新規ファイルをDBに登録する。
    既に登録済みのファイル（source_pathが重複）は無視する。
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # source_pathの重複チェックはSQLのUNIQUE制約とINSERT OR IGNOREに任せる
        cursor.execute('''
            INSERT OR IGNORE INTO articles (source_path, content_hash, status, created_at, updated_at)
            VALUES (?, ?, 'new', ?, ?)
        ''', (str(source_path), content_hash, datetime.now(), datetime.now()))
        
        if cursor.rowcount > 0:
            logger.info(f"新規ファイル登録: {source_path}")
            conn.commit()
            return cursor.lastrowid
        else:
            # 既に存在する場合はNoneを返す
            return None
    except Exception as e:
        logger.error(f"ファイル登録エラー {source_path}: {e}")
        return None
    finally:
        if conn:
            conn.close()

def check_hash_exists(content_hash):
    """指定されたハッシュ値を持つ記事が既に存在するか確認する"""
    if not content_hash:
        return None
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id, source_path, status FROM articles WHERE content_hash = ?', (content_hash,))
        return cursor.fetchone()
    finally:
        conn.close()

def revive_article(article_id, source_path):
    """missingまたはerror状態の記事を復活させる（パス更新、ステータスnew）"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE articles 
            SET source_path = ?, status = 'new', error_message = NULL, updated_at = ?
            WHERE id = ?
        ''', (str(source_path), datetime.now(), article_id))
        conn.commit()
    finally:
        conn.close()

def register_image(article_id, image_source_path):
    """
    記事に関連する画像をDBに登録する。
    既に登録済みの場合は無視する。
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        path_str = str(image_source_path)
        
        # まず存在確認
        cursor.execute('SELECT id, status FROM images WHERE article_id = ? AND source_path = ?', (article_id, path_str))
        row = cursor.fetchone()
        
        if row:
            # 存在する場合、ステータスが missing や error なら復活させる
            if row['status'] in ('missing', 'error'):
                cursor.execute("UPDATE images SET status = 'new', error_message = NULL, updated_at = ? WHERE id = ?", (datetime.now(), row['id']))
                conn.commit()
                logger.info(f"  -> 画像復活: {Path(image_source_path).name} (ID: {row['id']})")
                return row['id']
            return None
        else:
            # 新規登録
            cursor.execute('''
                INSERT INTO images (article_id, source_path, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (article_id, path_str, datetime.now(), datetime.now()))
            conn.commit()
            logger.info(f"  -> 新規画像登録: {Path(image_source_path).name} (記事ID: {article_id})")
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"画像登録エラー (記事ID:{article_id}, パス:{image_source_path}): {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_articles_by_status(status):
    """指定されたステータスの記事リストを取得する"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM articles WHERE status = ?', (status,))
        rows = cursor.fetchall()
        # dict形式に変換して返す
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_statistics():
    """記事と画像のステータス別件数を取得する"""
    conn = get_connection()
    stats = {'articles': {}, 'images': {}}
    try:
        cursor = conn.cursor()
        
        # Articles
        cursor.execute("SELECT status, COUNT(*) as count FROM articles GROUP BY status")
        for row in cursor.fetchall():
            stats['articles'][row['status']] = row['count']
        
        # Images
        cursor.execute("SELECT status, COUNT(*) as count FROM images GROUP BY status")
        for row in cursor.fetchall():
            stats['images'][row['status']] = row['count']
            
        return stats
    except Exception as e:
        logger.error(f"統計取得エラー: {e}")
        return stats
    finally:
        conn.close()

def get_images_by_status(status):
    """指定されたステータスの画像リストを取得する"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM images WHERE status = ?', (status,))
        rows = cursor.fetchall()
        # dict形式に変換して返す
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_processing_records(table_name):
    """処理中（完了・アーカイブ・欠損以外）のレコードを取得する"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # SQLインジェクション対策: table_nameは内部利用のみ想定だが、念のためホワイトリストチェック
        if table_name not in ['articles', 'images']:
            return []
        
        cursor.execute(f"SELECT * FROM {table_name} WHERE status NOT IN ('uploaded', 'archived', 'missing')")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_images_by_article_id(article_id):
    """指定された記事IDに関連する画像リストを取得する"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM images WHERE article_id = ?', (article_id,))
        rows = cursor.fetchall()
        # dict形式に変換して返す
        return [dict(row) for row in rows]
    finally:
        conn.close()

def reset_article_error(article_id, new_status):
    """記事のエラーステータスをリセットし、指定された新しいステータスに更新する"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE articles 
            SET status = ?, error_message = NULL, updated_at = ?
            WHERE id = ?
        ''', (new_status, datetime.now(), article_id))
        conn.commit()
        logger.info(f"記事エラーリセット: ID={article_id} -> status='{new_status}'")
    except Exception as e:
        logger.error(f"記事エラーリセット失敗 ID={article_id}: {e}")
        raise
    finally:
        conn.close()

def reset_image_error(image_id, new_status):
    """画像のエラーステータスをリセットし、指定された新しいステータスに更新する"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE images 
            SET status = ?, error_message = NULL, updated_at = ?
            WHERE id = ?
        ''', (new_status, datetime.now(), image_id))
        conn.commit()
        logger.info(f"画像エラーリセット: ID={image_id} -> status='{new_status}'")
    except Exception as e:
        logger.error(f"画像エラーリセット失敗 ID={image_id}: {e}")
        raise
    finally:
        conn.close()

def update_image_info(image_id, status=None, processed_path=None, blogger_url=None, error_message=None):
    """
    画像の情報を更新する汎用関数。
    引数で指定された項目のみを更新する。
    """
    updates = []
    params = []

    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if processed_path is not None:
        updates.append("processed_path = ?")
        params.append(str(processed_path))
    if blogger_url is not None:
        updates.append("blogger_url = ?")
        params.append(blogger_url)
    
    # error_messageはNoneを許容して上書き
    updates.append("error_message = ?")
    params.append(error_message)

    if not updates:
        return  # 更新対象がない

    updates.append("updated_at = ?")
    params.append(datetime.now())
    params.append(image_id)

    query = f"UPDATE images SET {', '.join(updates)} WHERE id = ?"

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        conn.commit()
    except Exception as e:
        logger.error(f"画像情報更新エラー ID={image_id}: {e}")
        raise
    finally:
        conn.close()

def update_content(article_id, content, title=None, labels=None):
    """記事の内容（HTMLコンテンツ、タイトル、ラベル）を更新する"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = 'UPDATE articles SET content = ?, updated_at = ?'
        params = [content, datetime.now()]
        
        if title is not None:
            query += ', title = ?'
            params.append(title)
        
        if labels is not None:
            # リストの場合はカンマ区切り文字列に変換
            if isinstance(labels, list):
                labels = ','.join(labels)
            query += ', labels = ?'
            params.append(labels)
            
        query += ' WHERE id = ?'
        params.append(article_id)
        
        cursor.execute(query, tuple(params))
        conn.commit()
    except Exception as e:
        logger.error(f"記事更新エラー ID={article_id}: {e}")
        raise
    finally:
        conn.close()

def update_status(article_id, new_status, error_message=None):
    """
    ステータスを更新する。
    エラー発生時は error_message に詳細を記録可能。
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if error_message:
            cursor.execute('''
                UPDATE articles 
                SET status = ?, error_message = ?, updated_at = ?
                WHERE id = ?
            ''', (new_status, error_message, datetime.now(), article_id))
        else:
            cursor.execute('''
                UPDATE articles 
                SET status = ?, updated_at = ?
                WHERE id = ?
            ''', (new_status, datetime.now(), article_id))
        conn.commit()
    except Exception as e:
        logger.error(f"ステータス更新エラー ID={article_id}: {e}")
        raise
    finally:
        conn.close()

def set_uploaded(article_id, blogger_post_id):
    """アップロード完了状態（status='uploaded'）にし、BloggerのPostIDを記録する"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE articles 
            SET status = 'uploaded', blogger_post_id = ?, updated_at = ?
            WHERE id = ?
        ''', (blogger_post_id, datetime.now(), article_id))
        conn.commit()
    except Exception as e:
        logger.error(f"アップロード完了記録エラー ID={article_id}: {e}")
        raise
    finally:
        conn.close()

def get_config_value(section, key, retry=True):
    """
    DBから設定値を取得する。
    指定セクションになければ DEFAULT セクションを探す。
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 1. 指定セクションから検索
        cursor.execute('SELECT value FROM configurations WHERE section = ? AND key = ?', (section, key.lower()))
        row = cursor.fetchone()
        if row:
            return row['value']
        
        # 2. DEFAULTセクションから検索
        cursor.execute('SELECT value FROM configurations WHERE section = ? AND key = ?', ('DEFAULT', key.lower()))
        row = cursor.fetchone()
        if row:
            return row['value']
            
        return None
    except sqlite3.OperationalError:
        # テーブルがない場合は初期化して再試行
        if conn:
            conn.close()
        if retry:
            init_db()
            return get_config_value(section, key, retry=False)
        else:
            raise
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass

def set_config_value(section, key, value):
    """DBに設定値を保存する"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO configurations (section, key, value, updated_at) VALUES (?, ?, ?, ?)',
                       (section, key.lower(), str(value), datetime.now()))
        conn.commit()
    finally:
        conn.close()

if __name__ == '__main__':
    # 単体テスト用: 直接実行された場合はDB初期化を行う
    init_db()
    print("database.py: DB initialized.")
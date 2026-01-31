# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path
import database
import io

def get_image_status_report():
    """画像のステータスレポートを作成して文字列で返す"""
    output = io.StringIO()
    
    def _print(text=""):
        output.write(str(text) + "\n")

    _print(f"--- 画像処理ステータス確認 ---")
    
    try:
        conn = database.get_connection()
        cursor = conn.cursor()

        # 1. ステータスごとの集計
        _print("\n【ステータス別件数】")
        cursor.execute("SELECT status, COUNT(*) as count FROM images GROUP BY status")
        rows = cursor.fetchall()
        
        status_map = {
            'new': '未処理 (透かし待ち)',
            'watermarked': '透かし完了 (アップロード待ち)',
            'uploaded': 'アップロード完了 (記事投稿待ち)',
            'archived': 'アーカイブ済み (全工程完了)',
            'error': 'エラー発生',
            'missing': 'ファイル消失'
        }

        if not rows:
            _print("  (画像データなし)")
        
        for row in rows:
            status = row['status']
            desc = status_map.get(status, 'その他')
            _print(f"  - {status:<12} : {row['count']:>3} 件  ({desc})")

        # 2. 処理待ち・エラーの詳細表示
        _print("\n【未完了の画像一覧 (new, watermarked, error)】")
        cursor.execute("""
            SELECT i.id, i.status, i.source_path, i.error_message, a.source_path as article_path
            FROM images i
            LEFT JOIN articles a ON i.article_id = a.id
            WHERE i.status NOT IN ('uploaded', 'archived')
            ORDER BY i.id
        """)
        rows = cursor.fetchall()

        if not rows:
            _print("  (未完了の画像はありません。すべて完了しています)")
        else:
            for row in rows:
                img_name = Path(row['source_path']).name
                art_name = Path(row['article_path']).name if row['article_path'] else "不明な記事"
                
                _print(f"  [ID:{row['id']:<3}] {row['status']:<12}: {img_name}")
                _print(f"         └ 所属記事: {art_name}")
                if row['error_message']:
                    _print(f"         └ ⚠️ エラー: {row['error_message']}")

    except Exception as e:
        _print(f"エラーが発生しました: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
    
    _print("\n--------------------------------------------------")
    _print("解説:")
    _print(" - new        : 次回「画像処理」で透かしが入ります。")
    _print(" - watermarked: 次回「画像アップロード」でBloggerへ送られます。")
    _print(" - error      : 自動では再試行されません。retry_errors.py でリセット可能です。")
    
    return output.getvalue()

if __name__ == '__main__':
    print(get_image_status_report())

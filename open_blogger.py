# -*- coding: utf-8 -*-
import os
import re
import tkinter as tk
from tkinter import simpledialog, messagebox
import webbrowser
from pathlib import Path
from config import get_config
import configparser

# URLからBLOG_IDを抽出する関数
def extract_blog_id_from_url(url):
    """
    URLからBLOG_IDを抽出
    例：https://www.blogger.com/blog/posts/7306624495354184863 -> 7306624495354184863
    """
    match = re.search(r'/posts/(\d+)', url)
    if match:
        return match.group(1)
    return None

# config.iniに設定を書き込む関数
def save_blog_id_to_config(blog_id):
    """
    抽出したBLOG_IDをconfig.iniに保存
    """
    config_file = Path(__file__).parent / 'config.ini'
    config = configparser.ConfigParser()
    config.read(config_file, encoding='utf-8')
    
    if 'OPEN_BLOGGER' not in config:
        config['OPEN_BLOGGER'] = {}
    
    config['OPEN_BLOGGER']['BLOG_ID'] = blog_id
    
    with open(config_file, 'w', encoding='utf-8') as f:
        config.write(f)
    
    print(f"BLOG_IDをconfig.iniに保存しました: {blog_id}")

def main():
    """
    メイン処理
    1. ブラウザでBloggerサイトとメディアマネージャーを開く
    2. URLを入力するダイアログボックスを表示
    3. URLからBLOG_IDを抽出してconfig.iniに保存
    """
    # ブラウザを開く
    blogger_signin_url = get_config('OPEN_BLOGGER', 'BLOGGER_SIGNIN_URL')
    media_manager_url = get_config('OPEN_BLOGGER', 'MEDIA_MANAGER_URL')
    
    print("Bloggerサイトとメディアマネージャーを開いています...")
    webbrowser.open(blogger_signin_url, new=1)
    webbrowser.open(media_manager_url, new=1)
    
    # Tkinterのルートウィンドウを作成（非表示）
    root = tk.Tk()
    root.withdraw()
    
    # URL入力ダイアログを表示
    url = simpledialog.askstring(
        "ブログURL入力",
        "ブログのURLを入力してください。\n例：https://www.blogger.com/blog/posts/7306624495354184863",
        parent=root
    )
    
    root.destroy()
    
    if url is None:
        # キャンセルボタンが押された場合
        print("キャンセルされました。")
        return
    
    # URLからBLOG_IDを抽出
    blog_id = extract_blog_id_from_url(url)
    
    if blog_id:
        # BLOG_IDをconfig.iniに保存
        save_blog_id_to_config(blog_id)
        messagebox.showinfo("成功", f"BLOG_IDを抽出して保存しました:\n{blog_id}")
        print(f"抽出したBLOG_ID: {blog_id}")
    else:
        messagebox.showerror("エラー", "URLが正しくありません。\n/posts/ の後に数字が必要です。")
        print("エラー: URLからBLOG_IDを抽出できませんでした。")

if __name__ == '__main__':
    main()
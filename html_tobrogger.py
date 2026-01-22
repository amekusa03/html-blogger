# !/usr/bin/env python
# -*- coding: utf8 -*-
import sys
import tkinter as Tkinter
from tkinter import messagebox
import subprocess
import datetime
import platform
from pathlib import Path

# --- 設定ファイル編集用関数 ---
def open_config_file():
    """config.iniを標準アプリで開く"""
    config_file = Path(__file__).parent / 'config.ini'
    if not config_file.exists():
        messagebox.showerror("エラー", f"{config_file} が見つかりません")
        return
    
    try:
        system = platform.system()
        if system == 'Darwin':  # macOS
            subprocess.Popen(['open', str(config_file)])
        elif system == 'Windows':
            subprocess.Popen(['start', str(config_file)], shell=True)
        else:  # Linux
            subprocess.Popen(['xdg-open', str(config_file)])
        print(f"config.iniを開きました: {config_file}")
    except Exception as e:
        messagebox.showerror("エラー", f"ファイルを開く際にエラーが発生しました: {e}")

def open_keywords_file():
    """keywords.xmlを標準アプリで開く"""
    keywords_file = Path(__file__).parent / 'keywords.xml'
    if not keywords_file.exists():
        messagebox.showerror("エラー", f"{keywords_file} が見つかりません")
        return
    
    try:
        system = platform.system()
        if system == 'Darwin':  # macOS
            subprocess.Popen(['open', str(keywords_file)])
        elif system == 'Windows':
            subprocess.Popen(['start', str(keywords_file)], shell=True)
        else:  # Linux
            subprocess.Popen(['xdg-open', str(keywords_file)])
        print(f"keywords.xmlを開きました: {keywords_file}")
    except Exception as e:
        messagebox.showerror("エラー", f"ファイルを開く際にエラーが発生しました: {e}")

def open_georss_file():
    """georss_point.xmlを標準アプリで開く"""
    georss_file = Path(__file__).parent / 'georss_point.xml'
    if not georss_file.exists():
        messagebox.showerror("エラー", f"{georss_file} が見つかりません")
        return
    
    try:
        system = platform.system()
        if system == 'Darwin':  # macOS
            subprocess.Popen(['open', str(georss_file)])
        elif system == 'Windows':
            subprocess.Popen(['start', str(georss_file)], shell=True)
        else:  # Linux
            subprocess.Popen(['xdg-open', str(georss_file)])
        print(f"georss_point.xmlを開きました: {georss_file}")
    except Exception as e:
        messagebox.showerror("エラー", f"ファイルを開く際にエラーが発生しました: {e}")

pythonproccess = [['キーワード作成', 'add_keywords.py'],
                ['位置情報追加', 'add_georss_point.py'],
                ['htmlクリーニング', 'cleaner.py'],
                ['ブログURL取得', 'open_blogger.py'],
                ['画像リンク設定', 'image_preparer.py'],
                ['Atomフィード生成', 'convert_atom.py']]

root = Tkinter.Tk()
root.title(u"htmlからBloggerアップロード")
root.geometry("640x480")

process = None
progress = 0

# --- メニューバー作成 ---
menubar = Tkinter.Menu(root)
root.config(menu=menubar)

# ファイルメニュー
file_menu = Tkinter.Menu(menubar, tearoff=0)
menubar.add_cascade(label="ファイル", menu=file_menu)

# 設定ファイル編集サブメニュー
config_edit_menu = Tkinter.Menu(file_menu, tearoff=0)
file_menu.add_cascade(label="設定ファイル編集", menu=config_edit_menu)
config_edit_menu.add_command(label="config.ini", command=open_config_file)
config_edit_menu.add_command(label="keywords.xml", command=open_keywords_file)
config_edit_menu.add_command(label="georss_point.xml", command=open_georss_file)

# ボタンが押されるとここが呼び出される
def StartEntryValue(event):
    btn_text = event.widget.cget("text")
    print(f"ボタン押下: {btn_text}")
    for item in pythonproccess:
        if item[0] == btn_text:
            script_name = item[1]
            break
    # ここで処理を開始する
    global process
    process = subprocess.Popen([sys.executable, script_name], stdout=subprocess.PIPE, text=True)
    root.after(10, update_timer)

def update_timer():
    # プロセスの終了確認
    global process
    if process is None:
        return True
    return_code = process.poll()

    # 標準出力を読み取る（非ブロッキング）
    try:
        output = process.stdout.read()
        if output:
            text_widget.insert(Tkinter.END, output.strip() + "\n")
            text_widget.see(Tkinter.END)
    except Exception:
        pass

    # 終了判定
    if return_code is not None:
        return False
    
    # 10ミリ秒後に再度この関数を呼び出す
    root.after(10, update_timer)
    return True

# ボタン
header_frame = Tkinter.Frame(root)
header_frame.pack(side="top", anchor="nw", padx=5, pady=5)
for item in pythonproccess:
    Button = Tkinter.Button(header_frame, text=item[0])
    Button.bind("<Button-1>", StartEntryValue)
    Button.pack(side="left", padx=5, pady=2)   

# ログ表示用テキストウィジェット
text_widget = Tkinter.Text(root, height=15, width=100)
text_widget.pack(pady=10)   

# 最初のタイマー処理を登録
update_timer()

root.mainloop()

if process is not None:
    rc = process.wait()
    sys.exit(rc)  

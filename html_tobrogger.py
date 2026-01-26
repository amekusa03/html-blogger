# !/usr/bin/env python
# -*- coding: utf8 -*-
import sys
import tkinter as Tkinter
from tkinter import messagebox, simpledialog
import subprocess
import datetime
import platform
import shutil
import webbrowser
from pathlib import Path
from config import get_config

# --- URL定数 ---
BLOGGER_SIGNIN_URL = 'https://www.blogger.com/go/signin'  # ブロガーサインインURL
MEDIA_MANAGER_URL = 'http://blogger.com/mediamanager'  # メディアマネージャーURL

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

def open_reports_folder():
    """reportsフォルダを開く（操作１）"""
    script_dir = Path(__file__).parent.resolve()
    reports_dir = script_dir / get_config('ADD_KEYWORDS', 'ORIGINAL_DIR')
    
    # フォルダが存在しない場合は作成
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # 仕様D：ファイルがあれば警告
    # 注：config.ini で ADD_KEYWORDS_DIR = './work' に統合されている
    work_dir = script_dir / './work'  # 直接 work フォルダを指定
    ready_upload_images_dir = script_dir / './ready_upload'
    ready_upload_dir = script_dir / './ready_upload'
    
    # デバッグ：確認するフォルダを表示
    print(f"チェック対象フォルダ:")
    print(f"  reports_dir: {reports_dir}")
    print(f"  work_dir: {work_dir}")
    print(f"  ready_upload_dir: {ready_upload_dir}")
    
    folders_to_check = [reports_dir, work_dir, ready_upload_dir]
    
    # バックアップファイルを除外して実ファイルがあるかチェック（再帰的）
    def has_real_files(folder):
        if not folder.exists():
            print(f"  {folder} は存在しません")
            return False
        
        print(f"  {folder} をチェック中...")
        try:
            for item in folder.rglob('*'):
                # finishedフォルダ配下は除外
                if 'finished' in item.parts:
                    continue
                # .xmlファイルは除外
                if item.is_file() and item.suffix.lower() == '.xml':
                    continue
                # .backup_を含むファイルは除外
                if item.is_file() and '.backup_' in item.name:
                    continue
                # 実ファイルが見つかった
                if item.is_file():
                    print(f"    -> 実ファイル検出: {item.relative_to(folder)}")
                    return True
        except Exception as e:
            print(f"    エラー: {e}")
            pass
        
        return False
    
    has_files = any(has_real_files(folder) for folder in folders_to_check)
    
    if has_files:
        response = messagebox.askyesno(
            "作業中のファイル確認",
            "作業中のファイルがあります。削除してもよろしいですか？\n\n※ *.xml ファイルと finished/ フォルダは削除されません"
        )
        if response:
            # フォルダをクリア（*.xmlと finished/は除外）
            for folder in folders_to_check:
                if folder.exists():
                    for item in folder.iterdir():
                        if item.is_file() and not item.suffix.lower() == '.xml':
                            item.unlink()
                        elif item.is_dir() and item.name != 'finished':
                            shutil.rmtree(str(item), ignore_errors=True)
            print("作業フォルダをクリアしました")
        else:
            print("キャンセルしました")
            return
    
    # reportsフォルダを開く
    try:
        system = platform.system()
        if system == 'Darwin':  # macOS
            subprocess.Popen(['open', str(reports_dir)])
        elif system == 'Windows':
            subprocess.Popen(['explorer', str(reports_dir)])
        else:  # Linux
            subprocess.Popen(['xdg-open', str(reports_dir)])
        print(f"reportsフォルダを開きました: {reports_dir}")
    except Exception as e:
        messagebox.showerror("エラー", f"フォルダを開く際にエラーが発生しました: {e}")

def open_media_manager_folder():
    """media_manager フォルダを開く（操作４）"""
    script_dir = Path(__file__).parent.resolve()
    media_dir = script_dir / 'media-man'
    media_dir.mkdir(parents=True, exist_ok=True)
    
    # ブラウザでメディアマネージャーURLを開く
    try:
        webbrowser.open(MEDIA_MANAGER_URL)
        print(f"メディアマネージャーをブラウザで開きました: {MEDIA_MANAGER_URL}")
    except Exception as e:
        messagebox.showerror("エラー", f"ブラウザを開く際にエラーが発生しました: {e}")
    
    # フォルダも開く
    try:
        system = platform.system()
        if system == 'Darwin':  # macOS
            subprocess.Popen(['open', str(media_dir)])
        elif system == 'Windows':
            subprocess.Popen(['explorer', str(media_dir)])
        else:  # Linux
            subprocess.Popen(['xdg-open', str(media_dir)])
        print(f"media_manager フォルダを開きました: {media_dir}")
    except Exception as e:
        messagebox.showerror("エラー", f"フォルダを開く際にエラーが発生しました: {e}")

def open_image_folder():
    """ready_upload フォルダを開く（操作４）"""
    script_dir = Path(__file__).parent.resolve()
    image_dir = script_dir / './ready_upload'
    image_dir.mkdir(parents=True, exist_ok=True)
    
    # ブラウザでブロガーサインインURLを開く
    try:
        webbrowser.open(BLOGGER_SIGNIN_URL)
        print(f"ブロガーサインインをブラウザで開きました: {BLOGGER_SIGNIN_URL}")
    except Exception as e:
        messagebox.showerror("エラー", f"ブラウザを開く際にエラーが発生しました: {e}")
    
    # フォルダも開く
    try:
        system = platform.system()
        if system == 'Darwin':  # macOS
            subprocess.Popen(['open', str(image_dir)])
        elif system == 'Windows':
            subprocess.Popen(['explorer', str(image_dir)])
        else:  # Linux
            subprocess.Popen(['xdg-open', str(image_dir)])
        print(f"ready_upload フォルダを開きました: {image_dir}")
    except Exception as e:
        messagebox.showerror("エラー", f"フォルダを開く際にエラーが発生しました: {e}")

def check_initialization():
    """初期化チェック（仕様D）"""
    script_dir = Path(__file__).parent.resolve()
    token_file = script_dir / 'token.pickle'
    
    if not token_file.exists():
        messagebox.showwarning(
            "警告",
            "token.pickle が見つかりません。\n\n"
            "アップロード時に認証が必要になります。\n"
            "open_blogger.py を実行して認証を完了してください。"
        )

# --- メイン処理 ---
# 操作３で実行される処理
pythonproccess = [['クリーニング', 'cleaner.py'],
                ['キーワード作成', 'add_keywords.py'],
                ['日付追加', 'add_date.py'],
                ['位置情報追加', 'add_georss_point.py'],
                ['画像位置情報削除＆ウォーターマーク追加', 'phot_exif_watemark.py'],
                ['アップロードフォルダ削除', 'delete_ready_upload.py'],
                ['画像リネーム', 'image_preparer.py']]

# 操作５で実行される処理
pythonproccess_step5 = [['HTMLリネーム', 'html_preparer.py'],
                        ['リンク設定', 'link_html.py'],
                        ['Atomフィード生成', 'convert_atom.py']]

# 操作６で実行される処理（単独）
pythonproccess_upload = [['アップロード', 'uploader.py']]
# ボタン定義
button_list = ['フォルダを開く'], ['開始'], ['メディアマネージャーを開く'], ['画像フォルダを開く'], ['リンク設定&Atomフィード生成'], ['アップロード']  

# --- メインウィンドウ作成 ---
root = Tkinter.Tk()
root.title(u"htmlからBloggerアップロード")
root.geometry("800x600")

process = None
current_process_index = 0
current_process_list = []

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
def StartEntryValue(btn_text):
    print(f"ボタン押下: {btn_text}")
    
    # 操作１：フォルダを開く
    if "フォルダを" in btn_text and "開く" in btn_text:
        open_reports_folder()
        return
    
    # 操作３：開始（キーワード作成～画像処理）
    elif btn_text == "開始":
        start_step3()
        return
    
    # 操作４：メディアマネージャーを開く
    elif "メディアマネージャー" in btn_text:
        open_media_manager_folder()
        return
    
    # 操作４：画像フォルダを開く
    elif "画像フォルダ" in btn_text:
        open_image_folder()
        return
    
    # 操作５：リンク設定 & Atomフィード生成
    elif "リンク設定" in btn_text:
        start_step5()
        return
    
    # 操作６：アップロード
    elif "アップロード" in btn_text:
        start_upload()
        return

def start_step3():
    """操作３：キーワード作成～画像処理を実行"""
    text_widget.delete('1.0', Tkinter.END)
    text_widget.insert(Tkinter.END, f"=== 操作３：処理開始 ({len(pythonproccess)}個) ===\n")
    
    # 順次実行
    global current_process_index, current_process_list
    current_process_list = pythonproccess
    current_process_index = 0
    run_next_process()

def start_step5():
    """操作５：リンク設定 & Atomフィード生成を実行"""
    
    # ブラウザでブロガーサインインURLを開く
    try:
        webbrowser.open(BLOGGER_SIGNIN_URL)
        print(f"ブロガーサインインをブラウザで開きました: {BLOGGER_SIGNIN_URL}")
    except Exception as e:
        messagebox.showerror("エラー", f"ブラウザを開く際にエラーが発生しました: {e}")
        
    # まず Blogger URL を入力してもらう
    url = simpledialog.askstring(
        "操作４：Blogger URL入力",
        "Blogger の URL を入力してください\n"
        "（例: https://www.blogger.com/blog/posts/1234567890）"
    )
    
    if not url:
        messagebox.showinfo("キャンセル", "キャンセルしました")
        return
    
    # open_blogger.py の処理と同様に BLOG_ID を抽出
    import re
    match = re.search(r'/posts/(\d+)', url)
    if not match:
        messagebox.showerror("エラー", "URL形式が正しくありません")
        return
    
    blog_id = match.group(1)
    print(f"抽出したBLOG_ID: {blog_id}")
    
    # 続けて操作５の処理を実行
    text_widget.delete('1.0', Tkinter.END)
    text_widget.insert(Tkinter.END, f"=== 操作５：リンク設定 & Atomフィード生成 ===\n")
    
    global current_process_index, current_process_list
    current_process_list = pythonproccess_step5
    current_process_index = 0
    run_next_process()

def start_upload():
    """操作６：アップロード開始"""
    response = messagebox.askyesno(
        "確認",
        "アップロードを開始します。よろしいですか？"
    )
    
    if not response:
        return
    
    text_widget.delete('1.0', Tkinter.END)
    text_widget.insert(Tkinter.END, f"=== 操作６：アップロード開始 ===\n")
    
    global current_process_index, current_process_list
    current_process_list = pythonproccess_upload
    current_process_index = 0
    run_next_process()

def run_next_process():
    """次の処理を実行"""
    global current_process_index, current_process_list, process
    
    if current_process_index >= len(current_process_list):
        text_widget.insert(Tkinter.END, "\n=== 全処理完了 ===\n")
        messagebox.showinfo("完了", "すべての処理が完了しました")
        return
    
    item = current_process_list[current_process_index]
    script_name = item[1]
    
    text_widget.insert(Tkinter.END, f"\n[{current_process_index + 1}/{len(current_process_list)}] {item[0]} 実行中...\n")
    text_widget.see(Tkinter.END)
    
    process = subprocess.Popen([sys.executable, script_name], stdout=subprocess.PIPE, text=True)
    root.after(10, update_timer)

def update_timer():
    """プロセス監視"""
    global process, current_process_index, current_process_list
    
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
        if return_code == 0:
            text_widget.insert(Tkinter.END, "✓ 完了\n")
        else:
            text_widget.insert(Tkinter.END, f"✗ エラー (コード: {return_code})\n")
        
        # 次の処理へ
        current_process_index += 1
        if current_process_index < len(current_process_list):
            root.after(500, run_next_process)
        else:
            text_widget.insert(Tkinter.END, "\n=== 全処理完了 ===\n")
        
        return False
    
    # 10ミリ秒後に再度この関数を呼び出す
    root.after(10, update_timer)
    return True

# ボタン（2行×3列のグリッドレイアウト）
header_frame = Tkinter.Frame(root)
header_frame.pack(side="top", anchor="nw", padx=10, pady=10)

button_labels = [
    ("フォルダを\n開く", 0, 0),
    ("開始", 0, 1),
    ("画像フォルダ\nを開く", 0, 2),
    ("メディアマネージャー\nを開く", 1, 0),
    ("リンク設定&\nAtomフィード生成", 1, 1),
    ("アップロード", 1, 2)
]

for label, row, col in button_labels:
    btn = Tkinter.Button(header_frame, text=label, width=18, height=3, wraplength=120,
                         command=lambda lbl=label: StartEntryValue(lbl))
    btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

# グリッドの列を均等に配置
for i in range(3):
    header_frame.columnconfigure(i, weight=1)   

# ログ表示用テキストウィジェット
text_widget = Tkinter.Text(root, height=20, width=100)
text_widget.pack(pady=10)   

# クレジット表示（仕様E）
credit_frame = Tkinter.Frame(root)
credit_frame.pack(side="bottom", pady=5)

credit_label1 = Tkinter.Label(credit_frame, text="Using: BeautifulSoup4, geopy, Janome, Google API Client")
credit_label1.pack()

credit_label2 = Tkinter.Label(credit_frame, text="© OpenStreetMap contributors", fg="blue", cursor="hand2")
credit_label2.pack()

# OpenStreetMapリンクをクリックで開く
def open_osm_link(event):
    import webbrowser
    webbrowser.open("https://www.openstreetmap.org/copyright/ja")

credit_label2.bind("<Button-1>", open_osm_link)

# 初期化チェック（仕様D）
check_initialization()

root.mainloop()

if process is not None:
    rc = process.wait()
    sys.exit(rc)  

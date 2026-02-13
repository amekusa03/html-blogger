import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import logging
import threading
import time
import sys
import os
import re
import subprocess
import platform
import webbrowser
from pathlib import Path
import queue

import main_process
from parameter import config, save_config, open_config_file, open_keywords_app, open_georss_file
from file_class import SmartFile


# ロガーの設定
logger = logging.getLogger(__name__)

class TkLogHandler(logging.Handler):
    """ログをTkinterのScrolledTextに出力するハンドラ"""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        tag = "INFO"
        if record.levelno >= logging.ERROR:
            tag = "ERROR"
        elif record.levelno >= logging.WARNING:
            tag = "WARN"
        elif record.levelno == logging.INFO:
            tag = "INFO"
        
        def append():
            try:
                self.text_widget.configure(state='normal')
                self.text_widget.insert(tk.END, msg + '\n', tag)
                self.text_widget.see(tk.END)
                self.text_widget.configure(state='disabled')
            except Exception:
                pass
        
        # Tkinterのメインスレッドで実行するためにafterを使用
        self.text_widget.after(0, append)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bloggers of that time...")
        self.geometry("1100x800")
        
        # テーマ設定
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        
        # ファイルステータス管理用
        self.html_status = {}
        self.image_status = {}

        # GUI構築
        self.create_menu()
        self.create_widgets()
        
        # ログ設定
        self.setup_logging()
        
        # 初回リスト更新
        #self.refresh_file_lists()
        
        # キューの初期化
        self.command_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        # 処理スレッドの開始
        self.thread = threading.Thread(target=self.start_thread)
        self.thread.daemon = True
        self.thread.start()        
        self.after(100, self.poll_queue)
        
        # 初期設定
        self.process_def = {}
        self.process = None
        self.initial_process(self.command_queue, self.result_queue)

    def _update_listbox(self, listbox, item_status, item_collection, smart_file):
        """リストボックスと対応する辞書を更新するヘルパー関数"""
        old_name = getattr(smart_file, 'old_name', None)
        if old_name:
            item_collection.pop(old_name, None)
        item_collection[smart_file.disp_path] = item_status

        target_name = str(old_name if old_name else smart_file.disp_path)
        updated = False
        for i in range(listbox.size()):
            if target_name in listbox.get(i):
                listbox.delete(i)
                listbox.insert(i, f"{item_status} {smart_file.disp_path}")
                listbox.see(i)
                updated = True
                break
        if not updated:
            listbox.insert(tk.END, f"{item_status} {smart_file.disp_path}")
            listbox.see(tk.END)

    def start_thread(self):
        """バックグラウンドプロセスを開始"""
        main_process.main_process(self.command_queue, self.result_queue)

    def poll_queue(self):
        """キューを監視してGUIを更新"""
        try:
            while True:
                msg_type = None
                fname = None
                result = self.result_queue.get_nowait()
                if isinstance(result, SmartFile):
                    fname = result
                    status = result.status
                    if fname.extensions == 'html':
                        self._update_listbox(self.html_listbox, status, self.html_status, fname)
                    elif fname.extensions == 'image':
                        self._update_listbox(self.image_listbox, status, self.image_status, fname)
                    else:
                        logger.warning(f"不明なファイルタイプ: {fname}") 
                    logger.info(f"ファイルステータス更新: {fname} -> {status}")
                    continue
                elif isinstance(result, tuple):
                    msg_type = result[0].lower()
                elif isinstance(result, str):
                    msg_type = result.lower()

                if msg_type == 'import_files':
                    self.refresh_process_steps('import_files', '✔')
                    open_path = config['gui']['reports_dir']
                    self.open_folder_action(open_path)
                    messagebox.showinfo("ファイル取り込み", f"開いたフォルダ\n{open_path}にHTMLの記事、画像を入れて下さい。")
                    logger.info("ファイル取り込みが完了しました。")
                if msg_type == 'check_files':
                    self.refresh_process_steps('check_files', '✔')
                    logger.info("ファイルチェックが完了しました。")
                if msg_type == 'serialize_files':
                    self.refresh_process_steps('serialize_files', '✔')
                    logger.info("シリアライズ処理が完了しました。")        
                if msg_type == 'clean_html':
                    self.refresh_process_steps('clean_html', '✔')
                if msg_type == 'find_keyword':
                    self.refresh_process_steps('find_keyword', '✔')                    
                if msg_type == 'find_location':
                    self.refresh_process_steps('find_location', '✔')
                if msg_type == 'find_date':
                    self.refresh_process_steps('find_date', '✔')
                if msg_type == 'mod_image':
                    self.refresh_process_steps('mod_image', '✔') 
                if msg_type == 'upload_image':
                    self.refresh_process_steps('upload_image', '✔') 
                    open_path = config['gui']['upload_dir']
                    self.open_folder_action(open_path)
                    open_web = config['gui']['blogger_url']
                    webbrowser.open(open_web)
                    messagebox.showinfo("画像アップロード", f"開いたフォルダ\n{open_path}をブロガーに下書き投稿してください。\n(タイトル不要、本文は空でOKです）")
                if msg_type == 'history_image':
                    self.refresh_process_steps('history_image', '✔')
                if msg_type == 'import_media_manager':
                    open_web = config['gui']['media_manager_url'] + str(config['upload_art']['blog_id'])
                    webbrowser.open(open_web)
                    open_path = config['link_html']['media_manager_dir']
                    self.open_folder_action(open_path)
                    messagebox.showinfo("メディアマネージャー", f"開いたフォルダ\n{open_path}をブロガーのメディアマネージャーにアップロードしてください。")
                    self.refresh_process_steps('import_media_manager', '✔') 
                if msg_type == 'link_html':
                    self.refresh_process_steps('link_html', '✔')                  
                
                if msg_type == 'upload_art':
                    self.refresh_process_steps('upload_art', '✔') 
                    open_web = config['gui']['blogger_url']
                    webbrowser.open(open_web)
                    messagebox.showinfo("記事アップロード", f"Bloggerの管理画面が開きます。\n投稿済みの記事を確認してください。")
                if msg_type == 'closing':
                    self.refresh_process_steps('closing', '✔') 
                    messagebox.showinfo("処理完了", f"すべての処理が完了しました。\nお疲れ様でした！")
                    logger.info("すべての処理が完了しました。")
                    self.reset_gui()
                      
                # プロセス完了通知であればボタンを再度有効化
                if self.process_def and msg_type in self.process_def:
                    self.btn_check.configure(state='normal')

                if msg_type == 'process_list':
                    # ステップリストの更新と仮定
                    self.step_labels = {}
                    count = 0
                    self.process_def = result[1]
                    completed_count = 0
                    for process in self.process_def.values():
                        lbl = ttk.Label(self.steps_group, text=f"{process['status']} {process['name']}")
                        lbl.grid(row=count, column=0, sticky="w", padx=5, pady=2)
                        self.step_labels[process['name']] = lbl
                        count += 1
                        if process['status'] == '✔':
                            completed_count += 1
                    
                    # プログレスバー初期化
                    total_steps = len(self.process_def)
                    if total_steps > 0:
                        progress = (completed_count / total_steps) * 100
                        self.progress_var.set(progress)
                        self.status_label.config(text=f"{int(progress)}% 完了")
                    logger.info("プロセスステップを更新しました。")
        except queue.Empty:
            pass
        finally:
            self.after(100, self.poll_queue)

    def reset_gui(self):
        """GUIを初期状態にリセットする"""
        self.process = None
        self.html_status = {}
        self.image_status = {}
        self.html_listbox.delete(0, tk.END)
        self.image_listbox.delete(0, tk.END)
        self.progress_var.set(0)
        self.status_label.config(text="待機中...")
        logger.info("-" * 30)
        
        # ステータスをリセット
        if self.process_def:
            for key in self.process_def:
                self.process_def[key]['status'] = '⌛'
        
        self.command_queue.put('process_list')

    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
#        file_menu.add_command(label="ブログIDを設定...", command=self.set_blog_id)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.quit)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="設定編集", menu=edit_menu)
        edit_menu.add_command(label="config.json5", command=open_config_file)
        edit_menu.add_command(label="keywords.xml", command=open_keywords_app)
        edit_menu.add_command(label="locate.xml", command=open_georss_file)
        
        tool_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ツール", menu=tool_menu)
        #tool_menu.add_command(label="レポート一覧HTML作成", command=self.create_reports_index)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="使い方 (Help)", command=self.open_help)
        help_menu.add_separator()
        help_menu.add_command(label="バージョン情報", command=self.show_about)

    def show_under_construction(self):
        messagebox.showinfo("作成中", "この機能は現在開発中です。")

    def create_widgets(self):
        # メインフレーム
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 3カラム構成
        main_frame.columnconfigure(0, weight=1, uniform="group1") # 左
        main_frame.columnconfigure(1, weight=1, uniform="group1") # 中
        main_frame.columnconfigure(2, weight=1, uniform="group1") # 右
        main_frame.rowconfigure(0, weight=1)

        # --- 左カラム: フォルダ、進行状況、ステップ ---
        left_col = ttk.Frame(main_frame)
        left_col.grid(row=0, column=0, sticky="nsew", padx=5)
        
        # フォルダ操作エリア
        folder_group = ttk.LabelFrame(left_col, text="フォルダ", padding=5)
        folder_group.pack(fill=tk.X, pady=(0, 10))
        
        folders_data = [
            ("📄 原稿", config['gui']['reports_dir']),
            ("⚙️ 作業中", config['gui']['work_dir']),
            ("📝 投稿HTML", config['gui']['upload_dir']),
            ("📦 完了分", config['gui']['history_dir']),
            ("🗄️ バックアップ", config['gui']['backup_dir']),
        ]
        
        # グリッド配置用のフレーム
        folder_btn_frame = ttk.Frame(folder_group)
        folder_btn_frame.pack(fill=tk.X)
        for i, (label, path) in enumerate(folders_data):
            btn = ttk.Button(folder_btn_frame, text=label, command=lambda p=path: self.open_folder_action(p))
            btn.grid(row=i//2, column=i%2, sticky="ew", padx=2, pady=2)
        folder_btn_frame.columnconfigure(0, weight=1)
        folder_btn_frame.columnconfigure(1, weight=1)

        # 進行状況エリア
        status_group = ttk.LabelFrame(left_col, text="進行状況", padding=5)
        status_group.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_group, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        self.status_label = ttk.Label(status_group, text="待機中...")
        self.status_label.pack(anchor=tk.E)

        # ステップ一覧
        self.steps_group = ttk.LabelFrame(left_col, text="ステップ", padding=5)
        self.steps_group.pack(fill=tk.BOTH, expand=True)
        
        
        # self.step_labels = {}
        # for i, (name,  _, _) in enumerate(self.process_def):
        #     display_name = name.split('. ', 1)[1] if '. ' in name else name
        #     # アイコンの代わりに文字を使用
        #     lbl = ttk.Label(steps_group, text=f"⌛ {display_name}")
        #     lbl.grid(row=i, column=0, sticky="w", padx=5, pady=2)
        #     self.step_labels[name] = lbl

        # --- 中カラム: ファイル一覧 ---
        mid_col = ttk.Frame(main_frame)
        mid_col.grid(row=0, column=1, sticky="nsew", padx=5)
        
        # HTMLファイル一覧
        html_group = ttk.LabelFrame(mid_col, text="HTMLファイル一覧", padding=5)
        html_group.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.html_listbox = tk.Listbox(html_group)
        html_scroll = ttk.Scrollbar(html_group, orient=tk.VERTICAL, command=self.html_listbox.yview)
        self.html_listbox.configure(yscrollcommand=html_scroll.set)
        self.html_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        html_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 画像ファイル一覧
        image_group = ttk.LabelFrame(mid_col, text="画像ファイル一覧", padding=5)
        image_group.pack(fill=tk.BOTH, expand=True)
        
        self.image_listbox = tk.Listbox(image_group)
        image_scroll = ttk.Scrollbar(image_group, orient=tk.VERTICAL, command=self.image_listbox.yview)
        self.image_listbox.configure(yscrollcommand=image_scroll.set)
        self.image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        image_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # --- 右カラム: ログ、アクション ---
        right_col = ttk.Frame(main_frame)
        right_col.grid(row=0, column=2, sticky="nsew", padx=5)
        
        # ログ
        log_group = ttk.LabelFrame(right_col, text="ログ", padding=5)
        log_group.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_group, state='disabled', height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # ログの色設定
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("WARN", foreground="#ff9800") # Orange-ish
        self.log_text.tag_config("ERROR", foreground="#f44336") # Red

        # アクションボタン
        actions_frame = ttk.Frame(right_col)
        actions_frame.pack(fill=tk.X)
        
        self.btn_check = ttk.Button(actions_frame, text="実行", command=self.on_actions_row_click)
        self.btn_check.pack(fill=tk.X, ipady=10)

    def setup_logging(self):
        # 既存のハンドラをクリア
        root_logger = logging.getLogger()
        for h in root_logger.handlers[:]:
            root_logger.removeHandler(h)
            
        root_logger.setLevel(logging.INFO)
        handler = TkLogHandler(self.log_text)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        root_logger.addHandler(handler)
        
    def initial_process(self, command_queue, result_queue):
        command_queue.put('process_list')
        

    def open_folder_action(self, path_str):
        path = Path(path_str)
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"フォルダ作成エラー: {e}")
                return
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', str(path)])
            else:
                subprocess.Popen(['xdg-open', str(path)])
            logger.info(f"フォルダを開きました: {path}")
        except Exception as e:
            logger.error(f"フォルダを開けませんでした: {e}")

    def refresh_process_steps(self, name, status):
        """プロセスステップ表示を更新する"""
        if name in self.process_def:
            self.process_def[name]['status'] = status
        
        # 既存のラベルをクリア
        for lbl in self.step_labels.values():
            lbl.destroy()
        self.step_labels = {}
        count = 0
        completed_count = 0
        for process in self.process_def.values():
            lbl = ttk.Label(self.steps_group, text=f"{process['status']} {process['name']}")
            lbl.grid(row=count, column=0, sticky="w", padx=5, pady=2)
            self.step_labels[process['name']] = lbl
            count += 1
            if process['status'] == '✔':
                completed_count += 1
        
        # プログレスバー更新
        total_steps = len(self.process_def)
        if total_steps > 0:
            progress = (completed_count / total_steps) * 100
            self.progress_var.set(progress)
            self.status_label.config(text=f"{int(progress)}% 完了")
        logger.info("プロセスステップを更新しました。")



    #def start_html_process(self):
        # HTMLタスクを生成（呼び出し方は上と同じ！）
#        self.current_task = HtmlEditTask(self.progress_queue)
        #self.execute_common()

    def execute_common(self):
        # 共通の実行＆監視フロー
        if self.process:
            self.process = self.process_def[self.process]['nextprocess']
        else:
            self.process = list(self.process_def.keys())[0]

        self.command_queue.put(self.process)


    def on_actions_row_click(self):
        # 処理中はボタンを無効化
        self.btn_check.configure(state='disabled')
        # ファイルチェック処理のプレースホルダー
        self.execute_common()
        logger.info("ファイルリストを更新しました。")
        # ここに実際の処理を追加可能

    def update_blog_id(self, blog_id):
        """ロジックに専念するメソッド"""
        if not blog_id:
            raise ValueError("Blog IDが入力されていません。")

        config['upload_art']['blog_id'] = blog_id
        try:
            save_config()
            logger.info(f"Blog ID更新成功: {blog_id}")
            return True
        except (IOError, OSError) as e: # OSレベルのエラーを具体的に捕捉
            logger.error(f"Config保存失敗: {e}")
            raise RuntimeError(f"設定ファイルの保存に失敗しました: {e}")
        
    def on_save_button_click(self):
        blog_id = self.entry_blog_id.get().strip()
        
        try:
            # ロジックの呼び出し
            self.update_blog_id(blog_id)
            messagebox.showinfo("成功", f"Blog IDを設定しました: {blog_id}")
        except ValueError as ve:
            messagebox.showwarning("入力エラー", str(ve))
        except Exception as e:
            messagebox.showerror("システムエラー", str(e))

    def open_help(self):
        """ヘルプファイル(HTML)をブラウザで開く"""
        docs_dir = Path(__file__).parent / 'docs'
        help_file = docs_dir / 'help.html'
        
        # ヘルプファイルがない場合は簡易作成
        if not help_file.exists():
            self.create_default_help(help_file)
            
        webbrowser.open(help_file.as_uri())

    def create_default_help(self, path):
        """簡易ヘルプHTMLを生成する"""
        try:
            path.parent.mkdir(exist_ok=True)
            content = """
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="UTF-8">
                <title>HTML to Blogger Help</title>
                <style>
                    body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }
                    h1, h2 { color: #333; border-bottom: 1px solid #ddd; padding-bottom: 10px; }
                    .step { background: #f9f9f9; padding: 15px; margin-bottom: 20px; border-radius: 5px; }
                    img { max-width: 100%; border: 1px solid #ccc; margin: 10px 0; }
                    code { background: #eee; padding: 2px 5px; border-radius: 3px; }
                </style>
            </head>
            <body>
                <h1>HTML to Blogger 使い方</h1>
                <p>このツールは、ローカルのHTML記事と画像をBloggerに投稿するときの支援ツールです。</p>
                
                <h2>基本的な流れ</h2>
                <div class="step">
                    <h3>1. 準備</h3>
                    <p><code>reports</code> フォルダに投稿したいHTMLファイルと画像を配置します。</p>
                </div>
                <div class="step">
                    <h3>2. 実行</h3>
                    <p>アプリの「次へ」ボタンを押すと、クリーニング、画像透かし処理、キーワード追加などが順次実行されます。</p>
                </div>
            </body>
            </html>
            """
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content.strip())
        except Exception as e:
            logger.error(f"ヘルプ生成失敗: {e}")

    def show_about(self):
        messagebox.showinfo("バージョン情報", "HTML to Blogger\nVersion: 1.0.0\n\n© OpenStreetMap contributors")

# --- mainエントリポイント ---
if __name__ == "__main__":
    app = App()
    app.mainloop()

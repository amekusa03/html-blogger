# -*- coding: utf-8 -*-
"""html_tobrogger.py
HTML to Bloggerのメインアプリケーション。TkinterでGUIを構築して、main_process.pyの処理をバックグラウンドスレッドで実行する。
ファイルのステータス管理、プロセスの進行状況表示、ログ表示、エラーファイルの管理などを行う。
"""
import logging
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, scrolledtext, ttk

import main_process
from file_class import SmartFile
from parameter import (
    Path,
    config,
    open_config_file,
    open_file_with_default_app,
    open_georss_file,
    open_keywords_app,
)

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
                self.text_widget.configure(state="normal")
                self.text_widget.insert(tk.END, msg + "\n", tag)
                self.text_widget.see(tk.END)
                self.text_widget.configure(state="disabled")
            except tk.TclError:
                pass

        # Tkinterのメインスレッドで実行するためにafterを使用
        self.text_widget.after(0, append)


class App(tk.Tk):
    """HTML to Bloggerのメインアプリケーションクラス"""

    def __init__(self):
        super().__init__()
        self.title("Bloggers of that time...")
        self.geometry("1100x800")

        # テーマ設定
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")

        # ファイルステータス管理用
        self.html_status = {}
        self.image_status = {}
        self.step_labels = {}
        self.disp_process_list = {}
        self.error_file_list = set()

        # GUI構築
        self.create_menu()
        self.create_widgets()

        # ログ設定
        self.setup_logging()

        # 手順初期化
        self.process = ""

        # キューの初期化
        self.command_queue = queue.Queue()
        self.result_queue = queue.Queue()

        # 処理スレッドの開始
        self.thread = threading.Thread(target=self.start_thread)
        self.thread.daemon = True
        self.thread.start()
        self.after(100, self.poll_queue)

        # 初期設定
        self.after(200, self.initial_process)

    def _update_listbox(self, listbox, item_status, item_collection, smart_file):
        """リストボックスと対応する辞書を更新するヘルパー関数"""
        old_name = getattr(smart_file, "old_name", None)
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
                status_type = None
                fname = None
                # ファイルステータス更新
                result = self.result_queue.get_nowait()
                if isinstance(result, SmartFile):
                    fname = result
                    status = result.status
                    if fname.extensions == "html":
                        # HTMLファイルのステータス更新
                        self._update_listbox(
                            self.html_listbox, status, self.html_status, fname
                        )
                        if result.iserror():
                            self.error_file_list.add(fname)
                            logger.warning("エラーファイル: %s", fname)
                    elif fname.extensions == "image":
                        # 画像ファイルのステータス更新
                        self._update_listbox(
                            self.image_listbox, status, self.image_status, fname
                        )
                        if result.iserror():
                            self.error_file_list.add(fname)
                            logger.warning("エラーファイル: %s", fname)
                    else:
                        # 不明なファイルタイプのステータス更新
                        # 不明なファイルタイプのエラーファイルリストに追加
                        if fname not in self.error_file_list:
                            self.error_file_list.add(fname)
                        logger.warning("不明なファイルタイプ: %s", fname)
                    logger.info("ファイルステータス更新: %s -> %s", fname, status)
                    continue
                elif isinstance(result, type(main_process.process_def)):
                    # プロセスステータス更新
                    msg_type = result["key"]
                    status_type = result.get("status", "⌛")
                if msg_type == "check_resume":
                    if status_type == "♻":
                        logger.info("再開処理があります。")
                if msg_type == "import_files" and status_type == "✔":
                    open_path = config["gui"]["reports_dir"]
                    self.open_folder_action(open_path)
                    messagebox.showinfo(
                        "ファイル取り込み",
                        f"開いたフォルダ\n{open_path}にHTMLの記事、画像を入れて下さい。",
                    )
                if msg_type == "upload_image":
                    if status_type == "✔" or status_type == "🔁":
                        if status_type == "🔁":
                            logger.info("画像の再開処理があります。")
                            if messagebox.askyesno(
                                "再アップロード",
                                "アップロードしていない画像があります。\n再度アップロードしますか？",
                            ):
                                self.process = "upload_image"
                            else:
                                continue
                        open_path = config["gui"]["upload_dir"]
                        self.open_folder_action(open_path)
                        open_web = config["gui"]["blogger_url"]
                        webbrowser.open(open_web)
                        messagebox.showinfo(
                            "画像アップロード",
                            f"開いたフォルダ\n{open_path}をブロガーに下書き投稿してください。\n(タイトル不要、本文は空でOKです）",
                        )

                if msg_type == "import_media_manager" and status_type == "✔":
                    open_web = config["gui"]["media_manager_url"]
                    webbrowser.open(open_web)
                    open_path = config["link_html"]["media_manager_dir"]
                    self.open_folder_action(open_path)
                    messagebox.showinfo(
                        "メディアマネージャー",
                        f"開いたフォルダ\n{open_path}をブロガーのメディアマネージャーにアップロードしてください。",
                    )
                if msg_type == "link_html":
                    if status_type == "⚠":
                        # エラーファイルがあればリスト表示
                        if self.error_file_message():
                            if messagebox.askyesno(
                                "リンク切れ画像",
                                "リンク切れの画像があります。\n再度画像アップロードしますか？",
                            ):
                                self.execute_common(retry=True)
                        else:
                            messagebox.showwarning(
                                "リンク切れ画像",
                                "不定のリンク切れの画像があります。\n処理を続行します。",
                            )
                if msg_type == "upload_art":
                    if status_type == "🔁":
                        logger.info("記事の再開処理があります。")
                        if messagebox.askyesno(
                            "再アップロード",
                            "アップロードしていない記事があります。\n再度アップロードしますか？",
                        ):
                            self.process = "upload_art"
                            self.execute_common(resume=True)
                        else:
                            continue
                    if status_type == "✔":
                        open_web = config["gui"]["blogger_url"]
                        webbrowser.open(open_web)
                        messagebox.showinfo(
                            "記事アップロード",
                            "Bloggerの管理画面が開きます。\n投稿済みの記事を確認してください。",
                        )
                    if result["status"] == "⏸️":
                        open_web = config["gui"]["blogger_url"]
                        webbrowser.open(open_web)
                        messagebox.showwarning(
                            "投稿制限",
                            "1回の投稿上限に達しました。\n日本時間17時以降に再度投稿してください。"
                            + "（BloggerのAPI使用時に投稿できる記事は実測値で45件でした） ",
                        )
                if msg_type == "closing" and status_type == "✔":
                    messagebox.showinfo(
                        "処理完了", "すべての処理が完了しました。\nお疲れ様でした！"
                    )
                    logger.info("すべての処理が完了しました。")
                    self.execute_common()
                if (
                    msg_type == "import_files"
                    or msg_type == "check_files"
                    or msg_type == "serialize_files"
                    or msg_type == "clean_html"
                    or msg_type == "find_keyword"
                    or msg_type == "find_location"
                    or msg_type == "find_date"
                    or msg_type == "mod_image"
                    or msg_type == "upload_image"
                    or msg_type == "import_media_manager"
                    or msg_type == "link_html"
                    or msg_type == "upload_art"
                ):

                    # ステップリストの更新と仮定
                    self.disp_process_list[msg_type] = result

                    lbl = ttk.Label(
                        self.steps_group,
                        text=f"{result['status']} {result['name']}",
                    )
                    row = list(self.disp_process_list.keys()).index(msg_type)
                    lbl.grid(row=row, column=0, sticky="w", padx=5, pady=2)
                    self.step_labels[self.disp_process_list[msg_type]["name"]] = lbl

                    # プログレスバー初期化
                    total_steps = len(self.disp_process_list)
                    completed_count = 0
                    for _, status in self.disp_process_list.items():
                        if status["status"] == "✔":
                            completed_count += 1
                            logger.info("%s処理が完了しました。", status["name"])
                    if total_steps > 0:
                        progress = (completed_count / total_steps) * 100
                        self.progress_var.set(progress)
                        self.status_label.config(text=f"{int(progress)}% 完了")
                    logger.info("プロセスステップを更新しました。")

                # --- 自動遷移とボタン制御ロジック (process_defのautonextを参照) ---
                if status_type == "✔":
                    # 処理ステップ完了時に、警告/エラーファイルがあったかチェック
                    has_error_files = self.error_file_message()

                    # process_defから自動遷移するかどうかを取得 (resultはプロセス定義の辞書)
                    should_autonext = result.get("autonext", False)

                    if has_error_files:
                        # 警告/エラーファイルがあった場合、ユーザー確認のため停止
                        self.btn_check.configure(state="normal")
                    elif should_autonext:
                        # エラーがなく、自動遷移が有効な場合は次へ
                        self.execute_common()
                    else:
                        # 手動ステップの場合は停止
                        self.btn_check.configure(state="normal")

                elif status_type in ["⚠", "⏸️", "🔁", "✖"]:
                    # 警告、一時停止、再開、エラー時はユーザー判断のためボタンを有効化
                    self.btn_check.configure(state="normal")

        except queue.Empty:
            pass
        finally:
            self.after(100, self.poll_queue)

    def create_menu(self):
        """メニューバーの作成"""
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
        # tool_menu.add_command(label="レポート一覧HTML作成", command=self.create_reports_index)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="使い方 (Help)", command=self.open_help)
        help_menu.add_separator()
        help_menu.add_command(label="バージョン情報", command=self.show_about)

    def create_widgets(self):
        """ウィジェットの作成"""
        # メインフレーム
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 3カラム構成
        main_frame.columnconfigure(0, weight=1, uniform="group1")  # 左
        main_frame.columnconfigure(1, weight=1, uniform="group1")  # 中
        main_frame.columnconfigure(2, weight=1, uniform="group1")  # 右
        main_frame.rowconfigure(0, weight=1)

        # --- 左カラム: フォルダ、進行状況、ステップ ---
        left_col = ttk.Frame(main_frame)
        left_col.grid(row=0, column=0, sticky="nsew", padx=5)

        # フォルダ操作エリア
        folder_group = ttk.LabelFrame(left_col, text="フォルダ", padding=5)
        folder_group.pack(fill=tk.X, pady=(0, 10))

        folders_data = [
            ("📄 原稿", config["gui"]["reports_dir"]),
            ("⚙️ 作業中", config["gui"]["work_dir"]),
            ("📝 投稿HTML", config["gui"]["upload_dir"]),
            ("📦 完了分", config["gui"]["history_dir"]),
            ("🗄️ バックアップ", config["gui"]["backup_dir"]),
        ]

        # グリッド配置用のフレーム
        folder_btn_frame = ttk.Frame(folder_group)
        folder_btn_frame.pack(fill=tk.X)
        for i, (label, path) in enumerate(folders_data):
            btn = ttk.Button(
                folder_btn_frame,
                text=label,
                command=lambda p=path: self.open_folder_action(p),
            )
            btn.grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
        folder_btn_frame.columnconfigure(0, weight=1)
        folder_btn_frame.columnconfigure(1, weight=1)

        # 進行状況エリア
        status_group = ttk.LabelFrame(left_col, text="進行状況", padding=5)
        status_group.pack(fill=tk.X, pady=(0, 10))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            status_group, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        self.status_label = ttk.Label(status_group, text="待機中...")
        self.status_label.pack(anchor=tk.E)

        # ステップ一覧
        self.steps_group = ttk.LabelFrame(left_col, text="ステップ", padding=5)
        self.steps_group.pack(fill=tk.BOTH, expand=True)

        # --- 中カラム: ファイル一覧 ---
        mid_col = ttk.Frame(main_frame)
        mid_col.grid(row=0, column=1, sticky="nsew", padx=5)

        # HTMLファイル一覧
        html_group = ttk.LabelFrame(mid_col, text="HTMLファイル一覧", padding=5)
        html_group.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.html_listbox = tk.Listbox(html_group)
        html_scroll = ttk.Scrollbar(
            html_group, orient=tk.VERTICAL, command=self.html_listbox.yview
        )
        self.html_listbox.configure(yscrollcommand=html_scroll.set)
        self.html_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        html_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 画像ファイル一覧
        image_group = ttk.LabelFrame(mid_col, text="画像ファイル一覧", padding=5)
        image_group.pack(fill=tk.BOTH, expand=True)

        self.image_listbox = tk.Listbox(image_group)
        image_scroll = ttk.Scrollbar(
            image_group, orient=tk.VERTICAL, command=self.image_listbox.yview
        )
        self.image_listbox.configure(yscrollcommand=image_scroll.set)
        self.image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        image_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # --- 右カラム: ログ、アクション ---
        right_col = ttk.Frame(main_frame)
        right_col.grid(row=0, column=2, sticky="nsew", padx=5)

        # ログ
        log_group = ttk.LabelFrame(right_col, text="ログ", padding=5)
        log_group.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.log_text = scrolledtext.ScrolledText(
            log_group, state="disabled", height=10
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # ログの色設定
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("WARN", foreground="#ff9800")  # Orange-ish
        self.log_text.tag_config("ERROR", foreground="#f44336")  # Red

        # アクションボタン
        actions_frame = ttk.Frame(right_col)
        actions_frame.pack(fill=tk.X)

        self.btn_check = ttk.Button(
            actions_frame, text="実行", command=self.on_actions_row_click
        )
        self.btn_check.pack(fill=tk.X, ipady=10)

    def setup_logging(self):
        """既存のハンドラをクリア"""
        root_logger = logging.getLogger()
        for h in root_logger.handlers[:]:
            root_logger.removeHandler(h)

        root_logger.setLevel(logging.INFO)
        handler = TkLogHandler(self.log_text)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        root_logger.addHandler(handler)

    def initial_process(self):
        """GUIを初期状態にリセットする"""
        self.html_status = {}
        self.image_status = {}
        self.html_listbox.delete(0, tk.END)
        self.image_listbox.delete(0, tk.END)
        self.progress_var.set(0)
        self.status_label.config(text="待機中...")
        self.step_labels.clear()
        self.disp_process_list.clear()
        self.error_file_list.clear()
        logger.info("-" * 30)

        self.process = list(main_process.process_def.keys())[0]  # "initial_process"
        self.command_queue.put(self.process)

    def open_folder_action(self, path_str):
        """指定されたパスのフォルダを開く。存在しない場合は作成してから開く"""
        path = Path(path_str)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        if open_file_with_default_app(path):
            logger.info("フォルダを開きました: %s", path)
        else:
            messagebox.showwarning(
                "オープン失敗",
                f"フォルダ '{path}' を開けませんでした。ファイルマネージャが正しく設定されているか確認してください。",
            )

    def execute_common(self, retry=False, resume=False):
        """共通の実行＆監視フロー"""
        if (
            retry
            and self.process in main_process.process_def
            and "retryprocess" in main_process.process_def[self.process]
        ):
            self.process = main_process.process_def[self.process]["retryprocess"]
        elif (
            resume
            and self.process in main_process.process_def
            and "resumeprocess" in main_process.process_def[self.process]
        ):
            self.process = main_process.process_def[self.process]["resumeprocess"]
        else:
            self.process = main_process.process_def[self.process]["nextprocess"]

        self.command_queue.put(self.process)

    def on_actions_row_click(self):
        """アクションボタンがクリックされたときの処理"""
        # 処理中はボタンを無効化
        self.btn_check.configure(state="disabled")
        # 処理開始
        self.execute_common()
        logger.info("処理を開始しました。")

    def error_file_message(self):
        """エラーファイルがある場合にメッセージを表示し、確認するかどうかをユーザーに尋ねる"""
        if self.error_file_list:
            # 表示するファイル数を制限（最大10件）
            display_list = list(self.error_file_list)
            limit = 10
            if len(display_list) > limit:
                filenames = "\n".join(str(f) for f in display_list[:limit])
                filenames += f"\n... 他 {len(display_list) - limit} 件"
            else:
                filenames = "\n".join(str(f) for f in display_list)

            if messagebox.askyesno(
                "異常ファイル",
                f"以下のファイルを確認しますか？\n（先頭5件のみ開きます）\n{filenames}",
            ):
                # 開くファイルを5件に制限
                files_to_open = display_list[:5]
                logger.info("先頭%d件のエラーファイルを開きます。", len(files_to_open))
                opened_any = False
                for fname in files_to_open:
                    if open_file_with_default_app(fname):
                        opened_any = True

                if not opened_any and files_to_open:
                    messagebox.showwarning(
                        "オープン失敗",
                        "ファイルのオープンに失敗しました。OSに紐づけられた標準のアプリケーションを確認してください。",
                    )
            self.error_file_list.clear()  # メッセージ表示後にリセット
            return True  # エラーファイルがあったことを示す
        return False  # エラーファイルがなかったことを示す

    def open_help(self):
        """ヘルプファイル(HTML)をブラウザで開く"""
        docs_dir = Path(__file__).parent / "docs"
        help_file = docs_dir / "help.html"

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
            with open(path, "w", encoding="utf-8") as f:
                f.write(content.strip())
        except (OSError, IOError) as e:
            logger.error("ヘルプ生成失敗: %s", e)

    def show_about(self):
        """バージョン情報を表示する"""
        messagebox.showinfo(
            "バージョン情報",
            "HTML to Blogger\nVersion: 1.0.0\n\nMap Data © OpenStreetMap contributors",
        )


# --- mainエントリポイント ---
if __name__ == "__main__":
    app = App()
    app.mainloop()

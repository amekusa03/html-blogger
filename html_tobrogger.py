#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys
import os
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, simpledialog
import subprocess
import platform
import shutil
import webbrowser
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import threading
import queue
import re
import configparser

# 依存モジュール
from config import get_config
import database
import check_image_status
import main  # パイプライン処理用
import retry_errors # エラーリセット用

# --- logging設定 ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('html_tobrogger.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
logger.addHandler(logging.StreamHandler())

# --- ヘルパー関数 ---
def open_path(path):
    """OS標準のファイラ/エディタでパスを開く"""
    try:
        system = platform.system()
        if system == 'Darwin':
            subprocess.Popen(['open', str(path)])
        elif system == 'Windows':
            subprocess.Popen(['start', str(path)], shell=True)
        else:
            subprocess.Popen(['xdg-open', str(path)])
        logger.info(f"開きました: {path}")
    except Exception as e:
        messagebox.showerror("エラー", f"開けませんでした: {e}")

def open_config_file():
    open_path(Path(__file__).parent / 'config.ini')

def open_keywords_file():
    open_path(Path(__file__).parent / 'keywords.xml')

def open_georss_file():
    open_path(Path(__file__).parent / 'georss_point.xml')

# --- ToolTipクラス ---
class ToolTip:
    """ウィジェットにマウスホバー時の説明を表示するクラス"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Yu Gothic UI", "8", "normal"))
        label.pack(ipadx=2, ipady=1)

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

# --- GUIクラス ---
class HtmlToBloggerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HTML to Blogger Pipeline")
        self.geometry("950x720")
        
        # 起動時にデータベース初期化とconfig.iniの同期を行う
        database.init_db()
        
        # テーマ設定
        self.style = ttk.Style(self)
        # 可能ならモダンなテーマを使用
        themes = self.style.theme_names()
        if 'clam' in themes:
            self.style.theme_use('clam')
        
        # スタイル定義
        self.configure_styles()
        
        # 変数初期化
        self.log_queue = queue.Queue()
        self.thread = None
        self.step_labels = {}
        self.stop_requested = False
        self.upload_guide_step = 1  # 手動アップロード手順のステップ管理
        self.is_initial_run = True  # 初回実行フラグ
        
        # ロギングハンドラの設定
        self.setup_logging_handler()
        
        # UI構築
        self.create_menu()
        self.create_layout()
        
        # 初期化処理
        self.check_initialization()
        self.update_db_stats()
        
        # ログ監視開始
        self.after(100, self.poll_log_queue)

    def configure_styles(self):
        bg_color = "#f4f4f4"
        self.configure(bg=bg_color)
        
        self.style.configure("TFrame", background=bg_color)
        self.style.configure("TLabel", background=bg_color, font=("Yu Gothic UI", 10))
        self.style.configure("TButton", font=("Yu Gothic UI", 10))
        self.style.configure("TLabelframe", background=bg_color)
        self.style.configure("TLabelframe.Label", background=bg_color, font=("Yu Gothic UI", 10, "bold"))
        
        # ステップ表示用スタイル
        self.style.configure("StepPending.TLabel", foreground="#999999")
        self.style.configure("StepRunning.TLabel", foreground="#007bff", font=("Yu Gothic UI", 10, "bold"))
        self.style.configure("StepDone.TLabel", foreground="#28a745", font=("Yu Gothic UI", 10))
        self.style.configure("StepSkip.TLabel", foreground="#e0a800", font=("Yu Gothic UI", 10, "italic"))
        
        # ヘッダー
        self.style.configure("Header.TLabel", font=("Yu Gothic UI", 18, "bold"), foreground="#333")

    def setup_logging_handler(self):
        class QueueHandler(logging.Handler):
            def __init__(self, log_queue):
                super().__init__()
                self.log_queue = log_queue
            def emit(self, record):
                self.log_queue.put(self.format(record))
        
        q_handler = QueueHandler(self.log_queue)
        q_handler.setFormatter(log_formatter)
        logging.getLogger().addHandler(q_handler)
        # main.pyのloggerも捕捉
        logging.getLogger("Orchestrator").addHandler(q_handler)

    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="ブログIDを設定...", command=self.set_blog_id)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.quit)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="設定編集", menu=edit_menu)
        edit_menu.add_command(label="config.ini", command=open_config_file)
        edit_menu.add_command(label="keywords.xml", command=open_keywords_file)
        edit_menu.add_command(label="georss_point.xml", command=open_georss_file)
        
        tool_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ツール", menu=tool_menu)
        tool_menu.add_command(label="画像ステータス詳細", command=self.show_image_status)
        tool_menu.add_command(label="レポート一覧HTML作成", command=self.create_reports_index)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="使い方 (Help)", command=self.open_help)
        help_menu.add_separator()
        help_menu.add_command(label="バージョン情報", command=self.show_about)

    def create_layout(self):
        # フッターエリア（アクションボタン）を先に定義（pack順序のため、下部に固定）
        action_frame = ttk.Frame(self, padding="10")
        action_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # 右寄せのアクションボタン
        self.btn_next = ttk.Button(action_frame, text="次へ", command=self.run_pipeline, width=15)
        self.btn_next.pack(side=tk.RIGHT, padx=5)
        ToolTip(self.btn_next, "通常のパイプライン処理を開始します。\n未処理の項目のみ実行されます。")

        self.btn_force_next = ttk.Button(action_frame, text="強制的に次へ", command=self.run_force_pipeline, width=15)
        # 初期状態では非表示（update_db_statsで制御）
        ToolTip(self.btn_force_next, "エラー状態をリセットし、強制的に再実行します。\n修正後の再試行に使用してください。")

        self.btn_stop = ttk.Button(action_frame, text="停止", command=self.stop_pipeline, state=tk.DISABLED, width=10)
        self.btn_stop.pack(side=tk.RIGHT, padx=5)
        ToolTip(self.btn_stop, "実行中の処理を安全に停止します。")

        # 左側にクレジット
        credit = ttk.Label(action_frame, text="© OpenStreetMap contributors", foreground="blue", cursor="hand2")
        credit.pack(side=tk.LEFT, padx=5)
        credit.bind("<Button-1>", lambda e: webbrowser.open("https://www.openstreetmap.org/copyright/ja"))
        ToolTip(credit, "OpenStreetMapの著作権情報をブラウザで開きます")

        # メインコンテナ
        main_container = ttk.Frame(self, padding="15")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # 1. ヘッダーエリア
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(header_frame, text="HTML to Blogger Pipeline", style="Header.TLabel").pack(side=tk.LEFT)
        
        # 2. フォルダアクセスエリア
        folder_frame = ttk.LabelFrame(main_container, text="フォルダ", padding="10")
        folder_frame.pack(fill=tk.X, pady=(0, 15))
        
        folders = [
            ("📄 原稿 (Reports)", get_config('DEFAULT', 'reports_dir', './reports'), "変換元のHTMLファイルを配置するフォルダ"),
            ("⚙️ 作業中 (Work)", get_config('CLEANER', 'output_dir', './work'), "処理中のファイルが格納される作業フォルダ"),
            ("🖼️ 加工画像", './processed_images', "透かし処理済み、または手動アップロード用の画像フォルダ"),
            ("📝 投稿HTML", './blogger_html', "手動アップロード時にBloggerのHTMLを保存するフォルダ"),
            ("📦 完了分 (Archive)", get_config('ARCHIVER', 'output_dir', './archive'), "処理が完了したファイルのアーカイブ先"),
        ]
        
        for label, path_str, tip_text in folders:
            path = Path(__file__).parent / path_str
            btn = ttk.Button(folder_frame, text=label, command=lambda p=path: self.open_folder_safe(p))
            btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            ToolTip(btn, f"{tip_text}\nパス: {path}")

        # 3. ステータス＆ステップ表示エリア
        status_frame = ttk.LabelFrame(main_container, text="進行状況", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        # プログレスバー
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        self.status_lbl = ttk.Label(status_frame, text="待機中...", foreground="#555")
        self.status_lbl.pack(anchor="e")
        
        # ステップ一覧のグリッド表示
        steps_inner_frame = ttk.Frame(status_frame, padding=(0, 10, 0, 0))
        steps_inner_frame.pack(fill=tk.X)
        
        # main.pyからステップ定義を取得してラベル生成
        col_count = 3
        for i, (name, _, _) in enumerate(main.PIPELINE_STEPS):
            # 表示名を整形 (例: "1. ファイルスキャン" -> "ファイルスキャン")
            display_name = name.split('. ', 1)[1] if '. ' in name else name
            lbl = ttk.Label(steps_inner_frame, text=f"● {display_name}", style="StepPending.TLabel")
            
            r, c = divmod(i, col_count)
            lbl.grid(row=r, column=c, sticky="w", padx=10, pady=2)
            
            self.step_labels[name] = lbl

        # 4. 統計情報エリア
        stats_frame = ttk.LabelFrame(main_container, text="データベース統計", padding="10")
        stats_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.lbl_stats_art = ttk.Label(stats_frame, text="記事: -")
        self.lbl_stats_art.pack(side=tk.LEFT, padx=20)
        
        self.lbl_stats_img = ttk.Label(stats_frame, text="画像: -")
        self.lbl_stats_img.pack(side=tk.LEFT, padx=20)
        
        btn_update = ttk.Button(stats_frame, text="更新", command=self.update_db_stats, width=8)
        btn_update.pack(side=tk.RIGHT)
        ToolTip(btn_update, "データベースの統計情報を最新の状態に更新します")

        # 5. ログ出力エリア
        log_frame = ttk.LabelFrame(main_container, text="ログ", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_frame, height=10, state=tk.DISABLED, font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ログの色分けタグ
        self.log_text.tag_config('error', foreground='#d9534f')
        self.log_text.tag_config('warning', foreground='#f0ad4e')
        self.log_text.tag_config('success', foreground='#5cb85c')
        self.log_text.tag_config('info', foreground='#5bc0de')

    # --- ロジック ---

    def log_write(self, message, level="normal"):
        self.log_text.config(state=tk.NORMAL)
        tag = None
        if "ERROR" in message or "失敗" in message or "エラー" in message: tag = 'error'
        elif "WARNING" in message or "警告" in message: tag = 'warning'
        elif "成功" in message: tag = 'success'
        
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def open_folder_safe(self, path):
        """フォルダが存在しなければ作成して開く"""
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        open_path(path)

    def poll_log_queue(self):
        while True:
            try:
                record = self.log_queue.get_nowait()
            except queue.Empty:
                break
            
            # 特別なシグナル処理
            if record == "PROGRESS_DONE":
                self.finish_pipeline()
                continue
            if record == "PROGRESS_SUSPEND":
                self.suspend_pipeline()
                continue
            if record == "UPDATE_STATS":
                self.update_db_stats()
                continue
            if record == "START_MANUAL_UPLOAD_GUIDE":
                self.show_manual_upload_guide()
                continue
            if record.startswith("SHOW_MSG:"):
                _, type_, msg = record.split(":", 2)
                if type_ == "INFO": messagebox.showinfo("完了", msg)
                elif type_ == "WARN": messagebox.showwarning("警告", msg)
                elif type_ == "ERROR": messagebox.showerror("エラー", msg)
                continue

            # ステップ進行状況の解析
            # main.py: logger.info(f"\n--- {name} を実行します ---")
            # main.py: logger.warning(f"\n--- {name}: スキップされました ...")
            clean_record = record.strip()
            
            # 開始検知
            match_start = re.search(r'---\s+(.+?)\s+を実行します', clean_record)
            if match_start:
                step_name = match_start.group(1)
                self.update_step_ui(step_name, "running")
                self.status_lbl.config(text=f"実行中: {step_name}")
                self.progress_bar.step(10)

            # スキップ検知
            match_skip = re.search(r'---\s+(.+?):\s+スキップされました', clean_record)
            if match_skip:
                step_name = match_skip.group(1)
                self.update_step_ui(step_name, "skip")

            self.log_write(clean_record)
        
        self.after(100, self.poll_log_queue)

    def update_step_ui(self, step_name, state):
        """ステップラベルのスタイルを更新"""
        # 前のステップを完了にする（簡易的ロジック）
        for name, lbl in self.step_labels.items():
            if name == step_name:
                if state == "running":
                    lbl.configure(style="StepRunning.TLabel", text=f"▶ {self.get_clean_name(name)}")
                elif state == "skip":
                    lbl.configure(style="StepSkip.TLabel", text=f"- {self.get_clean_name(name)}")
            elif str(lbl['style']) == "StepRunning.TLabel":
                # 実行中だったものを完了に変更
                lbl.configure(style="StepDone.TLabel", text=f"✔ {self.get_clean_name(name)}")

    def get_clean_name(self, name):
        return name.split('. ', 1)[1] if '. ' in name else name

    def reset_steps_ui(self):
        self.progress_var.set(0)
        self.status_lbl.config(text="待機中")
        for name, lbl in self.step_labels.items():
            lbl.configure(style="StepPending.TLabel", text=f"● {self.get_clean_name(name)}")

    def show_manual_upload_guide(self):
        """手動アップロードのガイダンスを表示してフォルダを開く"""
        script_dir = Path(__file__).parent.resolve()

        if self.upload_guide_step == 1:
            # 手順1: 画像フォルダ
            msg1 = (
                "【手動アップロード手順 1/2】\n\n"
                "自動アップロードができないため、手動での操作が必要です。\n"
                "「OK」を押すと、画像が保存されているフォルダが開きます。\n\n"
                "フォルダ内の画像をBloggerの投稿画面にドラッグ＆ドロップしてアップロードしてください。\n\n"
                "作業が完了したら、このツールの「次へ」ボタンを押してください。"
            )
            messagebox.showinfo("画像アップロード", msg1)
            
            processed_images_dir = script_dir / 'processed_images'
            processed_images_dir.mkdir(exist_ok=True)
            open_path(processed_images_dir)
            
            self.upload_guide_step = 2

        else:
            # 手順2: HTML保存フォルダ
            msg2 = (
                "【手動アップロード手順 2/2】\n\n"
                "画像のアップロードが完了したら、Bloggerの投稿画面を「HTMLビュー」に切り替え、\n"
                "すべてのHTMLコードをコピーしてください。\n\n"
                "「OK」を押すと、保存先フォルダが開きます。\n"
                "コピーしたコードを新しいテキストファイル（例: blogger.html）として保存してください。\n\n"
                "保存が完了したら、再度「次へ」ボタンを押してください。"
            )
            messagebox.showinfo("HTMLの保存", msg2)
            
            blogger_html_dir = script_dir / 'blogger_html'
            blogger_html_dir.mkdir(exist_ok=True)
            open_path(blogger_html_dir)
            
            # 完了案内
            messagebox.showinfo("確認", "ファイルの保存が完了したら、再度このツールの「次へ」ボタンを押してください。\n続きの処理（URL解決）が始まります。")
            
            # 次回のためにリセット
            self.upload_guide_step = 1

    def open_reports_check(self):
        """初回実行時にreportsフォルダを確認させる"""
        self.btn_next.config(text="次へ")
        msg = (
            "【実行前の確認】\n\n"
            "「reports」フォルダを開きます。\n"
            "処理対象のHTMLファイルと画像が正しく配置されているか確認してください。\n\n"
            "確認が完了したら、もう一度「次へ」ボタンを押してください。"
        )
        messagebox.showinfo("確認", msg)
        
        script_dir = Path(__file__).parent.resolve()
        reports_dir = script_dir / get_config('DEFAULT', 'reports_dir', './reports')
        self.open_folder_safe(reports_dir)
        
        self.is_initial_run = False

    def run_force_pipeline(self):
        """強制的に次へ（エラーリセットして実行）"""
        self.is_initial_run = False # 強制実行時は初回チェックをスキップ
        self.run_pipeline(retry=True)

    def run_pipeline(self, retry=False):
        # 手動アップロード手順の途中（ステップ2）の場合
        if self.upload_guide_step == 2:
            self.show_manual_upload_guide()
            return

        # 初回実行時：reportsフォルダを開く確認
        if self.is_initial_run:
            self.open_reports_check()
            return

        if self.thread and self.thread.is_alive():
            return
        
        self.btn_next.config(state=tk.DISABLED, text="次へ")
        self.btn_force_next.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        self.reset_steps_ui()
        self.log_write(f"=== パイプライン処理を開始します (Retry={retry}) ===")
        
        def task():
            try:
                errors, manual_req = main.main(auto_retry=retry)
                self.log_queue.put("UPDATE_STATS")
                
                if manual_req:
                    self.log_queue.put("PROGRESS_SUSPEND")
                    self.log_queue.put("START_MANUAL_UPLOAD_GUIDE")
                else:
                    self.log_queue.put("PROGRESS_DONE")
                    if errors > 0:
                        self.log_queue.put(f"SHOW_MSG:ERROR:処理完了しましたが、{errors}件のエラーがあります。")
                    else:
                        self.log_queue.put("SHOW_MSG:INFO:すべての処理が正常に完了しました。")
            except Exception as e:
                logger.error(f"予期せぬエラー: {e}", exc_info=True)
                self.log_queue.put("PROGRESS_DONE")

        self.thread = threading.Thread(target=task, daemon=True)
        self.thread.start()

    def stop_pipeline(self):
        if self.thread and self.thread.is_alive():
            main.STOP_REQUESTED = True
            logger.warning("停止要求を送信しました...")
            self.btn_stop.config(state=tk.DISABLED)

    def suspend_pipeline(self):
        """手動操作待ちのためにパイプラインを一時停止状態にする"""
        self.btn_next.config(state=tk.NORMAL, text="次へ")
        self.btn_force_next.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status_lbl.config(text="一時停止中")

    def finish_pipeline(self):
        self.btn_next.config(state=tk.NORMAL, text="完了")
        self.btn_force_next.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.progress_var.set(100)
        self.status_lbl.config(text="完了")
        self.upload_guide_step = 1  # 手順リセット
        self.is_initial_run = True  # 次回クリック時に初期チェックに戻る
        # 最後の実行中ステップを完了にする
        for name, lbl in self.step_labels.items():
            if str(lbl['style']) == "StepRunning.TLabel":
                lbl.configure(style="StepDone.TLabel", text=f"✔ {self.get_clean_name(name)}")

    def run_diagnostics(self):
        self.log_write("\n=== システム診断開始 ===")
        def task():
            main.validate_prerequisites(dry_run=True)
        threading.Thread(target=task, daemon=True).start()

    def update_db_stats(self):
        try:
            stats = database.get_statistics()
            art = stats.get('articles', {})
            img = stats.get('images', {})
            
            art_error = art.get('error', 0)
            img_error = img.get('error', 0)
            total_errors = art_error + img_error
            
            art_txt = f"記事: 全{sum(art.values())} (新規:{art.get('new',0)}, 完了:{art.get('uploaded',0)}, エラー:{art_error})"
            img_txt = f"画像: 全{sum(img.values())} (新規:{img.get('new',0)}, 完了:{img.get('uploaded',0)}, エラー:{img_error})"
            
            self.lbl_stats_art.config(text=art_txt)
            self.lbl_stats_img.config(text=img_txt)
            
            # エラーがある場合のみ「強制的に次へ」ボタンを表示
            self.toggle_force_button(total_errors > 0)
        except Exception:
            pass

    def toggle_force_button(self, show):
        """「強制的に次へ」ボタンの表示/非表示を切り替える"""
        if show:
            if not self.btn_force_next.winfo_ismapped():
                # 順序を保つために btn_stop を一旦隠して再配置
                self.btn_stop.pack_forget()
                self.btn_force_next.pack(side=tk.RIGHT, padx=5)
                self.btn_stop.pack(side=tk.RIGHT, padx=5)
        else:
            if self.btn_force_next.winfo_ismapped():
                self.btn_force_next.pack_forget()

    def set_blog_id(self):
        url = get_config('OPEN_BLOGGER', 'blogger_signin_url')
        if url:
            webbrowser.open(url)
            input_url = simpledialog.askstring("Blog ID設定", "Bloggerの投稿一覧URLを入力してください:")
            if input_url:
                match = re.search(r'/posts/(\d+)', input_url)
                if match:
                    bid = match.group(1)
                    database.set_config_value('DEFAULT', 'blog_id', bid)
                    
                    # config.ini も更新して永続化する
                    try:
                        config_path = Path(__file__).parent / 'config.ini'
                        
                        # ConfigParserを使うとコメントが消えるため、テキスト置換で対応する
                        with open(config_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        
                        new_lines = []
                        for line in lines:
                            # blog_id = ... の行を探して置換 (コメント行は無視)
                            if re.match(r'^\s*blog_id\s*=', line) and not line.strip().startswith((';', '#')):
                                new_lines.append(f"blog_id = {bid}\n")
                            else:
                                new_lines.append(line)
                                
                        with open(config_path, 'w', encoding='utf-8') as f:
                            f.writelines(new_lines)
                            
                        messagebox.showinfo("成功", f"Blog IDを設定しました: {bid}")
                    except Exception as e:
                        logger.error(f"config.iniの更新失敗: {e}")
                        messagebox.showwarning("完了(一部失敗)", f"DBには保存されましたが、config.iniの更新に失敗しました。\n{e}")
                else:
                    messagebox.showerror("エラー", "IDを抽出できませんでした。")

    def show_image_status(self):
        report = check_image_status.get_image_status_report()
        self.log_write("\n" + "="*20 + " 画像ステータス " + "="*20)
        self.log_write(report)

    def check_initialization(self):
        script_dir = Path(__file__).parent
        
        # 1. credentials.json の確認
        creds_path = script_dir / 'credentials.json'
        if not creds_path.exists():
            msg = (
                "【重要：初期設定】\n\n"
                "Google APIの認証ファイル (credentials.json) が見つかりません。\n"
                "これがないとBloggerへのアップロードができません。\n\n"
                "「OK」を押すとフォルダが開きます。\n"
                "取得した credentials.json をここに配置してください。"
            )
            messagebox.showwarning("設定不足", msg)
            self.open_folder_safe(script_dir)
        
        # 2. Blog ID の確認
        # DEFAULTセクションまたはUPLOADERセクションを確認
        blog_id = get_config('DEFAULT', 'blog_id') or get_config('UPLOADER', 'blog_id')
        
        if not blog_id:
            msg = (
                "【初期設定】\n\n"
                "投稿先のブログIDが設定されていません。\n"
                "今すぐ設定を行いますか？\n\n"
                "（Bloggerにログインし、URLからIDを取得します）"
            )
            if messagebox.askyesno("設定不足", msg):
                self.set_blog_id()

        # 3. 初回認証 (token.pickle) の確認
        if creds_path.exists() and not (script_dir / 'token.pickle').exists():
            self.log_write("案内: 初回実行時にGoogle認証（ブラウザ）が求められます。", "info")

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
                <p>このツールは、ローカルのHTML記事と画像をBloggerに自動投稿するための支援ツールです。</p>
                
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
        messagebox.showinfo("バージョン情報", "HTML to Blogger Pipeline\nVersion: 1.0.0\n\n© OpenStreetMap contributors")

    def create_reports_index(self):
        """reportsフォルダ内のHTMLファイルを一覧表示するHTMLを作成して開く"""
        script_dir = Path(__file__).parent.resolve()
        reports_dir = script_dir / get_config('DEFAULT', 'reports_dir', './reports')
        output_file = script_dir / 'reports_index.html'

        if not reports_dir.exists():
            messagebox.showerror("エラー", f"フォルダが見つかりません: {reports_dir}")
            return

        try:
            html_content = [
                "<!DOCTYPE html>", "<html lang='ja'>", "<head>",
                "<meta charset='UTF-8'>", "<title>Reports Index</title>",
                "<style>",
                "body { font-family: 'Yu Gothic UI', sans-serif; padding: 20px; background-color: #f4f4f4; }",
                "h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }",
                "ul { list-style-type: none; padding-left: 20px; }",
                "li { margin: 5px 0; }",
                ".folder { font-weight: bold; color: #555; margin-top: 10px; }",
                ".file { margin-left: 20px; }",
                ".file a { text-decoration: none; color: #007bff; transition: color 0.2s; }",
                ".file a:hover { text-decoration: underline; color: #0056b3; }",
                ".container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }",
                "</style>", "</head>", "<body>",
                "<div class='container'>",
                "<h1>Reports 一覧</h1>"
            ]

            def walk_dir(current_dir):
                content = ["<ul>"]
                items = sorted(list(current_dir.iterdir()))
                
                # フォルダとファイルを分類
                folders = [x for x in items if x.is_dir()]
                files = [x for x in items if x.is_file() and x.suffix.lower() in ('.html', '.htm')]

                has_content = False

                for folder in folders:
                    sub_content = walk_dir(folder)
                    if sub_content: # 中身がある場合のみ表示
                        content.append(f"<li><div class='folder'>📁 {folder.name}</div>")
                        content.append(sub_content)
                        content.append("</li>")
                        has_content = True
                
                for file in files:
                    # 自分自身(reports_index.html)がもし含まれていたら除外
                    if file.resolve() == output_file.resolve():
                        continue
                    
                    # HTMLファイルからの相対パスを計算
                    rel_path = os.path.relpath(file, output_file.parent).replace('\\', '/')
                    content.append(f"<li class='file'>📄 <a href='{rel_path}' target='_blank'>{file.name}</a></li>")
                    has_content = True
                
                content.append("</ul>")
                return "\n".join(content) if has_content else ""

            tree_html = walk_dir(reports_dir)
            html_content.append(tree_html if tree_html else "<p>HTMLファイルが見つかりませんでした。</p>")
            html_content.append("</div></body></html>")

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(html_content))
            
            webbrowser.open(output_file.as_uri())
            self.log_write(f"レポート一覧を作成しました: {output_file}", "success")

        except Exception as e:
            logger.error(f"レポート一覧作成失敗: {e}", exc_info=True)
            messagebox.showerror("エラー", f"作成に失敗しました: {e}")

if __name__ == "__main__":
    app = HtmlToBloggerApp()
    app.mainloop()

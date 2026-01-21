# !/usr/bin/env python
# -*- coding: utf8 -*-
# https://qiita.com/nnahito/items/ad1428a30738b3d93762
# https://www.google.com/search?q=vscode+python+print%E3%82%92%E5%88%A5%E3%81%AEPython%E3%81%A7%E5%8F%96%E5%BE%97&sca_esv=d0849dc9e7ce7768&sxsrf=ANbL-n7bJ4LbOf-2BmMssNTyC0T97r3waw%3A1768968337226&ei=kVBwabnBDd3i1e8PqdnYmAU&ved=0ahUKEwj5ze_K4JuSAxVdcfUHHaksFlMQ4dUDCBE&uact=5&oq=vscode+python+print%E3%82%92%E5%88%A5%E3%81%AEPython%E3%81%A7%E5%8F%96%E5%BE%97&gs_lp=Egxnd3Mtd2l6LXNlcnAiK3ZzY29kZSBweXRob24gcHJpbnTjgpLliKXjga5QeXRob27jgaflj5blvpcyBRAAGO8FMgUQABjvBTIIEAAYgAQYogQyCBAAGIkFGKIESIuVAVDPDFjxigFwAXgBkAEAmAGJAaABmRSqAQQ3LjE4uAEDyAEA-AEBmAIaoAKHFsICChAAGEcY1gQYsAPCAgQQIxgnwgIGECEYKhgKwgIGECEYChgqmAMAiAYBkAYKkgcEMy4yM6AHiiuyBwQyLjIzuAfvFcIHCDItMjQuMS4xyAecAYAIAQ&sclient=gws-wiz-serp
import sys
import tkinter as Tkinter
import subprocess
import datetime

pythonproccess = [['キーワード作成', 'add_keywords.py'],
                ['htmlクリーニング', 'cleaner.py'],
                ['画像リンク設定', 'image_preparer.py'],
                ['Atomフィード生成', 'convert_atom.py']
#                ['ブロガー登録', 'uploader.py']]
                ['ブロガー登録', '------.py']]
root = Tkinter.Tk()
root.title(u"htmlからBloggerアップロード")
root.geometry("640x480")

process = None
progress = 0
#
# ボタンが押されるとここが呼び出される
#
def StartEntryValue(event):
    btn_text = event.widget.cget("text")
    print(f"ボタン押下: {btn_text}")
    for item in pythonproccess:
        if item[0] == btn_text:
            script_name = item[1]
            break
    # ここで処理を開始する
    global process
    process = subprocess.Popen(['python', script_name], stdout=subprocess.PIPE, text=True)
    root.after(10, update_timer)

def update_timer():
    # 1. 動作中であることを表示
    #label.config(text="処理中")     

    # 2. プロセスの終了確認
    global process
    if process is None:
    #    root.after(10, update_timer)
        return True  # タイマー継続などのフラグ 
    return_code = process.poll()

    # 3. 標準出力を読み取る（非ブロッキング）
    try:
        # 読み込める分だけすべて読み込む
        output = process.stdout.read()
        if output:
            text_widget.insert(Tkinter.END, output.strip() + "\n")
            text_widget.see(Tkinter.END)
    except Exception:
        # 読み込むデータがない場合はここを通る
        pass

    # 4. 終了判定
    if return_code is not None:
        #label.config(text="クリーニング完了" + str(return_code))
        return False  # タイマー停止などのフラグ
    
    # 10ミリ秒（1秒）後に再度この関数(update_timer)を呼び出す
    root.after(10, update_timer)
    return True


    
# ボタン
# 1. ボタンを左上に並べるためのフレーム
header_frame = Tkinter.Frame(root)
header_frame.pack(side="top", anchor="nw", padx=5, pady=5)
for item in pythonproccess:
    Button = Tkinter.Button(header_frame,text=item[0])
    Button.bind("<Button-1>",StartEntryValue)
    Button.pack(side="left", padx=5, pady=2)   

# 時間を表示するラベル
# label = Tkinter.Label(root, font=("Helvetica", 30))
# label.pack(pady=20)
# label.pack(anchor="w")

# ログ表示用テキストウィジェット
text_widget = Tkinter.Text(root, height=15, width=100)
text_widget.pack(pady=10)   

# 最初のタイマー処理を登録
update_timer()

root.mainloop()

if process is not None:
    rc = process.wait() # プロセスの終了を待機
    sys.exit(rc)  

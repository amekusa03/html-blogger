import os
import re      
import shutil
import unicodedata
import calendar
from pathlib import Path
from config import get_config
from time import sleep
import tkinter as Tkinter
from tkinter import messagebox
import webbrowser

def get_entry_text():
    set_config('BLOGGER', 'BLOGGER_BLOGENTRY_URL', bloggerentrybox.get())
    set_config('IMAGE_PREPARER', 'MEDIA_MANAGER_URL', mediaentrybox.get())
    entrybuttn["text"] = bloggerentrybox.get() 
    sub.destroy()

def on_closing():
    if messagebox.askokcancel("終了確認", "本当に終了しますか？"):
        sub.destroy() # ユーザーが「OK」を押した場合のみ終了
            
sub = Tkinter.Tk()
sub.title(u"URL入力")
sub.geometry("800x600")

#Entry
bloggerentrybox = Tkinter.Entry(sub, bd=5,width=70)
bloggerentrybox.pack(padx=3, pady=3)
mediaentrybox = Tkinter.Entry(sub, bd=5,width=70)
mediaentrybox.pack(padx=3, pady=3)

#Button
entrybuttn = Tkinter.Button(
    sub,
    width = 15,
    bg = "lightblue",
    text = "get entry",
    command = get_entry_text
)
entrybuttn.pack(pady=3)

frame = Tkinter.Frame()
frame.pack()
canvas = Tkinter.Canvas(frame, width = 500, height = 300)
canvas.pack()
img = Tkinter.PhotoImage(file = 'Bloger.png')
canvas.create_image(0, 0, image = img)


webbrowser.open(get_config('OPEN_BLOGGER', 'BLOGGER_SIGNIN_URL'), new=1)
webbrowser.open(get_config('OPEN_BLOGGER', 'MEDIA_MANAGER_URL') )

sub.protocol("WM_DELETE_WINDOW", on_closing)

sub.mainloop()
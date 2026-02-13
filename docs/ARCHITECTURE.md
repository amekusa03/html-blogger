# プロジェクト構造ガイド

HTMLtoBloggerの内部構造と各ファイルの役割を説明します。

## フォルダ構成

```
htmltobrogger/
│
├── 📄 html_tobrogger.py        ← メインGUIアプリケーション
├── 📄 config.py                ← 設定管理モジュール
├── 📄 config.json5               ← 設定ファイル（ユーザー編集対象）
│
├── 📋 処理スクリプト
│   ├── find_keywords.py         ① キーワード自動注入
│   ├── find_locate.py     ② 位置情報（地理タグ）自動付与
│   ├── clean_html.py              ③ HTMLクリーニング・メタデータ抽出
│   ├── mod_image.py   ④ 画像EXIF削除・ウォーターマーク追加
│   ├── open_blogger.py         ⑤ Blogger認証・ブラウザ起動
│   ├── upload_image.py       ⑥ 画像アップロード支援
│   ├── link_image.py         ⑦ 画像リンク編集
│   └── upload_art.py             ⑧ 自動投稿（Blogger API v3）
│
├── 📁 データフォルダ
│   ├── reports/                ← 入力：ユーザーのHTMLファイル
│   │   ├── 0205tai/
│   │   │   ├── index.html
│   │   │   ├── photo01.jpg
│   │   │   └── photo02.jpg
│   │   ├── 0209nori/
│   │   └── 0301hokai/
│   │
│   ├── work/                   ← 処理中：全段階の中間ファイル
│   │   ├── 0205tai/
│   │   │   ├── index.html      (修正版)
│   │   │   └── index.html.backup_... (自動バックアップ)
│   │   ├── 0209nori/
│   │   └── 0301hokai/
│   │
│   ├── image/                  ← リネーム済み画像（アップロード用）
│   │   ├── 0205taiphoto01.jpg
│   │   ├── 0205taiphoto02.jpg
│   │   ├── 0209noriphoto01.jpg
│   │   └── ...
│   │
│   ├── ready_load/             ← アップロード前：待機ファイル
│   │   ├── feed.atom          (Atomフィード)
│   │   ├── 0205tai_index.html
│   │   ├── 0209nori_index.html
│   │   └── config_upload.ini  (投稿設定)
│   │
│   └── finished/               ← 完了：アップロード済みファイル
│       ├── feed.atom
│       ├── 0205tai_index.html
│       └── ...
│
├── 📝 設定ファイル
│   ├── keywords.xml            ← メタキーワード定義（ユーザー編集）
│   ├── locate.xml        ← 位置情報キャッシュ（自動更新）
│   ├── credentials.json        ← Google認証（GitHubに含めない！）
│   └── token.pickle            ← 認証トークン（自動生成）
│
├── 📚 ドキュメント
│   ├── README.md               ← プロジェクト概要・セットアップ
│   ├── LICENSE                 ← MIT ライセンス
│   ├── requirements.txt         ← Python依存パッケージ一覧
│   ├── .gitignore              ← Git除外ファイル設定
│   │
│   └── docs/
│       ├── SETUP.md            ← Google Cloud API設定手順
│       ├── TROUBLESHOOTING.md   ← 問題解決ガイド
│       ├── ARCHITECTURE.md      ← アーキテクチャ詳細（このファイル）
│       └── CONTRIBUTING.md      ← 開発者向けガイド（計画中）
│
├── 📦 その他
│   ├── .github/                ← GitHub設定
│   │   └── copilot-instructions.md
│   │
│   ├── __pycache__/            ← キャッシュ（Gitで除外）
│   │
│   ├── venv/                   ← 仮想環境（Gitで除外）
│   │   ├── bin/
│   │   ├── lib/
│   │   └── ...
│   │
│   └── Blogger メディア マネージャー*.html  ← Bloggerからのダウンロード
```

## 処理パイプラインのデータフロー

```
① imort-file.py
   ファイルチェック
report/                                    ← ユーザー入力
   ↓
backup/
work/
② serial-file.py
   フォルダ除去、シリアル追加
   ↓serial/
work/ (HTML + 画像)
   ↓
③ cean-html.py
   タグ除去・メタデータ抽出
   ↓
work/ (クリーニング済み HTML)
   ↓
④ find_keywords.py
   キーワード自動抽出・注入
   source: keywords.xml
   ↓
work/ (修正版 HTML + 画像)
   ↓
⑤ find_location.py
   地理タグ自動付与
   source: locate.xml
   ↓
work/ (更新)
   ↓
⑥ find_date.py
   日付付与
   ↓
work/ (更新)
   ↓
⑦ mod-image.py
   EXIF削除・ウォーターマーク追加
   ↓
work/ (処理完了)
   ↓
⑧ upload_image.py
image/ (画像)
   Bloggerへ画像アップロード                 ←ユーザー操作  
   ↓
⑨ analize_media_manager.py
    メディアマネージャーファイル保存         ←ユーザー操作
   メディアマネージャーファイル解析
   ↓
⑩ link_html.py
   URLリンク
   ↓
⑪ up_loader.py
art_ready_load/ (投稿設定)
   自動投稿
   ↓
history/ (完了)
Blogger (オンライン)
```

## 設定ファイルの詳細

### config.json5
```ini
; 共通設定
[COMMON]
TEST_MODE = true
IMAGE_EXTENSIONS = .jpg, .jpeg, .png, .gif
HTML_EXTENSIONS = .html, .htm
XML_EXTENSIONS = .xml

; Google認証設定
[AUTH_GOOGLE]
SCOPES = https://www.googleapis.com/auth/blogger
CREDENTIALS_FILE = ./credentials.json
TOKEN_FILE = ./token.pickle

; ファイルインポート設定
[IMPORT_FILE]
INPUT_DIR = ./reports
OUTPUT_DIR = ./work
BACKUP = true
BACKUP_DIR = ./backup

; HTMLクリーン設定
[CLEAN_HTML]
INPUT_DIR = ./work
OUTPUT_DIR = ./work

; キーワード検索設定
[FIND_KEYWORD]
INPUT_DIR = ./work
OUTPUT_DIR = ./work
KEYWORDS_XML_FILE = ./keywords.xml

; 位置情報検索設定
[FIND_LOCATION]
INPUT_DIR = ./work
OUTPUT_DIR = ./work
LOCATION_XML_FILE = ./locate.xml
GEOCODE_RETRIES = 3
GEOCODE_WAIT = 1.1
GEOCODE_TIMEOUT = 10
GEOCODE_DEBUG = false

; 画像加工設定
[MOD_IMAGE]
INPUT_DIR = ./work
OUTPUT_DIR = ./work
WATERMARK_TEXT = しふとべる

; 画像アップロード設定 (手動/準備)
[UPLOAD_IMAGE]
INPUT_DIR = ./work
UPLOAD_DIR = ./image
HISTORY_DIR = ./history

; HTMLリンク設定
[LINK_HTML]
INPUT_DIR = ./work
MEDIA_MANAGER_DIR = ./
UPLOAD_DIR = ./ready_load

; 記事アップロード設定
[UPLOAD_ART]
INPUT_DIR = ./ready_load
UPLOAD_DIR = ./finished
HISTORY_DIR = ./history
BLOG_ID = 1234567890123456789
DELAY_SECONDS = 1.1
MAX_POSTS_PER_RUN = 5
MAX_RETRIES = 3

; GUI設定
[GUI]
REPORTS_DIR = ./reports
WORK_DIR = ./work
UPLOAD_DIR = ./ready_load
HISTORY_DIR = ./history
BACKUP_DIR = ./backup
BLOGGER_URL = https://www.blogger.com/blogger.g?blogID=
MEDIA_MANAGER_URL = https://www.blogger.com/mediamanager/album/
```

### keywords.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<keywords>
    <Mastkeywords>   # 必ず登録されるラベルキーワード
        <word>キーワード1</word>
        <word>キーワード2</word>
    </Mastkeywords>
    <Hitkeywords>    # 本文にあれば登録されるラベルキーワード
        <word>キーワード3</word>
        <word>キーワード4</word>
    </Hitkeywords>
</keywords>
```

### locate.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<locations>
    <location>
        <name>タイ</name>  # 地域
        <latitude>15.8700</latitude>   # 緯度
        <longitude>100.9925</longitude>   # 経度
    </location>
    <location>
        <name>東京</name>
        <latitude>35.6762</latitude>
        <longitude>139.6503</longitude>
    </location>
</locations>
```

## 依存パッケージ

| パッケージ | 用途 | version |
|-----------|------|---------|
| BeautifulSoup4 | HTMLパース | ≥4.12.0 |
| geopy | 地名→座標変換 | ≥2.3.0 |
| Pillow (PIL) | 画像処理 | ≥10.0.0 |
| piexif | EXIF削除 | ≥1.1.3 |
| janome | 形態素解析 | ≥0.4.2 |
| google-api-python-client | Blogger API | ≥2.100.0 |
| google-auth-httplib2 | Google認証 | ≥0.2.0 |
| google-auth-oauthlib | OAuth2フロー | ≥1.2.0 |
| pykakasi | 日本語変換 | ≥2.2.0 |

---

**最終更新**: 2026年2月12日

# プロジェクト構造ガイド

HTMLtoBloggerの内部構造と各ファイルの役割を説明します。

## フォルダ構成

```
htmltobrogger/
│
├── 📄 html_tobrogger.py        ← メインGUIアプリケーション
├── 📄 config.py                ← 設定管理モジュール
├── 📄 config.ini               ← 設定ファイル（ユーザー編集対象）
│
├── 📋 処理スクリプト
│   ├── add_keywords.py         ① キーワード自動注入
│   ├── add_georss_point.py     ② 位置情報（地理タグ）自動付与
│   ├── cleaner.py              ③ HTMLクリーニング・メタデータ抽出
│   ├── phot_exif_watemark.py   ④ 画像EXIF削除・ウォーターマーク追加
│   ├── open_blogger.py         ⑤ Blogger認証・ブラウザ起動
│   ├── image_preparer.py       ⑥ 画像リネーム・統合
│   ├── convert_atom.py         ⑦ Atomフィード生成
│   └── uploader.py             ⑧ 自動投稿（Blogger API v3）
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
│   ├── georss_point.xml        ← 位置情報キャッシュ（自動更新）
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
reports/                                    ← ユーザー入力
   ↓
① add_keywords.py
   キーワード自動抽出・注入
   source: keywords.xml
   ↓
work/ (修正版 HTML + 画像)
   ↓
② add_georss_point.py
   地理タグ自動付与
   source: georss_point.xml
   ↓
work/ (更新)
   ↓
③ cleaner.py
   タグ除去・メタデータ抽出
   ↓
work/ (クリーニング済み HTML)
   ↓
④ phot_exif_watemark.py
   EXIF削除・ウォーターマーク追加
   ↓
work/ (処理完了)
   ↓
⑤ open_blogger.py
   [ユーザー操作: メディアマネージャーで画像アップロード]
   ↓
Blogger メディア マネージャー.html (ダウンロード)
   ↓
⑥ image_preparer.py
   画像リネーム・URL抽出
   ↓
image/ (リネーム済み画像)
ready_load/ (投稿設定)
   ↓
⑦ convert_atom.py
   Atomフィード生成
   ↓
ready_load/feed.atom
   ↓
⑧ uploader.py
   自動投稿
   ↓
finished/ (完了)
Blogger (オンライン)
```

## 主要スクリプトの詳細

### 1️⃣ add_keywords.py
**役割**: メタキーワード自動抽出・注入
```python
# 入力
- reports/{LOCATION_CODE}/index.html
- keywords.xml

# 処理
- HTMLタイトル・見出しからキーワード抽出
- keywords.xml から マスターキーワード・ヒットキーワード取得
- 重複排除・統合
- <meta name="keywords"> タグを注入

# 出力
- work/{LOCATION_CODE}/index.html
- work/{LOCATION_CODE}/index.html.backup_... (自動バックアップ)
```

### 2️⃣ add_georss_point.py
**役割**: 地理タグ自動付与
```python
# 入力
- work/{LOCATION_CODE}/index.html
- georss_point.xml (位置情報キャッシュ)

# 処理
- HTMLから地名を抽出
- Nominatim (OpenStreetMap) で座標検索
- <georss:point> タグを注入
- 検索結果をキャッシュ（API削減）

# 出力
- work/{LOCATION_CODE}/index.html (更新)
- georss_point.xml (キャッシュ更新)
```

### 3️⃣ cleaner.py
**役割**: HTMLクリーニング・メタデータ抽出
```python
# 入力
- work/{LOCATION_CODE}/index.html

# 処理
- <b>, <font>, <span> などのフォーマット削除
- 地理タグを一時保存
- プレーンテキスト化
- タイトル・日付・キーワード抽出

# 出力
- work/{LOCATION_CODE}/index.html (クリーニング済み)
- メタデータ: title, date, keywords (内部保持)
```

### 4️⃣ phot_exif_watemark.py
**役割**: 画像処理
```python
# 入力
- work/{LOCATION_CODE}/*.jpg, *.png

# 処理
- EXIF メタデータ削除 (プライバシー保護)
- ウォーターマーク追加（右下）
- オプション：リサイズ可能

# 出力
- work/{LOCATION_CODE}/*.jpg (更新)
```

### 5️⃣ open_blogger.py
**役割**: Blogger認証・メディアマネージャー起動
```python
# 入力
- config.ini

# 処理
- ブラウザで Blogger 開く
- ユーザーがメディアマネージャーで画像アップロード
- BLOG_ID を抽出・保存

# 出力
- Blogger メディア マネージャー_[BLOG_ID].html
- config.ini (BLOG_ID 更新)
```

### 6️⃣ image_preparer.py
**役割**: 画像リネーム・URL抽出
```python
# 入力
- work/{LOCATION_CODE}/*.jpg
- Blogger メディア マネージャー.html

# 処理
- ファイル名を {LOCATION_CODE}{filename} に統一
- Blogger HTML から 画像URLを抽出
- ローカルファイル名とURLをマッピング

# 出力
- image/{LOCATION_CODE}{filename}
- ready_load/image_mapping.json (URL対応)
```

### 7️⃣ convert_atom.py
**役割**: Atomフィード生成
```python
# 入力
- work/{LOCATION_CODE}/index.html (複数)
- config.ini

# 処理
- 各HTMLからタイトル・内容・日付抽出
- Atom 1.0 形式でフィード化
- 各エントリに UUID 割り当て

# 出力
- ready_load/feed.atom
```

### 8️⃣ uploader.py
**役割**: 自動投稿
```python
# 入力
- ready_load/feed.atom
- token.pickle / credentials.json

# 処理
- Google Blogger API v3 認証
- 各エントリを投稿
- レート制限を遵守（15秒間隔）

# 出力
- Blogger (投稿作成)
- finished/ (フィーバックアップ)
- uploaded_atom_ids.txt (重複防止ログ)
```

## 設定ファイルの詳細

### config.ini
```ini
[ADD_KEYWORDS]
ENABLED = true
INPUT_FOLDER = ./reports
OUTPUT_FOLDER = ./work

[ADD_GEORSS_POINT]
ENABLED = true
INPUT_FOLDER = ./work
OUTPUT_FOLDER = ./work

[CLEANER]
ENABLED = true
INPUT_FOLDER = ./work
OUTPUT_FOLDER = ./work

[PHOROS_DELEXIF_ADDWATERMARK]
ENABLED = true
INPUT_FOLDER = ./work
OUTPUT_FOLDER = ./work
WATERMARK = © HTMLtoBlogger

[OPEN_BLOGGER]
ENABLED = true
BLOG_ID = 1234567890123456789  # 自動設定される

[IMAGE_PREPARER]
ENABLED = true
INPUT_FOLDER = ./work
OUTPUT_FOLDER = ./image
MEDIA_MANAGER_FOLDER = ./media-man

[CONVERT_ATOM]
ENABLED = true
INPUT_FOLDER = ./work
OUTPUT_FOLDER = ./ready_load
BLOG_TITLE = My Blog
BLOG_URL = https://myblog.blogspot.com

[UPLOADER]
ENABLED = true
INPUT_FOLDER = ./ready_load
OUTPUT_FOLDER = ./finished
DELAY_SECONDS = 15
```

### keywords.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<keywords>
    <Mastkeywords>
        <word>キーワード1</word>
        <word>キーワード2</word>
    </Mastkeywords>
    <Hitkeywords>
        <word>キーワード3</word>
        <word>キーワード4</word>
    </Hitkeywords>
</keywords>
```

### georss_point.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<locations>
    <location>
        <name>タイ</name>
        <latitude>15.8700</latitude>
        <longitude>100.9925</longitude>
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

## エラーハンドリング戦略

### 各段階での失敗処理

| 段階 | エラー時の動作 | 継続可能 |
|-----|-------------|--------|
| add_keywords.py | 警告出力、キーワード未挿入 | ✅ Yes |
| add_georss_point.py | 警告出力、タグ未挿入 | ✅ Yes |
| cleaner.py | 警告出力、スキップ継続 | ✅ Yes |
| phot_exif_watemark.py | ファイルごとにスキップ | ✅ Yes |
| image_preparer.py | ファイルごとにスキップ | ✅ Yes |
| convert_atom.py | エラーで中断 | ❌ No |
| uploader.py | エラーで中断 | ❌ No |

## パフォーマンス最適化

### 処理時間の目安

| 段階 | 100KB HTML | 1MB HTML | 10個画像 |
|-----|-----------|---------|---------|
| add_keywords.py | <1s | 1-2s | N/A |
| add_georss_point.py | 1.2s+ | 1.2s+ | N/A |
| cleaner.py | <1s | 1-2s | N/A |
| phot_exif_watemark.py | N/A | N/A | 2-5s |
| image_preparer.py | N/A | N/A | <1s |
| convert_atom.py | <1s | 1-2s | N/A |
| uploader.py | 30s+ | 30s+ | (レート制限) |

⚠️ **注意**: add_georss_point.py は Nominatim API 呼び出し（1.1秒/回）で時間がかかります

---

**最終更新**: 2026年1月25日

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
│   ├── locate.xml              ← 位置情報キャッシュ（自動更新）
│   ├── credentials.json        ← Google認証（GitHubに含めない！）
│   └── token.pickle            ← 認証トークン（自動生成）
│
├── 📚 ドキュメント
│   ├── README.md               ← プロジェクト概要・セットアップ
│   ├── LICENSE                 ← MIT ライセンス
│   ├── requirements.txt        ← Python依存パッケージ一覧
│   ├── .gitignore              ← Git除外ファイル設定
│   │
│   └── docs/
│       ├── SETUP.md            ← Google Cloud API設定手順
│       ├── TROUBLESHOOTING.md  ← 問題解決ガイド
│       ├── ARCHITECTURE.md     ← アーキテクチャ詳細（このファイル）
│       └── CONTRIBUTING.md     ← 開発者向けガイド（計画中）
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
① imort_file.py
   ファイルチェック
report/                                    ← ユーザー入力
   ↓
backup/
work/
② serial_file.py
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
⑦ mod_image.py
   EXIF削除・ウォーターマーク追加
   ↓
work/ (処理完了)
   ↓
⑧ upload_image.py
image/ (画像)
   Bloggerへ画像アップロード                 ←ユーザー操作  
   ↓
⑨ link_html.py
    メディアマネージャーファイル保存         ←ユーザー操作
   メディアマネージャーファイル解析
   URLリンク
   ↓
⑩ up_loader.py
art_ready_load/ (投稿設定)
   自動投稿
   ↓
history/ (完了)
Blogger (オンライン)
```

## 設定ファイルの詳細

### config.json5
```json5
{
  // 共通設定
  common: {
    test_mode: 'false',               // テストモード (true/false) 
    image_extensions: ['.jpg', '.jpeg', '.png', '.gif'], // 画像拡張子
    html_extensions: ['.html', '.htm'],  // HTML拡張子
    htmlandimage_extensions: ['.html', '.htm', '.jpg', '.jpeg', '.png', '.gif'], // HTMLと画像拡張子
    xml_extensions: ['.xml'],   // XML拡張子
  },
  // Google認証設定
  auth_google: {
    scopes: 'https://www.googleapis.com/auth/blogger',  // Blogger API スコープ
    credentials_file: './data/credentials.json',  // OAuth2認証情報ファイル
    token_file: './data/token.pickle',        // 保存トークンファイル
  },
  // ファイルインポート設定
  import_file: {
    input_dir: './data/report',          // 入力フォルダ
    output_dir: './data/work',           // 出力フォルダ
    backup: 'true',                    // ファイルバックアップ有効
    backup_dir: './data/backup',        // バックアップフォルダ
  },
  // シリアライザ設定
  serializer: {
    input_dir: './data/work',            // 入力フォルダ
    serialization_dir: './data/serialization',  // シリアライズフォルダ
    output_dir: './data/work',           // 出力フォルダ
  },
  // HTMLクリーン設定
  clean_html: {
    input_dir: './data/work',            // 入力フォルダ
    output_dir: './data/work',           // 出力フォルダ
  },
  // キーワード検索設定
  find_keyword: {
    input_dir: './data/work',            // 入力フォルダ
    output_dir: './data/work',           // 出力フォルダ
    keywords_xml_file: './data/keywords.xml',  // キーワードXMLファイル
  },
  // 位置情報検索設定
  find_location: {
    input_dir: './data/work',            // 入力フォルダ
    output_dir: './data/work',           // 出力フォルダ
    location_xml_file: './data/location.xml',  // 地域情報XMLファイル
    geocode_retries: 3,             // ジオコーディングのリトライ回数
    geocode_wait: 1.1,              // ジオコーディングの待機時間（秒）
    geocode_timeout: 10,            // ジオコーディングのタイムアウト時間（秒）
    geocode_debug: false,           // ジオコーディングのデバッグモード  
  },
  // 日付検索設定
    find_date: {
    input_dir: './data/work',        // 入力フォルダ
    output_dir: './data/work',           // 出力フォルダ（同じフォルダに上書き）
  },
  // 画像加工設定
  mod_image: {
    input_dir: './data/work',           // 入力フォルダ
    output_dir: './data/work',          // 出力フォルダ
    watermark_text: 'サンプル',            // 透かしテキスト
  },
  // 画像アップロード設定
  upload_image: {
    input_dir: './data/work',            // 入力フォルダ
    upload_dir: './data/upload',         // アップロードフォルダ
  },
  // HTMLリンク設定
  link_html: {
    input_dir: './data/work',            // 入力フォルダ
    history_dir: './data/history',       // 履歴フォルダ
    upload_dir: './data/upload',         // アップロードフォルダ
    media_manager_dir: './data/media_man', // メディアマネージャーフォルダ
    link_list_file: './data/work/image_upload_list.txt',  // 画像アップロードリストファイル名
    link_list_file_html: './data/history/image_upload_list.html',  // 画像アップロードリストhtml
  },
  // 記事アップロード設定
    upload_art: {
    input_dir: './data/work',            // 入力フォルダ
    upload_dir: './data/upload',         // アップロードフォルダ
    history_dir: './data/history',       // 履歴フォルダ
    blog_id: 1234567890123456789,   // ブログID
    delay_seconds: 11.1,            // Blogger API標準値（制限　100/100 QPS? 推奨 1.5~2 QPS?）
    max_posts_per_run: 45,          // 1回の実行で処理する最大ポスト数(API制限対 50 件/日?)
    max_retries: 3,                 // アップロードリトライ回数
  },
  // 履歴オープン設定
  history_open: {
    output_dir: './data/history',
  },
  // GUI設定
  gui: {
    reports_dir: './data/report',        // 元レポートフォルダ
    work_dir: './data/work',             // 作業フォルダ
    upload_dir: './data/upload',         // アップロードフォルダ
    history_dir: './data/history',       // 履歴フォルダ
    backup_dir: './data/backup',        // バックアップフォルダ
    blogger_url: 'https://www.blogger.com/blogger.g?blogID=',  // ブロガーURL
    media_manager_url: 'https://www.blogger.com/mediamanager/album/',   // ブロガーメディアマネージャーURL
}
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

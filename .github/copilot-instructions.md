# Blogger HTMLアップロードパイプライン - AI開発ガイド

## プロジェクト概要
**HTMLtoBlogger** は、HTML4.0形式で作成された大量のWebページをGoogle Bloggerに移行・投稿するためのローカルデスクトップツールです。Tkinter GUI (`html_tobrogger.py`)から起動される8つの連続ステージで構成され、キーワード抽出、位置情報タグ付け、HTMLクリーニング、画像処理、自動アップロードを実行します。

## アーキテクチャ概要

### データフロー
```
reports/          → work/                                      → ready_upload/      → finished/        → Blogger
  (ユーザー入力)     (キーワード注入、位置追加、EXIF削除等)      (リネーム済み画像)   (完了)            (Google API)
```

**注**: 仕様変更により、ステージ処理結果は `work/` に集約され、各ステージは config.ini で ON/OFF 制御可能

### 処理ステージ（実行順）

**操作３（メイン処理）**: 以下を順次実行
1. **cleaner.py**: HTMLからタイトル・日付・キーワードを抽出、プレーンテキスト形式で`work/`に出力
2. **add_keywords.py**: `keywords.xml`を読み込み、HTMLに`<search>`タグでキーワードを注入・マージ、オリジナルをバックアップ
3. **add_date.py**: HTML内からtime属性や日本語日付パターンから日付を抽出、`DATE:` 形式で注入
4. **add_georss_point.py**: `georss_point.xml`から地域情報を読み込み、HTML内で地域名が見つかった場合に`LOCATION:` 形式で注入
5. **phot_exif_watemark.py**: *(オプション)* 画像からEXIFデータを削除し、ウォーターマークを追加（`piexif`、`PIL`使用）
6. **delete_ready_upload.py**: `ready_upload/` フォルダ内の古いファイルをクリア
7. **image_preparer.py**: `work/`から画像をコピー・リネーム（カウンター式命名パターン使用）、`ready_upload/`に配置

**操作４**: ユーザーがメディアマネージャーで画像を手動アップロード、HTMLファイルを`media-man/`フォルダに保存

**操作５（リンク設定&Atom生成）**: 以下を順次実行
8. **html_preparer.py**: HTMLファイルを`ready_upload/`にリネーム・コピー
9. **link_html.py**: `media-man/`のメディアマネージャーHTMLから画像URLを抽出、HTML内の画像パスを置換
10. **convert_atom.py**: 処理済みHTMLからAtomフィード形式に変換（`feed.atom`生成）

**操作６（アップロード）**:
11. **uploader.py**: Google Blogger API v3を使用してポストを公開

## データフロー＆フォルダ構造（仕様変更版）

### 入力/出力フォルダ
- **`reports/`**: ユーザーが入力するソースHTMLファイル `reports/{LOCATION_CODE}/index.html`と埋め込み画像
- **`work/`**: 処理ステージ集約フォルダ - キーワード注入、位置情報追加、EXIF削除、ウォーターマーク追加などの中間ファイルを順次生成
- **`ready_upload/`**: リネーム済み画像とHTMLの出力先（`image_preparer.py`と`html_preparer.py`が`work/`から自動生成、カウンター式命名パターン使用）
- **`media-man/`**: ユーザーがBlogger メディアマネージャーからダウンロードしたHTMLファイル（`Blogger メディア マネージャー_*.html`）の保存先
- **`finished/`**: アップロード完了済みファイルの移動先
- **設定ファイル群**: `keywords.xml`、`georss_point.xml`、`config.ini`、`credentials.json` (削除しない)

### フォルダ命名規則とカウンター式ネーミング（仕様変更F）
ロケーションコードはディレクトリ名（例：`0205tai`、`0209nori`、`r0212`）。

**カウンター式命名ルール**（同名フォルダ重複防止）:
- フォーマット: `{4桁16進カウンタ}_{フォルダ名}{ファイル名}`
- 例: `reports/0205tai/photo01.jpg` → `ready_upload/0001_0205taiphoto01.jpg`
- カウンタ範囲: 0001～FFFF (1～65535件)
- 管理ファイル: `counter.txt`（プロジェクトルートに配置、4桁16進数で保存）
- 同期: 1フォルダ処理ごとに1カウンタ、画像とHTMLで同じ値を使用

## 重要な実装パターン

### HTML処理 (cleaner.py, add_keywords.py)
- **改行・タブを最初に削除**: `re.sub(r'[\r\n\t]+', '', html_text)` - 正規表現パターンが確実に機能するために、パース前に実行必須
- **キーワードマージ戦略**: HTMLから既存キーワードを抽出、Mastkeywords（常に追加）と結合、Hitkeywords（テキスト内で見つかった場合のみ）とマージ。重複を削除し、順序を維持
- **タイトル抽出の優先順位**: まず`<title>`タグを試す、フォールバックは`<h1-9>`タグ。抽出テキストから`<b>`、`<font>`、`<span>`、`<strong>`などのフォーマットタグを削除
- **日付抽出**: 第1優先：`<time datetime="...">`属性。第2優先：`(\d{4})年(\d{1,2})月(\d{1,2})日`のような正規表現パターン、日本語数字の一貫性のため`unicodedata.normalize('NFKC', text)`を使用
- **プレーンテキスト形式**: cleaner.py処理後のHTMLは以下の形式で出力：
  ```
  キーワード1,キーワード2,キーワード3
  TITLE: タイトル文字列
  DATE: 2002-04-29
  LOCATION: 地域名 | 緯度 経度
  
  <p>本文コンテンツ...</p>
  ```
- **検索タグフォーマット**: add_keywords.pyは`<search>キーワード1,キーワード2</search>`形式でキーワードを注入（カンマ周辺に空白なし）
- **HTML用の正規表現フラグ**: タグのバリエーション＆ネストされた構造に対応するため、常に`re.IGNORECASE | re.DOTALL`を使用

### add_keywords.py の詳細
- **キーワードソース**: `Mastkeywords`（常に注入）、`Hitkeywords`（テキスト内で見つかった場合のみ注入）
- **バックアップ作成**: 変更前に必ず`{filename}.backup_YYYYMMDD_HHMMSS`を作成。バックアップ失敗時は警告で継続
- **重複キーワード**: 既存HTMLキーワード（`<search>`タグから抽出） + Mast + Hitをマージ、重複を削除、追加順を維持
- **注入ポイント**: `<search>`タグを`</title>`の直後に挿入。`<title>`がない場合は`<head>`の直後。どちらもない場合はファイルの先頭に追加
- **config.ini での制御**: `[ADD_KEYWORDS]` セクションに `ENABLED = true/false` で処理の ON/OFF 制御

### add_date.py の詳細
- **日付抽出**: `<time datetime="...">`属性を優先、見つからない場合は本文から日本語日付パターンを検索
- **日付正規化**: `unicodedata.normalize('NFKC', text)`で全角数字を半角に統一
- **日付形式変換**: `2002.04.25`、`2002/04/25`などを`2002年04月25日`に変換
- **範囲日付サポート**: `2003年1/18〜20`のようなパターンから最初の日付を抽出
- **出力フォーマット**: ISO形式 `DATE: YYYY-MM-DD` で注入
- **config.ini での制御**: `[ADD_DATE]` セクションに `ENABLED = true/false` で処理の ON/OFF 制御

### add_georss_point.py の詳細
- **位置情報ソース**: `georss_point.xml`から地域名・緯度・経度を読み込み（形式：`<location><name>地域名</name><latitude>緯度</latitude><longitude>経度</longitude></location>`）
- **地域名検出**: Janome形態素解析で地名を抽出、HTML内でマッチする場合に採用（大文字小文字区別なし、複数見つかった場合は最後のものを使用）
- **外部API使用**: Nominatim (OpenStreetMap) を使用して未知の地名から緯度経度を取得（レート制限：1.1秒/リクエスト厳守、結果はXMLにキャッシュ）
- **注入フォーマット**: プレーンテキスト形式 `LOCATION: 地域名 | 緯度 経度` で出力
- **Atom フィード拡張**: convert_atom.pyが`LOCATION:`行から地域情報を読み取り、Atomエントリに追加：`<blogger:location><blogger:name>地域名</blogger:name><blogger:latitude>...</blogger:latitude><blogger:longitude>...</blogger:longitude></blogger:location>`
- **依存ライブラリ**: `geopy`（Nominatim）、`janome`（形態素解析）
- **config.ini での制御**: `[ADD_GEORSS_POINT]` セクションに `ENABLED = true/false` で処理の ON/OFF 制御

### cleaner.py の詳細
- **出力ファイル名フォーマット**: タイトル・日付・キーワードを抽出、`work/{FOLDER_NAME}/{original_filename}.html`に出力
- **メタデータ抽出**: タイトル（`<title>`または`<h1-9>`）を抽出、整形タグを削除
- **タグクリーニング**: `<script>`、`<style>`、`<meta>`タグを完全削除。`<head>`、`<title>`、`<search>`、`<time>`は保持
- **属性削除**: すべてのHTMLタグから属性を削除（`class`、`style`など）してシンプル化
- **改行整理**: `<br>`、`<p>`、`<div>`、`<h1-9>`、`<li>`タグを改行に変換
- **重大削除チェック**: 処理前後の本文テキスト長を比較、50%以上減少した場合は警告を出力
- **エラーハンドリング**: タイトルが見つからない場合、警告を出力するが継続（失敗しない）
- **config.ini での制御**: `[CLEANER]` セクションに `ENABLED = true/false` で処理の ON/OFF 制御

### phot_exif_watemark.py の詳細
- **EXIF削除**: `piexif.remove()`で画像位置情報など全EXIFデータを削除（プライバシー保護）
- **ウォーターマーク追加**: 透かしテキスト（`config.ini`の`WATERMARK`設定）を右下に配置、サイズは画像の1/4
- **処理対象**: `.jpg`、`.jpeg`、`.png`形式の画像ファイル
- **依存ライブラリ**: `piexif`、`PIL (Pillow)`
- **config.ini での制御**: `[PHOROS_DELEXIF_ADDWATERMARK]` セクションに `ENABLED = true/false` で処理の ON/OFF 制御

### open_blogger.py の詳細
- **ブラウザ自動起動**: `webbrowser`モジュールで Blogger サインインURL と メディアマネージャーURL を開く
- **BLOG_ID抽出**: ユーザーが GUI ダイアログに貼り付けたURL（`https://www.blogger.com/blog/posts/{BLOG_ID}`形式）から正規表現 `r'/posts/(\d+)'` で抽出
- **設定自動保存**: 抽出した BLOG_ID を `config.ini` の `[OPEN_BLOGGER]` セクションに自動書き込み
- **クロスプラットフォーム対応**: macOS（`open`）、Windows（`start`）、Linux（`xdg-open`）でそれぞれブラウザを起動

### image_preparer.py の詳細
- **画像発見**: `work/` フォルダから画像をコピー・リネーム（`config.ini`の`[READY_UPLOAD]`セクションで設定）
- **サポート形式**: `.jpg`、`.jpeg`、`.png`、`.gif`（大文字小文字区別なし）
- **リネームパターン（カウンター式）**: `{4桁16進カウンタ}_{folder_name}{original_filename}`
  - 例：`work/0205tai/photo01.jpg` → `ready_upload/0001_0205taiphoto01.jpg`
  - カウンタ管理: `counter.txt` から読み込み、フォルダ処理完了後にインクリメント
  - フォルダ単位: 1フォルダの全画像に同じカウンタを使用
- **コピー操作**: メタデータを保存するため`shutil.copy2()`を使用。出力フォルダは`mkdir(parents=True, exist_ok=True)`で作成
- **出力先**: `./ready_upload/` フォルダにリネーム済み画像を配置（Bloggerへの手動アップロード用）
- **エラーハンドリング**: ファイルごとにtry/except、エラー出力後も他のファイル処理を継続
- **config.ini での制御**: `[READY_UPLOAD]` セクションに `INPUT_DIR`、`OUTPUT_DIR` で入出力パス設定

### html_preparer.py の詳細
- **HTMLコピー**: `work/` フォルダから処理済みHTMLを `ready_upload/` にコピー
- **リネームパターン（カウンター式）**: `{4桁16進カウンタ}_{folder_name}{original_filename}.html`
  - 例：`work/0205tai/tai.html` → `ready_upload/0001_0205taitai.html`
  - カウンタ管理: `counter.txt` から読み込み、フォルダ処理完了後にインクリメント
  - 同期: `image_preparer.py` と同じカウンタ値を使用（フォルダ単位で管理）
- **出力先**: `./ready_upload/` フォルダにリネーム済みHTMLを配置

### link_html.py の詳細
- **メディアマネージャー解析**: `media-man/Blogger メディア マネージャー_*.html` から画像URLマッピングを抽出
- **複数ファイルチェック**: media-manフォルダ内に複数のメディアマネージャーファイルがある場合はエラーで中断
- **画像URL置換**: `ready_upload/` 内のHTML内の画像パスをBlogger URLに置換
- **サイズマッピング**: 元の画像サイズを標準サイズにマップ（横長: 640×480, 400×300など、縦長: 480×640, 300×400など）
- **URL抽出パターン**: `<a href="...googleusercontent.com...">` からURLを抽出、ファイル名でマッピング

### delete_ready_upload.py の詳細
- **フォルダクリア**: `ready_upload/` フォルダ内のファイルを削除（次の処理のため）
- **除外パターン**: `.gitkeep` などの隠しファイルは保持

### convert_atom.py の詳細
- **Atomフィード生成**: `ready_upload/`内の各HTMLをAtomエントリに変換、`feed.atom`ファイルを生成
- **メタデータ抽出**: プレーンテキスト形式からメタデータを抽出：
  - 1行目: キーワード（カンマ区切り）
  - `TITLE:` で始まる行: タイトル
  - `DATE:` で始まる行: 日付（ISO形式）
  - `LOCATION:` で始まる行: 地域情報（`地域名 | 緯度 経度`形式）
- **地域情報統合**: `LOCATION:` 行から地域情報を読み取り、Atomエントリに `<blogger:location>` タグで埋め込み
- **エントリID生成**: 各ポスト用に UUID 生成（`uuid.uuid4()`）
- **フィード設定**: `config.ini` の `[CONVERT_ATOM]` セクション (`BLOG_TITLE`、`BLOG_URL`) を使用
- **出力先**: `ready_upload/feed.atom`

### Google Blogger API統合 (uploader.py)
- **OAuthフロー**:
  1. `token.pickle`から既存の認証情報を確認
  2. 期限切れ/無効な場合、`creds.refresh(Request())`でリフレッシュ
  3. 有効な認証情報がない場合、`InstalledAppFlow.from_client_secrets_file()`でインタラクティブ認証実行
  4. リフレッシュされた認証情報を`token.pickle`に自動保存
- **画像URL抽出**: `Blogger メディア マネージャー_{ブログ名}.html`をBeautifulSoup（`html.parser`エンジン）でパース、すべての`<a href="...googleusercontent.com...">` URLを抽出、ファイル名でマッピング
  - **重要**: 同じフォルダーに複数のMediaManager HTMLファイルが存在する場合は**エラーとして処理を中断**し、ユーザーに正確なファイルを1つだけ残すようメッセージ表示
  - ファイル名の `{ブログ名}` 部分はユーザーのブログ名によって変わる
- **サイズマッピング**: 元の画像サイズを標準サイズにマップ：
  - 横長 (w > h): 640×480、400×300、320×240、200×150
  - 縦長 (h ≥ w): 480×640、300×400、240×320、150×200
- **レート制限**: ポスト提出間に`time.sleep(15)`を挿入（`DELAY_SECONDS`で設定可能）
- **API呼び出しパターン**: `service.posts().insert(blogId=BLOG_ID, body=post_body).execute()`

## キー設定ファイル
- **`keywords.xml`**: `<Mastkeywords>`と`<Hitkeywords>`ノード付きXML、各々に`<word>`子要素
- **`georss_point.xml`**: 位置情報XML（`<location><name>地域名</name><latitude>緯度</latitude><longitude>経度</longitude></location>`）、Nominatim キャッシュ用
- **`config.ini`**: `get_config(section, key)`経由の使用パターンについては`config.py`を参照
  - セクション：`[ADD_KEYWORDS]`、`[ADD_GEORSS_POINT]`、`[CLEANER]`、`[PHOROS_DELEXIF_ADDWATERMARK]`、`[OPEN_BLOGGER]`、`[IMAGE_PREPARER]`、`[CONVERT_ATOM]`、`[UPLOADER]`
  - 処理制御フラグ：各セクションに `ENABLED = true/false` で ON/OFF 制御（仕様変更A）
- **`credentials.json`**: Google Cloud ConsoleからのOAuth認証情報（Desktop App型、プロジェクトルートに配置）
- **`token.pickle`**: 最初のOAuthフロー後に自動生成、認証セッションを永続化
- **`uploaded_atom_ids.txt`**: アップロード済みポストIDのログ（重複投稿防止用）

### プロジェクト管理ファイル
- **`memo-spec.md`**: 仕様メモ（開発者用）
- **`Todo.md`**: タスク管理
- **`counter.txt`**: カウンター管理ファイル（4桁16進数、0001～FFFF）- ファイルネーミングのユニーク性保証用
- **`venv/` または `.venv/`**: Python仮想環境（Gitで除外、各環境で個別作成）
- **`.github/copilot-instructions.md`**: このファイル - AI開発エージェント用ガイド

## 一般的なワークフロー

### 環境セットアップ
```bash
# 仮想環境作成・有効化
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 依存パッケージインストール
pip install -r requirements.txt

# Google Cloud認証設定（詳細は docs/SETUP.md 参照）
# credentials.json をプロジェクトルートに配置
```

### フルパイプライン実行
```bash
# GUI から実行（メインエントリーポイント - 推奨）
python html_tobrogger.py
# ボタンはスクリプトを順次起動、テキストウィジェットで出力を監視

# または個別実行（デバッグ用）
python cleaner.py           # HTMLクリーニング・メタデータ抽出
python add_keywords.py      # キーワード注入
python add_georss_point.py  # 位置情報注入
python phot_exif_watemark.py # EXIF削除・ウォーターマーク追加（オプション）
python image_preparer.py    # 画像リネーム・統合
python open_blogger.py      # BrowserでBlogger開き、BLOG_ID取得
python convert_atom.py      # Atomフィード生成
python uploader.py          # Blogger API へのアップロード
```

### クイックスタートコマンド
```bash
# 新規セットアップ（初回のみ）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac (Windows: venv\Scripts\activate)
pip install -r requirements.txt

# GUIアプリ起動（通常の使用）
python html_tobrogger.py

# 設定ファイル編集（GUIメニューからも可能）
# - config.ini: 全般設定
# - keywords.xml: キーワード定義
# - georss_point.xml: 位置情報キャッシュ（自動更新）
```

### 単一ステージのテスト
- 中間フォルダを使用：`work/`（各処理後の出力）
- 問題を分離するため、次のステージ実行前に出力を確認
- GUI統合：`html_tobrogger.py`の`pythonproccess`リスト（各スクリプトとラベルのペア）で実行順序を定義
- **テスト推奨**: 最初は小規模データ（1-2ファイル）で動作確認、`config.ini`の`MAX_POSTS_PER_RUN = 1`に設定して1件ずつ投稿テスト

## 開発ノート

### Unicode/エンコーディング
- すべてのファイルはUTF-8エンコーディング使用（`# -*- coding: utf8 -*-`または`# coding: utf-8`）
- フォルダ名は日本語ロケーションコード（ローマ字化なし）；ファイル名はASCII
- 日付パース時は、日本語数字一貫性のため`unicodedata.normalize('NFKC', html)`を使用

### エラーハンドリングパターン
- **XML解析失敗** (add_keywords.py): 空リストを返す、警告で慎重に継続
- **ファイル欠落**: 操作前に`os.path.exists()`または`Path.exists()`で確認；警告後も継続
- **BeautifulSoup HTMLパース**: `'html.parser'`エンジン使用（`'lxml'`ではなく）；不正形式なHTMLもグレースフルに処理
- **バックアップ失敗** (add_keywords.py): 警告で継続、全プロセスを失敗させない

### GUIアーキテクチャ (html_tobrogger.py)
- **GUI実装**: シングルスレッドTkinterで`subprocess.Popen()`経由で子プロセスを順次起動
- **出力キャプチャ**: `process.stdout.read()`で非ブロッキングループ内（10ms ポーリング `root.after(10, update_timer)`）に出力をキャプチャ
- **処理フロー定義**: プロセス間通信なし；フォルダ状態でのデータフローに依存
  ```python
  pythonproccess = [['クリーニング', 'cleaner.py'],
                    ['キーワード作成', 'add_keywords.py'],
                    ['日付追加', 'add_date.py'],
                    ['位置情報追加', 'add_georss_point.py'],
                    ['画像位置情報削除＆ウォーターマーク追加', 'phot_exif_watemark.py'],
                    ['アップロードフォルダ削除', 'delete_ready_upload.py'],
                    ['画像リネーム', 'image_preparer.py']]
  pythonproccess_step5 = [['HTMLリネーム', 'html_preparer.py'],
                          ['リンク設定', 'link_html.py'],
                          ['Atomフィード生成', 'convert_atom.py']]
  pythonproccess_upload = [['アップロード', 'uploader.py']]
  ```
- **メニューバー機能**: `config.ini`、`keywords.xml`、`georss_point.xml`を標準アプリで開く（クロスプラットフォーム対応）
- **操作ボタン構成**:
  1. **フォルダを開く**: `reports/` フォルダを開く（HTMLファイルを配置）。ファイルが既にある場合は削除確認ダイアログを表示
  2. **開始**: メイン処理実行（cleaner → add_keywords → add_date → add_georss_point → phot_exif_watemark → delete_ready_upload → image_preparer）
  3. **メディアマネージャーを開く**: `media-man/` フォルダを開く（メディアマネージャーHTMLの保存先）
  4. **画像フォルダを開く**: `ready_upload/` フォルダを開く（リネーム済み画像の確認・手動アップロード用）
  5. **リンク設定&Atomフィード生成**: html_preparer → link_html → convert_atom を実行
  6. **アップロード**: uploader.py で Blogger API 経由で自動投稿
- **起動時警告（仕様変更D）**: `token.pickle` がない場合は警告を出す（ただし操作は続行可能）
- **フォルダクリア警告（仕様変更D）**: ユーザーが「フォルダを開く」ボタンを押時に、`reports/`、`work/`、`image/` に ファイルがあれば確認ダイアログを表示。OK で全削除（`*.xml`、`finished/` は除外）

### 設定管理 (config.py)
- `config.ini`経由でセクションベースの組織化で一元管理（コメント`#`削除、引用符除去を自動処理）
- `get_config(section, key, default=None)`関数で安全な設定取得を処理
- `DEFAULTS`辞書にすべてのセクションにデフォルト値を提供
- すべてのパスは相対パス（例：`./reports`、`./work`）をスクリプト位置相対で使用

## 外部依存関係
- **Google APIs**: `google-auth-oauthlib`、`google-auth-httplib2`、`google-api-python-client` - Blogger API v3認証・投稿用
  - ⚠️ **重要**: Blogger APIは30日間アクセスがないと警告メールが送信され、アクセスキーが削除される。定期的に使用すること
- **HTML/XML処理**: `BeautifulSoup4` (`html.parser`エンジン) - HTMLパース、`xml.etree.ElementTree` - XML設定読み込み
- **画像処理**: `Pillow (PIL)` - ウォーターマーク追加、`piexif` - EXIF削除
- **位置情報**: `geopy` (Nominatim) - 地名→緯度経度変換（OpenStreetMap、レート制限1.1秒/リクエスト）
  - **設計判断**: Google Geocoding APIではなくNominatim（OpenStreetMap）を使用する理由は、クレジットカード登録を避けるため
- **形態素解析**: `janome` - 日本語地名抽出用
- **GUI**: `tkinter` (標準ライブラリ) - デスクトップアプリインターフェース

## 一般的な陥穽と警告パターン（仕様変更D）

### 重大エラー - 警告して中断
1. **HTML クリーニング時にコンテンツ削除**: 過度に積極的な正規表現置換；サンプルHTMLで最初にテストして検証してから本実行すること
2. **画像URL がマッピングされない**: MediaManager HTMLフォーマット変更の可能性；ファイル名がリンクできなかった場合は「この画像ファイルが紐付けできませんでした」と一覧表示
   - ユーザーに「操作５から やり直すか」「アップロード後に手動修正するか」を選択させる
3. **MediaManager HTML が複数存在**: `Blogger メディア マネージャー_{ブログ名}.html` が2つ以上ある場合は エラーとして処理を中断し、ユーザーに正確なファイル（1つだけ）を残すようメッセージ表示
4. **アップロード がサイレント失敗**: BLOG_IDが設定されていない、認証情報が無効、またはレート制限ヒット；実行前にこれらを確認し、エラー時は明示的なエラーメッセージを出力して中断
5. **Nominatimレート制限違反**: 大量の地名処理時、1.1秒間隔を厳守（`time.sleep(1.1)`）。違反するとOpenStreetMapからブロックされる可能性あり
6. **同名フォルダによるデータ上書きリスク**: 元データが `report1/r0001/`、`report2/r0001/` のように異なるソースから同名フォルダが存在する場合、`reports/` に順次コピーすると上書きが発生。カウンター式ネーミング（`counter.txt`）でユニーク性を保証

### 警告が出ても継続する場合
- **キーワード注入されない**: XMLが不正形式でもアップロード可能（警告は出力される）
- **日付抽出失敗**: 日付が抽出できなくてもアップロード可能（警告は出力される）
- **token.pickle がない**: 起動時に警告を出すが、アップロード時にエラーになるまで処理は続行可能（仕様変更D）

## OpenStreetMap 属性表示（仕様変更E）
GUI画面およびREADMEに以下の表示を追加する：
```
© OpenStreetMap contributors
https://www.openstreetmap.org/copyright/ja
```

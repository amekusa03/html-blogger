# Blogger HTMLアップロードパイプライン - AI開発ガイド

## プロジェクト概要
**HTMLtoBlogger** は、HTML4.0形式で作成された大量のWebページをGoogle Bloggerに移行・投稿するためのローカルデスクトップツールです。Tkinter GUI (`html_tobrogger.py`)から起動される8つの連続ステージで構成され、キーワード抽出、位置情報タグ付け、HTMLクリーニング、画像処理、自動アップロードを実行します。

## アーキテクチャ概要

### データフロー
```
reports/          → work/                                      → image/             → ready_load/  → finished/    → Blogger
  (ユーザー入力)     (キーワード注入、位置追加、EXIF削除等)      (ユーザーが配置)    (アップロード待機)  (完了)       (Google API)
```

**注**: 仕様変更により、ステージ処理結果は `work/` に集約され、各ステージは config.ini で ON/OFF 制御可能

### 処理ステージ（実行順）
1. **add_keywords.py**: `keywords.xml`を読み込み、HTMLに`<meta name="keywords">`を注入・マージ、オリジナルをバックアップ
2. **add_georss_point.py**: `georss_point.xml`から地域情報を読み込み、HTML内で地域名が見つかった場合に`<georss:point>`タグを`<head>`内に注入（複数見つかった場合は最後のものを採用）
3. **cleaner.py**: HTMLからタイトル・日付・キーワードを抽出、すべてのフォーマットを削除、`work/`に出力
4. **phot_exif_watemark.py**: *(オプション)* 画像からEXIFデータを削除し、ウォーターマークを追加（`piexif`、`PIL`使用）
5. **open_blogger.py**: ブラウザでBloggerサインインとメディアマネージャーを開き、URLからBLOG_IDを抽出して`config.ini`に自動保存
6. **image_preparer.py**: `work/`から画像をコピー・リネーム（`{folder_name}{filename}`パターン使用）、`image/`に配置
7. **convert_atom.py**: クリーニング済みHTMLからAtomフィード形式に変換（`feed.atom`生成）
8. **uploader.py**: Google Blogger API v3を使用してポストを公開

## データフロー＆フォルダ構造（仕様変更版）

### 入力/出力フォルダ
- **`reports/`**: ユーザーが入力するソースHTMLファイル `reports/{LOCATION_CODE}/index.htm`と埋め込み画像
- **`work/`**: 処理ステージ集約フォルダ - キーワード注入、位置情報追加、EXIF削除、ウォーターマーク追加などの中間ファイルを順次生成
- **`image/`**: ユーザーがアップロード用画像をここに配置（リネーム済み: `{folder_name}{filename}`パターン）
- **`ready_load/`**: アップロード前の待機フォルダ - Atomフィード・HTMLファイル・設定情報を保持
- **`finished/`**: アップロード完了済みファイルの移動先（`ready_load/`から処理後に移動）
- **設定ファイル群**: `keywords.xml`、`georss_point.xml`、`config.ini`、`credentials.json` (削除しない)

### フォルダ命名規則
ロケーションコードはディレクトリ名（例：`0205tai`、`0209nori`、`1404tokyo`）。これらが画像名プレフィックスになる：
- ソース: `reports/0205tai/photo01.jpg` → リネーム後: `image/0205taiphoto01.jpg`

## 重要な実装パターン

### HTML処理 (cleaner.py, add_keywords.py)
- **改行・タブを最初に削除**: `re.sub(r'[\r\n\t]+', '', html_text)` - 正規表現パターンが確実に機能するために、パース前に実行必須
- **キーワードマージ戦略**: HTMLから既存キーワードを抽出、Mastkeywords（常に追加）と結合、Hitkeywords（テキスト内で見つかった場合のみ）とマージ。重複を削除し、順序を維持
- **タイトル抽出の優先順位**: まず`<title>`タグを試す、フォールバックは`<h1-9>`タグ。抽出テキストから`<b>`、`<font>`、`<span>`、`<strong>`などのフォーマットタグを削除
- **日付抽出**: 第1優先：`<time datetime="...">`属性。第2優先：`(\d{4})年(\d{1,2})月(\d{1,2})日`のような正規表現パターン、日本語数字の一貫性のため`unicodedata.normalize('NFKC', text)`を使用
- **メタタグフォーマット**: 厳密に必須：`<meta name="keywords" content="word1,word2,word3">` （カンマ周辺に空白なし）
- **HTML用の正規表現フラグ**: タグのバリエーション＆ネストされた構造に対応するため、常に`re.IGNORECASE | re.DOTALL`を使用

### add_keywords.py の詳細
- **キーワードソース**: `Mastkeywords`（常に注入）、`Hitkeywords`（テキスト内で見つかった場合のみ注入）
- **地域名抽出（新規）**: `<title>`・`<h1~9>`から記号（＝、ー、・、＿、"、'、＆、／）で区切り、位置情報検索用に地域名を抽出
- **Nominatim キャッシング**: `georss_point.xml` に一度検索した地名を保存、未知の地名のみ Nominatim クエリを発行（レート制限1.1秒厳守）
- **バックアップ作成**: 変更前に必ず`{filename}.backup_YYYYMMDD_HHMMSS`を作成。バックアップ失敗時は警告で継続
- **重複キーワード**: 既存HTMLキーワード + Mast + Hitをマージ、重複を削除、追加順を維持
- **注入ポイント**: `</head>`タグの直前に挿入。見つからない場合は`</body>`の直前。どちらも見つからない場合は`</html>`を閉じる前に追加
- **config.ini での制御**: `[ADD_KEYWORDS]` セクションに `ENABLED = true/false` で処理の ON/OFF 制御

### add_georss_point.py の詳細
- **位置情報ソース**: `georss_point.xml`から地域名・緯度・経度を読み込み（形式：`<location><name>地域名</name><latitude>緯度</latitude><longitude>経度</longitude></location>`）
- **地域名検出**: Janome形態素解析で地名を抽出、HTML内でマッチする場合に採用（大文字小文字区別なし、複数見つかった場合は最後のものを使用）
- **外部API使用**: Nominatim (OpenStreetMap) を使用して未知の地名から緯度経度を取得（レート制限：1.1秒/リクエスト厳守、結果はXMLにキャッシュ）
- **注入ポイント**: `<georss:point>{緯度} {経度}</georss:point>`を`<head>`タグ内に挿入
- **Atom フィード拡張（新規）**: 検出した地域情報を Atom エントリに追加：`<blogger:location><blogger:name>地域名</blogger:name><blogger:latitude>...</blogger:latitude><blogger:longitude>...</blogger:longitude><blogger:span>...</blogger:span></blogger:location>`
- **依存ライブラリ**: `geopy`（Nominatim）、`janome`（形態素解析）
- **config.ini での制御**: `[ADD_GEORSS_POINT]` セクションに `ENABLED = true/false` で処理の ON/OFF 制御

### cleaner.py の詳細
- **出力ファイル名フォーマット**: タイトル・日付・キーワードを抽出、`work/{FOLDER_NAME}/{title_or_default}.html`に出力
- **メタデータ保存**: HTMLクリーニング前にタイトル・日付・キーワードを抽出（クリーニングですべてのタグが削除されるため）
- **コンテンツ抽出**: すべてのHTMLタグを削除：`re.sub(r'</?(B|font|span|strong).*?>', '', text, flags=re.IGNORECASE)`
- **エラーハンドリング**: タイトル・日付が見つからない場合、警告を出力するが継続（失敗しない）。ファイル名にはセンスのあるデフォルト値を使用
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
- **クロスプラットフォーム**: macOS（`open`）、Windows（`start`）、Linux（`xdg-open`）で動作
- **エラーハンドリング**: 不正なURL入力の場合は エラーメッセージを表示し、操作をやり直すよう促す

### image_preparer.py の詳細
- **画像発見**: `work/` フォルダから画像をコピー・リネーム
- **サポート形式**: `.jpg`、`.jpeg`、`.png`、`.gif`（大文字小文字区別なし）
- **リネームパターン**: `{folder_name}{original_filename}`（例：`0205tai/photo01.jpg` → `0205taiphoto01.jpg`）
- **コピー操作**: メタデータを保存するため`shutil.copy2()`を使用。出力フォルダは`mkdir(parents=True, exist_ok=True)`で作成
- **HTML内パス置換**: リネーム後、HTML内の旧ファイル名参照も新ファイル名に自動置換
- **エラーハンドリング**: ファイルごとにtry/except、エラー出力後も他のファイル処理を継続

### convert_atom.py の詳細
- **Atomフィード生成**: `work/`内の各HTMLをAtomエントリに変換、`feed.atom`ファイルを生成
- **メタデータ抽出**: 各HTMLからキーワード・タイトル・日付を抽出（優先：元の`reports/`フォルダの`.htm`ファイル）
- **地域情報統合（新規）**: `georss_point.xml` から検出された地域情報を Atom エントリに埋め込み（`<blogger:location>`タグ）
- **エントリID生成**: 各ポスト用に UUID 生成（`uuid.uuid4()`）
- **フィード設定**: `config.ini` の `[CONVERT_ATOM]` セクション (`BLOG_TITLE`、`BLOG_URL`) を使用

### Google Blogger API統合 (uploader.py)
- **OAuthフロー**:
  1. `token.pickle`から既存の認証情報を確認
  2. 期限切れ/無効な場合、`creds.refresh(Request())`でリフレッシュ
  3. 有効な認証情報がない場合、`InstalledAppFlow.from_client_secrets_file()`でインタラクティブ認証実行
  4. リフレッシュされた認証情報を`token.pickle`に自動保存
- **画像URL抽出**: `Blogger メディア マネージャー_ddd.html`をBeautifulSoup（`html.parser`エンジン）でパース、すべての`<a href="...googleusercontent.com...">` URLを抽出、ファイル名でマッピング
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
# GUI から実行（メインエントリーポイント）
python html_tobrogger.py
# ボタンはスクリプトを順次起動、テキストウィジェットで出力を監視

# または個別実行（デバッグ用）
python add_keywords.py      # キーワード注入
python add_georss_point.py  # 位置情報注入
python cleaner.py           # HTMLクリーニング・メタデータ抽出
python phot_exif_watemark.py # EXIF削除・ウォーターマーク追加（オプション）
python open_blogger.py      # BrowserでBlogger開き、BLOG_ID取得
python image_preparer.py    # 画像リネーム・統合
python convert_atom.py      # Atomフィード生成
python uploader.py          # Blogger API へのアップロード
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
  pythonproccess = [['キーワード作成', 'add_keywords.py'],
                    ['位置情報追加', 'add_georss_point.py'],
                    ['htmlクリーニング', 'cleaner.py'],
                    ['画像位置情報削除＆ウォーターマーク追加', 'phot_exif_watemark.py']]
  pythonproccess_step5 = [['画像リンク設定', 'image_preparer.py'],
                          ['Atomフィード生成', 'convert_atom.py']]
  pythonproccess_upload = [['アップロード', 'uploader.py']]
  ```
- **メニューバー機能**: `config.ini`、`keywords.xml`、`georss_point.xml`を標準アプリで開く（クロスプラットフォーム対応）
- **操作ボタン構成**:
  1. **操作１**: `reports/` フォルダを開く
  2. **操作２**: メディアマネージャー（`media-man/`）フォルダを開く  
  3. **操作３**: メイン処理実行（`pythonproccess`リスト）
  4. **操作４**: Bloggerメディアマネージャーをブラウザで開く + BLOG_ID抽出
  5. **操作５**: 画像リンク設定 & Atomフィード生成（`pythonproccess_step5`リスト）
  6. **操作６**: Bloggerへアップロード（`pythonproccess_upload`）
- **起動時警告（仕様変更D）**: `token.pickle` がない場合は警告を出す（ただし操作は続行可能）
- **フォルダクリア警告（仕様変更D）**: ユーザーが「フォルダを開く」ボタンを押時に、`reports/`、`work/`、`image/`、`ready_load/` に ファイルがあれば確認ダイアログを表示。OK で全削除（`*.xml`、`finished/` は除外）

### 設定管理 (config.py)
- `config.ini`経由でセクションベースの組織化で一元管理（コメント`#`削除、引用符除去を自動処理）
- `get_config(section, key, default=None)`関数で安全な設定取得を処理
- `DEFAULTS`辞書にすべてのセクションにデフォルト値を提供
- すべてのパスは相対パス（例：`./reports`、`./work`）をスクリプト位置相対で使用

## 外部依存関係
- **Google APIs**: `google-auth-oauthlib`、`google-auth-httplib2`、`google-api-python-client` - Blogger API v3認証・投稿用
- **HTML/XML処理**: `BeautifulSoup4` (`html.parser`エンジン) - HTMLパース、`xml.etree.ElementTree` - XML設定読み込み
- **画像処理**: `Pillow (PIL)` - ウォーターマーク追加、`piexif` - EXIF削除
- **位置情報**: `geopy` (Nominatim) - 地名→緯度経度変換（OpenStreetMap、レート制限1.1秒/リクエスト）
- **形態素解析**: `janome` - 日本語地名抽出用
- **GUI**: `tkinter` (標準ライブラリ) - デスクトップアプリインターフェース

## 一般的な陥穽と警告パターン（仕様変更D）

### 重大エラー - 警告して中断
1. **HTML クリーニング時にコンテンツ削除**: 過度に積極的な正規表現置換；サンプルHTMLで最初にテストして検証してから本実行すること
2. **画像URL がマッピングされない**: MediaManager HTMLフォーマット変更の可能性；ファイル名がリンクできなかった場合は「この画像ファイルが紐付けできませんでした」と一覧表示
   - ユーザーに「操作５から やり直すか」「アップロード後に手動修正するか」を選択させる
3. **MediaManager HTML が複数存在**: `BloggerMediaManager_XXXX.html` が2つ以上ある場合は エラーとして次に進めない
4. **アップロード がサイレント失敗**: BLOG_IDが設定されていない、認証情報が無効、またはレート制限ヒット；実行前にこれらを確認し、エラー時は明示的なエラーメッセージを出力して中断
5. **Nominatimレート制限違反**: 大量の地名処理時、1.1秒間隔を厳守（`time.sleep(1.1)`）。違反するとOpenStreetMapからブロックされる可能性あり

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

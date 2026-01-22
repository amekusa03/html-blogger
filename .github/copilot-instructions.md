# Blogger HTMLアップロードパイプライン - AI開発ガイド

## アーキテクチャ概要
**ローカルデスクトップツール**で、HTMLレポートをBloggerと互換性のあるポストに変換し、自動画像処理を行う。Tkinter GUI (`html_tobrogger.py`)から起動される4つの連続ステージから構成される：

```
reports/          → addKeyword_upload/  → ready_to_upload/    → ready_to_upload_images/  → Blogger
  (index.htm        (キーワード注入)      (クリーニング済み)     (リネーム済み画像)         (Google API)
   + 写真)
```

### 処理ステージ
1. **add_keywords.py**: `keywords.xml`を読み込み、HTMLに`<meta name="keywords">`を注入・マージ、オリジナルをバックアップ
2. **cleaner.py**: HTMLからタイトル・日付・キーワードを抽出、すべてのフォーマットを削除、`ready_to_upload/`に出力
3. **image_preparer.py**: `ready_to_upload/`から画像をコピー・リネーム（`{folder_name}{filename}`パターン使用）
4. **uploader.py**: *(GUIに未統合)* Google Blogger API v3を使用してポストを公開

## データフロー＆フォルダ構造

### 入力/出力フォルダ
- **`reports/`**: ソースHTMLファイル `reports/{LOCATION_CODE}/index.htm`（またはその他ファイル名）と埋め込み画像
- **`addKeyword_upload/`**: `add_keywords.py`の出力 - キーワード注入済み + `.backup_*`ファイル付きの同じ構造
- **`ready_to_upload/`**: `cleaner.py`の出力 - クリーニング済みHTMLファイル、メタデータはファイル名/フォルダに抽出
- **`ready_to_upload_images/`**: `image_preparer.py`の出力 - Bloggerアップロード準備完了のリネーム済み画像

### フォルダ命名規則
ロケーションコードはディレクトリ名（例：`0205tai`、`0209nori`、`1404tokyo`）。これらが画像名プレフィックスになる：
- ソース: `reports/0205tai/photo01.jpg` → リネーム後: `ready_to_upload_images/0205taiphoto01.jpg`

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
- **バックアップ作成**: 変更前に必ず`{filename}.backup_YYYYMMDD_HHMMSS`を作成。バックアップ失敗時は警告で継続
- **重複キーワード**: 既存HTMLキーワード + Mast + Hitをマージ、重複を削除、追加順を維持
- **注入ポイント**: `</head>`タグの直前に挿入。見つからない場合は`</body>`の直前。どちらも見つからない場合は`</html>`を閉じる前に追加

### cleaner.py の詳細
- **出力ファイル名フォーマット**: タイトル・日付・キーワードを抽出、`ready_to_upload/{FOLDER_NAME}/{title_or_default}.html`に出力
- **メタデータ保存**: HTMLクリーニング前にタイトル・日付・キーワードを抽出（クリーニングですべてのタグが削除されるため）
- **コンテンツ抽出**: すべてのHTMLタグを削除：`re.sub(r'</?(B|font|span|strong).*?>', '', text, flags=re.IGNORECASE)`
- **エラーハンドリング**: タイトル・日付が見つからない場合、警告を出力するが継続（失敗しない）。ファイル名にはセンスのあるデフォルト値を使用

### image_preparer.py の詳細
- **画像発見**: `src_file.rglob('*')`を使用してサブディレクトリ内のすべての画像を再帰的に検索
- **サポート形式**: `.jpg`、`.jpeg`、`.png`、`.gif`（大文字小文字区別なし）
- **リネームパターン**: `{folder_name}{original_filename}`（例：`0205tai` + `photo01.jpg` = `0205taiphoto01.jpg`）
- **コピー操作**: メタデータを保存するため`shutil.copy2()`を使用。出力フォルダは`mkdir(parents=True, exist_ok=True)`で作成
- **エラーハンドリング**: ファイルごとにtry/except、エラー出力後も他のファイル処理を継続

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
- **`config.ini`**: `get_config(section, key)`経由の使用パターンについては`config.py`を参照
  - セクション：`[ADD_KEYWORDS]`、`[CLEANER]`、`[OPEN_BLOGGER]`、`[IMAGE_PREPARER]`、`[CONVERT_ATOM]`、`[UPLOADER]`
- **`credentials.json`**: Google Cloud ConsoleからのOAuth認証情報（Desktop App型、プロジェクトルートに配置）
- **`token.pickle`**: 最初のOAuthフロー後に自動生成、認証セッションを永続化

## 一般的なワークフロー

### フルパイプライン実行
```bash
# GUI から実行（メインエントリーポイント）
python html_tobrogger.py
# ボタンはスクリプトを順次起動、テキストウィジェットで出力を監視

# または個別実行（デバッグ用）
python add_keywords.py      # キーワード注入
python cleaner.py           # HTMLクリーニング・メタデータ抽出
python image_preparer.py    # 画像リネーム・統合
python uploader.py          # Blogger API へのアップロード
```

### 単一ステージのテスト
- 中間フォルダを使用：`addKeyword_upload/`（add_keywords後）、`ready_to_upload/`（cleaner後）
- 問題を分離するため、次のステージ実行前に出力を確認

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
- シングルスレッドTkinterで`subprocess.Popen()`経由で子プロセスを順次起動
- `process.stdout.read()`で非ブロッキングループ内（10ms ポーリング `root.after(10, update_timer)`）に出力をキャプチャ
- プロセス間通信なし；フォルダ状態（入出力フォルダ）でのデータフローに依存
- 各ボタンは`pythonproccess`リスト内の1つのスクリプトに対応

### 設定管理 (config.py)
- `config.ini`経由でセクションベースの組織化で一元管理
- `get_config(section, key, default=None)`関数で安全な設定取得を処理
- `DEFAULTS`辞書にすべてのセクションにデフォルト値を提供
- すべてのパスは相対パス（例：`./reports`、`./addKeyword_upload`）をスクリプト位置相対で使用

## 一般的な陥穽（重大エラー - 警告して中断）
1. **HTML クリーニング時にコンテンツ削除**: 過度に積極的な正規表現置換；サンプルHTMLで最初にテストして検証してから本実行すること
2. **画像URL がマッピングされない**: MediaManager HTMLフォーマット変更の可能性；BeautifulSoup の`prettify()`で検査し、URLマッピングが0件の場合は警告して中断
3. **アップロード がサイレント失敗**: BLOG_IDが設定されていない、認証情報が無効、またはレート制限ヒット；実行前にこれらを確認し、エラー時は明示的なエラーメッセージを出力して中断

### 注意: 警告が出ても継続する場合
- **キーワード注入されない**: XMLが不正形式でもアップロード可能（警告は出力される）
- **日付抽出失敗**: 日付が抽出できなくてもアップロード可能（警告は出力される）
これらは重大ではなく、処理は続行します。

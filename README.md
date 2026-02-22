# HTML to Blogger Ver0.98

ローカルにあるHTMLファイルと画像を、自動的に処理してBloggerに投稿するためのデスクトップアプリケーションです。
HTMLのクリーニング、画像への透かし追加、キーワードや位置情報の付与、そしてBloggerへのアップロードを実行します。

## 主な機能

*   **HTMLクリーニング**: 投稿に不要なタグの削除、フォーマットの正規化。
*   **画像処理**: 画像のEXIF削除、透かし（ウォーターマーク）の追加。
*   **メタデータ付与**: 本文解析によるキーワード(`search`タグ)や位置情報(`georss`タグ)の自動追加。
*   **Bloggerアップロード**: 画像リンクと記事をBlogger APIを使用して下書きとして投稿。
*   **GUI操作**: 進行状況の可視化、エラー時のリカバリー機能などを備えた使いやすいGUI。

## 処理の流れ

以下の順番で処理が実行されます:

1.  **`import_file.py`**: 原稿フォルダから作業フォルダへファイルを取り込みます。
2.  **`serial_file.py`**: ファイル名を連番形式に変換します。
3.  **`clean_html.py`**: HTMLをBlogger用にクリーンアップします。
4.  **`find_keyword.py`**: 記事本文からキーワードを抽出します。
5.  **`find_location.py`**: 記事内の地名を抽出し、位置情報を付与します。
6.  **`find_date.py`**: 記事内の日付を解析します。
7.  **`mod_image.py`**: 画像の加工（リサイズ、透かし追加）を行います。
8.  **`upload_image.py`**: 画像をアップロード用に準備します。
9.  **`import_media_manager.py`**: メディアマネージャー用フォルダをクリーンアップします。
10. **`link_html.py`**: HTML内の画像リンクを更新します。
11. **`upload_art.py`**: 完成した記事をBloggerにアップロードします。

## ファイル構成

### メインファイル
*   **`html_tobrogger.py`**: メインGUIアプリケーション
*   **`main_process.py`**: 処理フローの制御

### 処理モジュール
*   **`import_file.py`**: ファイル取り込み検証
*   **`serial_file.py`**: ファイル名の連番化
*   **`clean_html.py`**: HTMLクリーニング
*   **`find_keyword.py`**: キーワード抽出
*   **`find_location.py`**: 位置情報付与
*   **`find_date.py`**: 日付抽出
*   **`mod_image.py`**: 画像加工
*   **`upload_image.py`**: 画像準備
*   **`import_media_manager.py`**: メディアマネージャークリーンアップ
*   **`link_html.py`**: HTMLリンク更新
*   **`upload_art.py`**: 記事アップロード

### ユーティリティ
*   **`file_class.py`**: ファイル管理クラス
*   **`parameter.py`**: 共通定数・設定読み込み
*   **`auth_google.py`**: Google認証処理
*   **`cons_progressber.py`**: コンソール進捗バー表示

### 設定ファイル（`data/` フォルダ内）
*   **`config.json5`**: アプリケーション全体の設定
*   **`log_config.json5`**: ログ出力の設定
*   **`serial.json5`**: シリアル番号カウンター（自動管理）
*   **`keywords.xml`**: メタキーワード定義
*   **`location.xml`**: 位置情報キャッシュ（自動更新）
*   **`credentials.json`**: Google認証情報（要ユーザー配置、GitHubに含めない）
*   **`token.pickle`**: 認証トークン（自動生成）

### その他
*   **`requirements.txt`**: 必要なPythonパッケージ一覧
*   **`pyproject.toml`**: プロジェクト設定

## 動作環境

*   Python 3.8 以上
*   Google Cloud Platform (GCP) プロジェクトとBlogger APIの有効化

## インストール方法

### 1. ソースコードの配置
このツール一式を任意のフォルダに配置してください。

### 2. 依存ライブラリのインストール
以下のコマンドを実行して、必要なPythonライブラリをインストールします。
`requirements.txt` が含まれているため、一括インストールが可能です。

```bash
pip install -r requirements.txt
# または pip install beautifulsoup4 google-api-python-client google-auth-oauthlib google-auth-httplib2 Pillow geopy janome
```

※ Linux (Ubuntu等) をご使用の場合、Tkinterのインストールが必要な場合があります。
```bash
sudo apt-get install python3-tk
```

## 初期設定

### 1. Google API 認証情報の準備
1.  Google Cloud Console にアクセスし、プロジェクトを作成します。
2.  「APIとサービス」>「ライブラリ」から **Blogger API v3** を検索し、有効にします。
3.  「APIとサービス」>「認証情報」から **OAuth 2.0 クライアントID** を作成します（アプリケーションの種類は「デスクトップアプリ」）。
4.  作成した認証情報のJSONファイルをダウンロードし、**`credentials.json`** という名前でこのツールのdataフォルダに保存します。

### 2. アプリケーションの起動
以下のコマンドでGUIアプリを起動します。

```bash
python3 html_tobrogger.py
```

### 3. ブログIDの設定
ブログIDをconfig.json5設定保存して下さい。
※ 初回実行時のみ、ブラウザが開きGoogleアカウントへのログインと権限の許可（OAuth認証）が求められます。

## 使い方

### 基本的な流れ

1.  **原稿の準備**:
    *   `reports` フォルダに、投稿したいHTMLファイルと画像ファイルを配置します。
    *   GUIの「フォルダ」エリアにある「📄 原稿 (Reports)」ボタンでフォルダを開けます。

2.  **処理の実行**:
    *   GUI右下の **実行** ボタンをクリックします。
    *   クリーニング → 画像処理 → キーワード追加 → アップロードが順次実行されます。

3.  **画像アップロード**:
    *   案内ダイアログが表示され、加工済み画像フォルダが開きます。
    *   Bloggerdeで新しい記事を選び、フォルダ内の画像を貼り付けてください。
    *   新しい記事は**下書き**として保存して下さい。
    *   完了したらツールの「 実行」を押します。

3.  **メディアマネージャーの解析**:
    *   案内ダイアログが表示され、HTML保存用フォルダが開きます。
    *   Bloggerの投稿画面を「メディアマネージャー」に切り替え、HTML形式でmedia_manフォルダに置きます。
    *   コピーしたコードをテキストファイル（例: `blogger.html`）として保存用フォルダに保存します。
    *   完了したらツールの「 実行」を押します。
    *   ツールが画像URLを解析し、記事のリンクをBloggerのURLに置換して処理を続行します。

4.    **記事アップロード**
    *   記事が自動投稿をします。
    *   自動投稿がu完了するとBloggerの下書きになっていますので、確認し**公開**して下さい

## トラブルシューティング

*   **エラーが発生した場合**:
    *   ログウィンドウに赤字でエラー内容が表示されます。
    *   ファイル自体の問題（文字コード不明など）の場合は、ファイルを修正してから再実行してください。

*   **設定を変更したい**:
    *   メニューバーの「設定編集」から `config.json5` や `keywords.xml` を直接編集できます。

## ライセンス / クレジット

*   © OpenStreetMap contributors
*   その他、使用しているライブラリのライセンスに従います。

## 📚 ドキュメント

- **[クイックスタート](docs/QUICKSTART.md)** - 5分でセットアップ
- **[セットアップガイド](docs/SETUP.md)** - Google Cloud & Blogger API設定
- **[アーキテクチャ](docs/ARCHITECTURE.md)** - プロジェクト構造の詳細
- **[トラブルシューティング](docs/TROUBLESHOOTING.md)** - よくある問題と解決方法

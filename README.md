# HTML to Blogger Ver 0.98

HTML to Blogger is a desktop application designed to automate the processing and uploading of local HTML files and images to Blogger. It handles HTML sanitization, image watermarking, metadata generation (keywords and geolocation), and seamless publishing via the Blogger API.

## Resources

*   **Detailed Guide:** [Read the full article on Qiita (Japanese)](https://qiita.com/amekusa03/items/b8ac77cd3dd6e6cc65aa)
*   **Demo Video:**

    [![Watch the Demo](https://img.youtube.com/vi/gFgYCVHIfW0/maxresdefault.jpg)](https://youtu.be/gFgYCVHIfW0?si=fby7oARRbfOy2K4K)

## Key Features

*   **HTML Sanitization**: Automatically removes unnecessary tags and normalizes formatting for Blogger compatibility.
*   **Image Optimization**: Strips EXIF metadata and adds customizable watermarks.
*   **Automated Metadata**: Extracts keywords (`search` tags) and geolocation (`georss` tags) by analyzing post content.
*   **Blogger Integration**: Uploads articles as drafts with updated image links using the Blogger API.
*   **User-Friendly GUI**: Intuitive interface with progress tracking and error recovery tools.

## Processing Workflow

The application executes tasks in the following order:

1.  **`import_file.py`**: Transfers files from the "Reports" (source) folder to the workspace.
2.  **`serial_file.py`**: Renames files using a sequential numbering format.
3.  **`clean_html.py`**: Sanitizes HTML for Blogger-specific requirements.
4.  **`find_keyword.py`**: Extracts keywords from the article body.
5.  **`find_location.py`**: Identifies place names and attaches geolocation data.
6.  **`find_date.py`**: Parses dates within the article.
7.  **`mod_image.py`**: Processes images (resizing and watermarking).
8.  **`upload_image.py`**: Prepares images for upload.
9.  **`import_media_manager.py`**: Cleans up the Media Manager workspace.
10. **`link_html.py`**: Updates image URLs within the HTML to point to Blogger.
11. **`upload_art.py`**: Uploads the finalized article to Blogger.

## Project Structure

### Core Components
*   **`html_tobrogger.py`**: Main GUI application entry point.
*   **`main_process.py`**: Logic for controlling the processing flow.

### Processing Modules
*   **`import_file.py`**: File import and validation.
*   **`serial_file.py`**: File serialization.
*   **`clean_html.py`**: HTML sanitization.
*   **`find_keyword.py`**: Keyword extraction.
*   **`find_location.py`**: Geolocation tagging.
*   **`find_date.py`**: Date analysis.
*   **`mod_image.py`**: Image processing.
*   **`upload_image.py`**: Image upload preparation.
*   **`import_media_manager.py`**: Media manager cleanup.
*   **`link_html.py`**: HTML link updates.
*   **`upload_art.py`**: Article publishing.

### Utilities
*   **`file_class.py`**: File management helper.
*   **`parameter.py`**: Shared constants and configuration loader.
*   **`auth_google.py`**: Google OAuth 2.0 authentication.
*   **`cons_progressber.py`**: Console-based progress indicators.

### Configuration (Stored in `data/`)
*   **`config.json5`**: Global application settings.
*   **`log_config.json5`**: Logging configuration.
*   **`serial.json5`**: Serial number counter (managed automatically).
*   **`keywords.xml`**: Meta-keyword definitions.
*   **`location.xml`**: Geolocation cache (updated automatically).
*   **`credentials.json`**: Google API credentials (User-provided).
*   **`token.pickle`**: Authentication token (Auto-generated).

### Others
*   **`requirements.txt`**: List of Python dependencies.
*   **`pyproject.toml`**: Project configuration.

## Requirements

*   Python 3.8 or higher.
*   A Google Cloud Platform (GCP) project with the **Blogger API v3** enabled.

## Installation

### 1. Clone/Download
Place the project files in your desired directory.

### 2. Install Dependencies
Install the required libraries using pip:

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

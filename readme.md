# HTMLtoBlogger

HTML4.0で作成された大量のWebページをGoogle Bloggerに移行・投稿するためのデスクトップツールです。

**English**: [README.en.md](README.en.md) (coming soon)

## 概要

このアプリケーションは、以下の処理を自動化します：

1. **キーワード自動抽出** - keywords.xmlからメタキーワードを挿入
2. **位置情報タグ自動付加** - OpenStreetMap (Nominatim) から緯度経度を取得
3. **HTMLクリーニング** - 古いHTML形式を削除、Blogger互換にフォーマット
4. **画像処理** - EXIF削除、ウォーターマーク追加
5. **自動アップロード** - Google Blogger API v3で記事を自動投稿

## 主な機能

- 📁 複数フォルダの一括処理
- 🗺️ OpenStreetMapを使用した自動地理情報タグ付け
- 🔒 プライバシー保護（EXIF削除）
- 💾 キャッシング機能（重複クエリ防止）
- 🖥️ クロスプラットフォーム対応（Windows/Mac/Linux）
- ⚡ GUI アプリケーション（Tkinter）

## インストール

### 必要な環境

- Python 3.8以上
- Google Cloud アカウント（Blogger API用）
- インターネット接続

### セットアップ手順

1. **リポジトリをクローン**
   ```bash
   git clone https://github.com/yourusername/htmltobrogger.git
   cd htmltobrogger
   ```

2. **仮想環境を作成・有効化**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # または
   venv\Scripts\activate  # Windows
   ```

3. **依存パッケージをインストール**
   ```bash
   pip install -r requirements.txt
   ```

4. **Google Cloud認証設定**
   詳細は [SETUP.md](docs/SETUP.md) を参照してください。

## 使い方

### 基本的な流れ

```bash
python html_tobrogger.py
```

GUI ウィンドウが起動します。6つの操作ボタンで処理を進めます：

1. **フォルダを開く** - reports/フォルダにHTMLファイルを配置
2. **開始** - 自動処理（キーワード、位置情報、クリーニング、画像処理）
3. **メディアマネージャーを開く** - Bloggerでメディアをアップロード
4. **画像フォルダを開く** - リネーム済み画像をBloggerに貼り付け
5. **画像リンク設定&Atomフィード生成** - URLをマッピング、Atom形式で生成
6. **アップロード** - Google Blogger APIで自動投稿

### フォルダ構成

```
reports/              # ユーザーの入力フォルダ
├── 0205tai/
│   ├── index.html
│   └── photo01.jpg
├── 0209nori/
│   └── ...

work/                 # 処理中の一時フォルダ
image/                # Blogger用にリネーム済みの画像
ready_load/           # アップロード待機フォルダ
finished/             # アップロード完了済みファイル
```

### 設定ファイル

- **config.ini** - フォルダパス、処理設定
- **keywords.xml** - メタキーワード定義
- **georss_point.xml** - 位置情報キャッシュ（自動生成・更新）
- **credentials.json** - Google Cloud 認証情報（自分で取得）

## 対応HTML要素

以下の要素を処理・保持します：

- タグ: `<head>`, `<title>`, `<h1>-<h9>`, `<body>`, `<table>`, `<tr>`, `<td>`
- メディア: `<img>`, `<figure>` (style対応)
- メタ情報: `<meta name="keywords">`, `<time datetime>`, `<georss:point>`

## 注意点⚠️

### セキュリティ
- `credentials.json` は絶対に公開しないでください
- `token.pickle` には認証情報が含まれます
- `.gitignore` で上記ファイルを除外しています

### OpenStreetMap（Nominatim）の利用規約
- リクエスト間隔: **最低1.1秒**（本ツールは自動的に遵守）
- 大量連続利用は禁止
- キャッシングを必ず利用
- **クレジット表示が必須**

### Google Blogger API
- API呼び出しには制限があります
- 高速で大量のアップロードを行うとアカウントロックの可能性
- 1回のアップロードは最大5件（デフォルト設定）

## トラブルシューティング

### Q: 「ModuleNotFoundError」が出る
A: `pip install -r requirements.txt` で必要なパッケージをインストール

### Q: 位置情報が見つからない
A: `georss_point.xml` を確認、またはOpenStreetMapで手動検索

### Q: 画像がアップロードされない
A: メディアマネージャーのHTMLファイルが正しく配置されているか確認

詳細は [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) を参照

## ライセンス

MIT License - 詳細は [LICENSE](LICENSE) を参照

## 謝辞

このプロジェクトで使用している主要なライブラリ：

- **BeautifulSoup4** - HTMLパース
- **geopy (Nominatim)** - 地理情報取得
- **Janome** - 日本語形態素解析
- **Google API Client** - Blogger API連携
- **Pillow** - 画像処理
- **piexif** - EXIF削除

### 地理データ

© [OpenStreetMap contributors](https://www.openstreetmap.org/copyright/ja)

このソフトウェアはOpenStreetMapの地理データを使用しています。OpenStreetMapのライセンスに従い、利用時にはクレジット表示が必須です。

## 開発支援

Gemini (Google AI) の支援を受けて開発されました。

## サポート

問題が発生した場合：

1. [ドキュメント](docs/) を確認
2. [Issues](https://github.com/yourusername/htmltobrogger/issues) で類似の問題を検索
3. 新しいIssueを作成（ログ情報を含める）

## ロードマップ

- [ ] 複数Bloggerサイト対応
- [ ] ドラッグ&ドロップでファイル追加
- [ ] 処理結果のエクスポート（CSV）
- [ ] 自動バックアップ機能
- [ ] Web UI版の開発

---

**最終更新**: 2026年1月25日

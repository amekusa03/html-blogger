# クイックスタート

5分で HTMLtoBlogger をセットアップして使い始めるためのガイド。

## ⚡ 最速セットアップ（5分）

### ステップ 1: リポジトリをクローン
```bash
git clone https://github.com/yourusername/htmltobrogger.git
cd htmltobrogger
```

### ステップ 2: 仮想環境を作成
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate  # Windows
```

### ステップ 3: 依存パッケージをインストール
```bash
pip install -r requirements.txt
```

### ステップ 4: Google Cloud 認証ファイルを配置
[SETUP.md](docs/SETUP.md) のステップ 4 に従って、`credentials.json` をプロジェクトフォルダにコピー。

### ステップ 5: アプリケーションを起動
```bash
python html_tobrogger.py
```

🎉 **完了！** GUI ウィンドウが起動します。

---

## 📋 基本的な使い方

### 1. HTML ファイルを準備
```
reports/
├── 0205tai/
│   ├── index.html  ← ここにHTMLファイルを配置
│   ├── photo01.jpg
│   └── photo02.jpg
```

### 2. GUI でボタンを順番にクリック

```
[フォルダを開く]
    ↓ reports フォルダを表示
    
[開始]
    ↓ キーワード・位置情報・クリーニング・画像処理を自動実行
    ↓ ログウィンドウで進行状況を確認
    
[メディアマネージャーを開く]
    ↓ Blogger の メディアマネージャーでアップロード
    
[画像フォルダを開く]
    ↓ リネーム済み画像を確認（念のため）
    
[画像リンク設定 & Atom フィード生成]
    ↓ URL マッピングと Atom フィード生成
    
[アップロード]
    ↓ Google Blogger API で自動投稿開始
```

### 3. 完了確認

```
finished/
├── feed.atom
├── 0205tai_index.html
└── ...
```

ファイルが `finished/` に移動すれば完了です。

---

## ⚙️ 必須設定

### 1. `config.ini` を編集
```ini
[OPEN_BLOGGER]
BLOG_ID = 1234567890123456789  # あなたのブログID

[CONVERT_ATOM]
BLOG_TITLE = My Blog            # ブログ名
BLOG_URL = https://myblog.blogspot.com  # ブログURL
```

### 2. `keywords.xml` を編集
```xml
<Mastkeywords>
    <word>キーワード1</word>
    <word>キーワード2</word>
</Mastkeywords>
```

---

## 🆘 うまくいかない場合

### ❌ モジュールエラーが出る場合
```bash
pip install -r requirements.txt
```

### ❌ 認証エラーが出る場合
1. [SETUP.md](docs/SETUP.md) を再読
2. `credentials.json` が正しく配置されているか確認
3. Google Cloud で Blogger API v3 が有効化されているか確認

### ❌ その他の問題
[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) を参照

---

## 📚 詳細ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [README.md](../README.md) | プロジェクト概要・機能一覧 |
| [SETUP.md](SETUP.md) | Google Cloud API 詳細設定 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | システム設計・ファイル構成 |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | 問題解決ガイド |

---

## 💡 よくある質問

**Q: 複数のブログに投稿できますか？**
A: `BLOG_ID` を変更して、複数回実行してください。

**Q: 大量の HTML ファイル（100+）を処理できますか？**
A: はい。ただしBlogger API には割り当て制限があるため、複数日に分けることをお勧めします。

**Q: 画像を手動で配置する必要はありますか？**
A: メディアマネージャーで Blogger にアップロードした後、ツールが自動でマッピングします。

**Q: バックアップは作成されますか？**
A: はい。各 HTML ファイルの修正前に `*.backup_` ファイルが自動作成されます。

---

## 🚀 次のステップ

1. [サンプル HTML](../reports/0205tai/tai.html) で試す
2. [設定ファイル](../config.ini) をカスタマイズ
3. [キーワード定義](../keywords.xml) を追加
4. 大量投稿の場合は [ARCHITECTURE.md](ARCHITECTURE.md) でパフォーマンス最適化を確認

---

**最終更新**: 2026年1月25日

**問題が発生した場合は、[TROUBLESHOOTING.md](TROUBLESHOOTING.md) を参照してください。**

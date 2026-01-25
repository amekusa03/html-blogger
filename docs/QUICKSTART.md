# クイックスタート

5分で HTMLtoBlogger をセットアップして使い始めるためのガイド。

## ⚡ 最速セットアップ（5分）

### ステップ 1: リポジトリをクローン
```bash
git clone https://github.com/amekusa03/html-blogger.git
cd html-blogger
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

🖥️ **GUI ウィンドウが起動します。** 

⚠️ **起動確認チェックリスト**:
- [ ] GUI ウィンドウが表示される
- [ ] 「フォルダを開く」ボタンが反応する
- [ ] `reports/` フォルダが開く

---

## 🧪 初回動作確認（重要！）

**本格利用する前に、必ず小さなテスト HTML ファイルで動作確認してください：**

1. **テストファイルを用意**
   ```
   reports/test/
   ├── test.html (100KB以下の小さいHTML)
   └── test_image.jpg (小さい画像 1-2枚)
   ```

2. **各ボタンを順番にクリック**してみる
   - エラーが出ないか確認
   - ログメッセージを確認

3. **すべてが正常に完了したら、本格利用を開始**
   - テストで問題が出た場合は [TROUBLESHOOTING.md](TROUBLESHOOTING.md) を参照
   - 解決しない場合は [GitHub Issues](https://github.com/amekusa03/html-blogger/issues) で報告

⚠️ **警告**: 動作確認なしに大量ファイルを処理するのは避けてください。予期しない動作が発生する可能性があります。

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

## 💡 動作確認時によくあること

**Q: GUI は起動するが、ボタンが反応しない**
A: Python の version 確認、 venv が有効化されているか確認してください。[TROUBLESHOOTING.md](TROUBLESHOOTING.md) を参照。

**Q: エラーメッセージが出る**
A: エラーメッセージをコピーして [TROUBLESHOOTING.md](TROUBLESHOOTING.md) で検索。見つからない場合は [GitHub Issues](https://github.com/amekusa03/html-blogger/issues) で報告。

**Q: 処理は完了したが、ファイルが生成されていない**
A: work/ フォルダの内容を確認。config.ini の設定を再度確認。

---

## 🚀 次のステップ

1. ✅ テスト HTML で動作確認
2. ✅ すべてが問題なく動作することを確認
3. ✅ [設定ファイル](../config.ini) をカスタマイズ
4. ✅ [キーワード定義](../keywords.xml) を追加
5. ✅ 本格利用開始

---

**最終更新**: 2026年1月25日

**動作確認の結果を教えてもらえると、今後の改善に役立ちます！**

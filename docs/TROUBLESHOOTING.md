# トラブルシューティングガイド

⚠️ **本ドキュメントは開発版のトラブルシューティングです** - まだ動作確認が完全には完了していません。

このドキュメントで解決しない問題については、以下をお試しください：
1. [GitHub Issues](https://github.com/amekusa03/html-blogger/issues) で既知の問題を検索
2. 新しい Issue を作成して、開発チームに報告

HTMLtoBloggerで発生しやすい問題と解決策をまとめています。

## よくある問題

### 1. インストール・セットアップ関連

#### Q: `ModuleNotFoundError: No module named 'xxx'` エラーが出る

**原因**: 必要なPythonパッケージがインストールされていません

**解決策**:
```bash
# 仮想環境を有効化
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate  # Windows

# パッケージをインストール
pip install -r requirements.txt

# バージョン確認（オプション）
pip list
```

---

#### Q: `command not found: python3` または `python: command not found`

**原因**: Pythonがインストールされていないか、PATHに設定されていません

**解決策**:

**Linux/Mac:**
```bash
# Pythonのインストール確認
python3 --version

# インストールされていない場合
brew install python3  # Mac
# または
apt-get install python3 python3-venv  # Ubuntu/Debian
```

**Windows:**
1. [python.org](https://www.python.org/downloads/) からダウンロード
2. インストール時に「Add Python to PATH」をチェック
3. インストール完了後、コマンドプロンプトを再起動

---

#### Q: 仮想環境が有効化されない

**原因**: 仮想環境が正しく作成されていません

**解決策**:
```bash
# 既存の仮想環境を削除
rm -rf venv

# 新しい仮想環境を作成
python3 -m venv venv

# 有効化
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate  # Windows

# 確認（プロンプトに (venv) が表示されるはず）
```

---

### 2. Google認証関連

#### Q: `FileNotFoundError: credentials.json not found`

**原因**: `credentials.json`がプロジェクトフォルダに配置されていません

**解決策**:
1. [Google Cloud Console](https://console.cloud.google.com) にアクセス
2. 「APIとサービス」→「認証情報」で OAuth クライアント ID をダウンロード
3. ダウンロードしたファイルを `credentials.json` に名前変更
4. `data/` フォルダに配置

📝 **詳細**: [SETUP.md](SETUP.md) ステップ4を参照

---

#### Q: `403 Permission Denied` エラー

**原因**: 以下のいずれか：
- Blogger API が有効化されていない
- OAuth同意画面が正しく設定されていない
- テストユーザーが追加されていない

**解決策**:

1. Google Cloud Console で Blogger API v3 が有効化されているか確認
   ```
   APIとサービス → ライブラリ → "Blogger API" で検索
   ```

2. OAuth同意画面を確認
   ```
   APIとサービス → OAuth同意画面 → 編集
   ```

3. テストユーザーに自分のメールアドレスが追加されているか確認
   ```
   APIとサービス → OAuth同意画面 → テストユーザー
   ```

📝 **詳細**: [SETUP.md](SETUP.md) ステップ2-4を参照

---

#### Q: `token.pickle` が生成されない

**原因**: 初回認証フローが完了していません

**解決策**:
1. `python html_tobrogger.py` でGUIを起動
2. 「次へ」ボタンを押して処理を進め、アップロード段階まで進む
3. ブラウザで Google 認証を完了
4. `token.pickle`が自動生成されるのを待つ

⚠️ **注意**: インターネット接続が必要です

---

#### Q: `token.pickle` をリセットしたい

**解決策**:
```bash
# トークンを削除
rm data/token.pickle

# 次回起動時に再認証が促されます
```

---

### 3. HTMLファイル処理関連

#### Q: HTMLファイルが処理されない

**原因**: 以下のいずれか：
- `reports/` フォルダに HTML ファイルがない
- ファイルが .html 拡張子ではない

**解決策**:

1. ファイルを確認
```
report/
├── 0205tai/          
│   └── index.html    
├── 0209nori/
│   └── index.html
```

2. リンクについて
#　画像のリンクはreport内で収まるようにして下さい

---

#### Q: キーワードが追加されない

**原因**: `keywords.xml` が見つからないか、形式が正しくない

**解決策**:

1. `data/keywords.xml`を確認
```xml
<?xml version="1.0" encoding="UTF-8"?>
<keywords>
    <Mastkeywords>
        <word>キーワード1</word>
        <word>キーワード2</word>
    </Mastkeywords>
    <Hitkeywords>
        <word>キーワード3</word>
    </Hitkeywords>
</keywords>
```

2. `data/location.xml`の形式を確認
```xml
<?xml version='1.0' encoding='utf-8'?>
<root>
    <location>
        <name>タイ</name>
        <latitude>15.8700</latitude>
        <longitude>100.9925</longitude>
    </location>
</root>
```

3. ファイルの文字エンコーディングが UTF-8 か確認

---

#### Q: 位置情報（地理タグ）が付与されない

**原因**: 以下のいずれか：
- HTMLのタイトルや見出しに地域名が含まれていない
- `locate.xml`の形式が正しくない
- OpenStreetMap (Nominatim) が地域名を認識できない

**解決策**:

1. HTMLのタイトルを確認
```html
<title>タイの観光地</title>  <!-- "タイ" が認識される -->
```

2. `data/location.xml`の形式を確認
```xml
<?xml version='1.0' encoding='utf-8'?>
<root>
    <location>
        <name>タイ</name>
        <latitude>15.8700</latitude>
        <longitude>100.9925</longitude>
    </location>
</root>
```

3. 地域名を手動で追加
- テキストエディタで `data/location.xml` を開く
- 必要な位置情報を追加

4. OpenStreetMap で検証
- https://www.openstreetmap.org/search で地域名を検索
- 座標を確認して `data/location.xml` に追加

---

#### Q: `<georss:point>` タグが削除されている

**原因**: HTML クリーニング時にタグが削除されました

**解決策**:
1. タイトルに地域名を含める（自動再取得）
2. 手動で `data/location.xml` に位置情報を追加
3. 処理を再実行

---

### 4. 画像処理関連

#### Q: 画像がアップロードされない

**原因**: 以下のいずれか：
- `image/` フォルダに画像ファイルがない
- ファイル名のマッピングが間違っている
- Blogger メディア マネージャーのHTMLファイルがない

**解決策**:

1. ファイル構造を確認
```bash
image/
├── 0205taiphoto01.jpg
├── 0205taiphoto02.jpg
└── ...
```

2. メディア マネージャー HTML を確認
- Blogger → メディア → ファイルを開く
- HTMLファイルが自動ダウンロードされているか確認

3. リネーム規則を確認
```
元の位置: reports/0205tai/photo01.jpg
リネーム後: image/0205taiphoto01.jpg
          ↑ フォルダ名 + ファイル名
```

---

#### Q: EXIF データが削除されない

**原因**: 対応していない画像形式

**解決策**:

1. 画像形式を確認
- JPEG, PNG, GIF のみ対応
- その他の形式は処理スキップ

---

#### Q: ウォーターマーク が表示されない

**原因**: 以下のいずれか：
- `config.json5` でウォーターマーク機能が無効化されている
- フォントがインストールされていない

**解決策**:

1. `data/config.json5` を確認
```json5
  // 画像加工設定
  mod_image: {
    watermark_text: 'サンプル',  // 透かしテキスト
  },
```

2. フォント を確認（Linux の場合）
```bash
# フォントをインストール
sudo apt-get install fonts-liberation
```

3. ウォーターマークテキストを短くする（可視性向上）

---

### 5. アップロード関連

#### Q: ブログに投稿されない

**原因**: 以下のいずれか：
- BLOG_ID が設定されていない
- 認証情報が無効
- API割り当てに達した

**解決策**:

1. BLOG_ID を確認
```bash
# Blogger → ダッシュボード → URL確認
# https://www.blogger.com/blog/posts/{BLOG_ID}
# BLOG_ID を data/config.json5 に設定
```

2. 認証情報を確認
```bash
rm data/token.pickle
# 次回起動時に再認証
```

3. API割り当てを確認
- Google Cloud Console → APIs and Services → Quotas
- Blogger API の 使用状況 を確認
- 超過している場合は翌日再試行

---

#### Q: `Quota exceeded` エラー

**原因**: Google Blogger API の割り当てに達しました

**解決策**:
- 日本時間17:00以降に再実行（割り当てはリセットされます）
- または Google Cloud Console で割り当てを増加申請

---

#### Q: `Invalid request` エラー

**原因**:  フィード形式が正しくない

**解決策**:
1. `data/upload/` のhtmlファイルを確認
2. ブラウザーで正常に表示できるか確認
3. 必須フィールドが含まれているか確認：
   - `<html>`
   - `<head>`

---

### 6. GUI関連

#### Q: ボタンをクリックしても何も起こらない

**原因**: 処理がバックグラウンドで実行中

**解決策**:
- ターミナルでのプロセス実行完了を待つ
- ステータスウィンドウでログを確認

---

#### Q: ウィンドウがハング（フリーズ）している

**原因**: 重い処理中（HTML解析、Nominatim検索など）

**解決策**:
```bash
# 強制終了（ターミナルで Ctrl+C）
Ctrl+C

# アプリケーション再起動
python html_tobrogger.py
```

---

#### Q: テキストが文字化けしている

**原因**: ターミナルのエンコーディングが UTF-8 ではない

**解決策**:

**Linux/Mac**:
```bash
export LANG=ja_JP.UTF-8
python html_tobrogger.py
```

**Windows (PowerShell)**:
```powershell
$env:PYTHONIOENCODING = "utf-8"
python html_tobrogger.py
```

---

### 7. パフォーマンス関連

#### Q: 処理が遅い

**原因**: 以下のいずれか：
- HTMLファイルが大きい
- 画像数が多い
- インターネット接続が遅い
- Nominatim レート制限（1.1秒/リクエスト）

**解決策**:
- HTMLを小さなチャンクに分割
- 画像解像度を下げる
- インターネット接続を確認
- 処理を分割実行（複数日にかけて）

---

#### Q: メモリ不足 (MemoryError)

**原因**: 非常に大きいHTMLファイルまたは画像

**解決策**:
- ファイルを分割
- 仮想メモリを増加（OS設定）
- 不要なプロセスを終了

---

## 高度なトラブルシューティング

### デバッグログを有効化

各スクリプトに以下を追加：

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# コード内で
logger.debug(f"デバッグ情報: {variable}")
logger.error(f"エラー: {error}")
```

### ターミナル出力をファイルに保存

```bash
python html_tobrogger.py > debug.log 2>&1
```

### XML を検証

```bash
# Linux/Mac
xmllint --noout data/keywords.xml
xmllint --noout data/location.xml
```

---

## さらにサポートが必要な場合

1. [GitHub Issues](https://github.com/amekusa03/html-blogger/issues) で同様の問題を検索
2. エラーメッセージ全文をコピーして新しい Issue を作成
3. 以下の情報を含める：
   - OS とバージョン
   - Python バージョン（`python --version`）
   - エラー再現の手順
   - スクリーンショットまたはログファイル

---

**最終更新**: 2026年2月23日

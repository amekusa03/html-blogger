import os
import re      
import shutil
import logging
from pathlib import Path
from bs4 import BeautifulSoup, Comment
from config import get_config
from utils import ProgressBar

# logging設定
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = logging.FileHandler('cleaner.log', encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING) # プログレスバー表示のため、コンソールは警告以上のみ表示
logger.addHandler(stream_handler)

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = SCRIPT_DIR / get_config('CLEANER', 'output_dir', './work')  # 出力フォルダ

def clean_html_for_blogger(html_text):
    """ブログ用にHTMLをクリーンアップする。
    重大削除チェックは本文テキスト同士の比較で行い、headやscript削除による誤検知を避ける。
    """
    # 元のHTMLを保持（後でテキスト長を比較するため）
    original_html = html_text
    
    # 1. 改行とタブを一旦削除（後で<br>に基づいて再整理するため）
    html_text = re.sub(r'[\r\n\t]+', '', html_text)    
        
    # 2. タイトルの抽出（安全な判定）
    title_match = re.search(r'<title>(.*?)</title>', html_text, flags=re.IGNORECASE | re.DOTALL)
    extracted_title = ""
    
    # 判定順序の整理：titleタグがあるか -> 中身があるか
    if title_match and title_match.group(1).strip():
        extracted_title = title_match.group(1).strip()
        extracted_title = re.sub(r'</?(B|font|span|strong).*?>', '', extracted_title, flags=re.IGNORECASE)
    else:
        # 見出しを探す
        hx_match = re.search(r'<h[1-9].*?>(.*?)</h[1-9].*?>', html_text, flags=re.IGNORECASE | re.DOTALL)
        if hx_match:
            extracted_title = hx_match.group(1).strip()
            extracted_title = re.sub(r'</?(B|font|span|strong).*?>', '', extracted_title, flags=re.IGNORECASE)
    if not extracted_title:
        logger.warning("タイトルが見つかりません")

    # 3. BeautifulSoupを使って不要なタグと属性を削除
    soup = BeautifulSoup(html_text, 'html.parser')
    
    # 4. 不要なタグを完全に削除（タグとその中身）
    # <head>, <title>, <search>, <time>, <georss> は保持する
    for tag in soup.find_all(['script', 'style', 'meta']):
        tag.decompose()
    
    # 5. コメントを削除
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    
    # 6. フォーマットタグを削除（タグのみ削除、中身は保持）
    unwrap_tags = ['font', 'span', 'strong', 'b', 'em', 'i', 'u', 'strike', 's', 'center']
    for tag_name in unwrap_tags:
        for tag in soup.find_all(tag_name):
            tag.unwrap()
    
    # 7. すべてのタグから不要な属性を削除
    bad_attrs = ['bgcolor', 'style', 'class', 'id', 'width', 'height', 'border', 
                 'align', 'valign', 'cellspacing', 'cellpadding', 'lang', 
                 'http-equiv', 'content', 'font-family', 'font-color', 'color']
    
    for tag in soup.find_all(True):  # すべてのタグ
        # imgタグは特別扱い（width/heightは後で処理）
        if tag.name == 'img':
            attrs_to_remove = [attr for attr in tag.attrs if attr not in ['src', 'alt', 'width', 'height']]
        else:
            attrs_to_remove = [attr for attr in tag.attrs if attr in bad_attrs]
        
        for attr in attrs_to_remove:
            del tag[attr]
    
    # 8. 画像処理 (figure/figcaptionの追加)
    # Bloggerでの表示互換性のため、figureではなくdivを使用する
    for img in soup.find_all('img'):
        # divタグ作成
        div_wrapper = soup.new_tag('div', style="text-align:center; margin-bottom:1em;")
        # alt取得
        alt_text = img.get('alt')
        alt_text = alt_text.strip() if alt_text is not None else "Image"
        # caption作成
        caption = soup.new_tag('div', style="font-size:small; color:#666;")
        caption.string = alt_text
        # imgをdivでラップし、captionを追加
        img.wrap(div_wrapper)
        div_wrapper.append(caption)

    # <body>と<head>の属性を削除（タグは保持）
    for tag_name in ['body', 'head']:
        tag = soup.find(tag_name)
        if tag:
            tag.attrs = {}
    
    # HTML文字列に戻す（全体を保持）
    html_text = str(soup)
    
    # 念のため、残っているfontタグを正規表現でも削除
    html_text = re.sub(r'<font[^>]*>', '', html_text, flags=re.IGNORECASE)
    html_text = re.sub(r'</font>', '', html_text, flags=re.IGNORECASE)
    
    # 6. 改行整理
    #html_text = re.sub(r'[\r\n\t]+', '\n', html_text) # 連続改行をスペース1つに
    html_text = re.sub(r'\s+', ' ', html_text).strip()
    #html_text = re.sub(r'<br.?*>', '<br />\n', html_text, flags=re.IGNORECASE)
    html_text = re.sub(r'(<br/>|</br>|<br>|<br\s*/>)', '<br/>\n', html_text, flags=re.IGNORECASE)    

    # 7. テーブルやリストなどの構造タグの後にも改行を入れるとソースが見やすくなります
    html_text = re.sub(r'(</td>|</tr>|</table>|</h1>|</h2>|</h3>|</li>)', r'\1\n', html_text, flags=re.IGNORECASE)
    
    # 【重大エラーチェック】コンテンツ削除検出
    # head/script/styleなどの削除で大きく減ることがあるため、本文テキスト同士で比較する
    original_plain = re.sub(r'<[^>]*>', '', original_html)
    cleaned_plain = re.sub(r'<[^>]*>', '', html_text)
    original_length = len(original_plain)
    cleaned_length = len(cleaned_plain)
    
    # 本文が極端に削られていないかチェック（20%未満なら中断）
    if original_length > 100 and cleaned_length < original_length * 0.2:
        error_msg = (
            "HTML クリーニング時にコンテンツが過度に削除されました。\n"
            f"元(本文): {original_length}文字 → 削除後: {cleaned_length}文字\n"
            "正規表現が過度に積極的な可能性があります。サンプルHTMLで検証してください。"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # 11. HTML構造の正規化（<head>と<body>が存在しない場合は追加）
    soup_final = BeautifulSoup(html_text, 'html.parser')
    
    # <head>タグの存在確認と追加
    if not soup_final.find('head'):
        head_tag = soup_final.new_tag('head')
        # <title>を探してあればheadに移動
        title_tag = soup_final.find('title')
        if title_tag:
            title_tag.extract()
            head_tag.append(title_tag)
        # htmlタグがあればその先頭に、なければ全体の先頭に挿入
        html_tag = soup_final.find('html')
        if html_tag:
            html_tag.insert(0, head_tag)
        else:
            soup_final.insert(0, head_tag)
    
    # <body>タグの存在確認と追加
    if not soup_final.find('body'):
        body_tag = soup_final.new_tag('body')
        # <head>以外の全要素をbodyに移動
        head_tag = soup_final.find('head')
        for element in list(soup_final.children):
            if element != head_tag and element.name not in [None, 'html']:
                element.extract()
                body_tag.append(element)
        # htmlタグがあればその中に、なければ全体に追加
        html_tag = soup_final.find('html')
        if html_tag:
            html_tag.append(body_tag)
        else:
            soup_final.append(body_tag)
    
    html_text = str(soup_final)
    
    return html_text.strip()

def run_cleaning():
    """
    作業ディレクトリを初期化し、HTMLファイルをクリーニングする。
    main.pyから呼び出されることを想定。
    """
    # ✅ work/ ディレクトリをリセット（reports/ からコピー）
    REPORTS_DIR = SCRIPT_DIR / get_config('DEFAULT', 'reports_dir', './reports')
    
    if not REPORTS_DIR.exists():
        logger.error(f"{REPORTS_DIR} が見つかりません")
        return 0, 1 # success, error
    
    # work/ を削除して再作成
    shutil.rmtree(str(OUTPUT_DIR), ignore_errors=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # reports/ から work/ にコピー
    logger.info(f"{REPORTS_DIR} から {OUTPUT_DIR} へファイルをコピーしています...")
    try:
        shutil.copytree(str(REPORTS_DIR), str(OUTPUT_DIR), dirs_exist_ok=True)
    except Exception as e:
        logger.error(f"ディレクトリコピーに失敗しました: {e}", exc_info=True)
        return 0, 1
    
    # エラー出力用ディレクトリの準備
    ERROR_DIR = SCRIPT_DIR / 'cleaning_errors'
    shutil.rmtree(str(ERROR_DIR), ignore_errors=True)
    ERROR_DIR.mkdir(exist_ok=True)

    processed_count = 0
    error_count = 0

    logger.info(f"HTMLクリーニング処理を開始: {OUTPUT_DIR}")

    files_to_process = [p for p in OUTPUT_DIR.rglob('*') if p.is_file() and p.suffix.lower() in ('.htm', '.html')]
    
    if not files_to_process:
        logger.warning("クリーニング対象のHTMLファイルが見つかりません。")
        return 0, 0

    pbar = ProgressBar(len(files_to_process), prefix='Clean')

    for src_path in files_to_process:
        content = None
        for encoding in ['utf-8', 'cp932', 'shift_jis', 'euc-jp']:
            try:
                with open(src_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except Exception:
                continue

        if content:
            try:
                cleaned_html = clean_html_for_blogger(content)
                with open(src_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_html)
                processed_count += 1
            except Exception as e:
                logger.error(f"HTMLクリーニングエラー: {src_path.name} - {e}", exc_info=True)
                error_count += 1
                # エラーファイルを退避
                try:
                    shutil.move(str(src_path), str(ERROR_DIR / src_path.name))
                    logger.info(f"エラーファイルを退避しました: {src_path.name} -> {ERROR_DIR.name}/")
                except Exception as move_error:
                    logger.error(f"エラーファイルの退避に失敗: {move_error}")
        else:
            logger.error(f"文字コード不明でスキップ: {src_path.name}")
            error_count += 1
        
        pbar.update()

    logger.info(f"完了: HTMLクリーニング {processed_count}件")
    return processed_count, error_count

# --- メイン処理 ---
if __name__ == '__main__':
    try:
        run_cleaning()
    except Exception as e:
        logger.critical(f"予期せぬエラーが発生しました: {e}", exc_info=True)

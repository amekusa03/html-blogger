import os
import re      
import shutil
import unicodedata
import calendar

# --- 設定 ---
REPORTS_DIR = './reports'        # 元のレポートフォルダ群が入っている親フォルダ
ADD_KEYWORDS_DIR = './addKeyword_upload'        # キーワード追加後のフォルダ群が入っている親フォルダ
OUTPUT_DIR = './ready_to_upload' # 変換後の出力先フォルダ

def clean_html_for_blogger(html_text):
    
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
    if extracted_title:
        print(f"  -> Title見つかりました: {extracted_title}")
    else:
        print("  -> !!!!!Titleが見つかりません!!!!!!") 

            
    # 3. キーワードを抽出して保存する（消される前に！）
    # <meta name="keywords" content="..."> の中身を抜き出す
    keywords_all = re.findall(r'<meta\s+name=["\']keywords["\']\s+content=["\'](.*?)["\']', html_text, flags=re.IGNORECASE | re.DOTALL)
    
    extracted_keywords = ""
    if keywords_all:
        # 見つかったすべてのキーワード定義をカンマで結合
        # 例：['登山', 'スキー'] -> "登山, スキー"
        combined_keywords = ",".join(keywords_all)
        
        # 不要な空白を掃除し、重複を排除（もしあれば）
        kw_list = [k.strip() for k in combined_keywords.split(',') if k.strip()]
        unique_kws = []
        for k in kw_list:
            if k not in unique_kws:
                unique_kws.append(k)
        
        extracted_keywords = ",".join(unique_kws)
    if extracted_keywords:
        print(f"  -> Keywords見つかりました: {extracted_keywords}")
    else:
        print("  -> !!!!Keywordsが見つかりません!!!!")
        
    # 4. 日付を抽出して保存する（消される前に！）
    # <time datetime="..."> の中身を抜き出す
    date_match = re.search(r'<time\s+datetime=["\'](.*?)["\']', html_text, flags=re.IGNORECASE | re.DOTALL)
    extracted_date = ""
    if date_match:
        for group in date_match.groups():
            if group.strip() !="":
                extracted_date = group.strip()
    if not extracted_date:
        # 代替案：本文中の日付パターンを探す（例: 2003年1/18〜20）
        # 正規表現で各パーツを分離して抽出
        # グループ1: 年, グループ2: 月, グループ3: 開始日, グループ4: 終了日(任意)
        unicode  = unicodedata.normalize('NFKC', html_text)

        # まずは年を探す
        def extract_year():
            match = re.search(r'(\d{4})年', unicode)        
            if not match:
                match = re.search(r'(\d{4})/', unicode)
                if not match:
                    match = re.search(r'(\d{4}.)', unicode)
                    if not match:
                        match = re.search(r'(\d{4})', unicode)
                        if not match:
                            return None
            if int(match.group(1)) > 1900 and int(match.group(1)) < 2100:
                return match.group(1)
            return None
        def extract_month():
            match = re.search(r'(\d{1,2})月', unicode)        
            if not match:
                match = re.search(r'/(\d{1,2})/', unicode)
                if not match:
                    match = re.search(r'/(\d{1,2}).', unicode)
                    if not match:
                        match = re.search(r'/(\d{1,2})', unicode)
                        if not match:
                            return None
            month = int(match.group(1))
            if int(month) >=1 and int(month) <=12:
                return str(month)
            return None
        def extract_start_day():
            match = re.search(r'(\d{1,2})日', unicode)        
            if not match:
                match = re.search(r'/(\d{1,2})/', unicode)
                if not match:
                    match = re.search(r'/(\d{1,2}).', unicode)
                    if not match:
                        match = re.search(r'/(\d{1,2})', unicode)
                        if not match:
                            return None
            day = int(match.group(1))
            if day >=1 and day <=31:
                return str(day)
            return None
        def extract_end_day():
            match = re.search(r'〜\s*(\d{1,2})日', unicode)        
            if not match:
                match = re.search(r'〜\s*/(\d{1,2})/', unicode)
                if not match:
                    match = re.search(r'〜\s*/(\d{1,2}).', unicode)
                    if not match:
                        match = re.search(r'〜\s*/(\d{1,2})', unicode)
                        if not match:
                            return None
            day = int(match.group(1))
            if day >=1 and day <=31:
                return str(day)
            return None

        year = extract_year()
        month = extract_month()
        start_day = extract_start_day()
        end_day = extract_end_day()
        
        # ✅ None チェック強化
        if year is None or month is None:
            year, month, start_day = None, None, None
        
        if end_day is None:
            day = start_day
        else:
            day = end_day
        
        # day が None の場合は月の最終日を使用
        if day is None and year is not None and month is not None:
            try:
                day = str(calendar.monthrange(int(year), int(month))[1])
            except (ValueError, TypeError):
                day = None
            
        # すべての必須フィールドがそろった場合のみ日付を確定
        if start_day is not None and month is not None and year is not None and day is not None:
            extracted_date = f"{year}-{month}-{day}"

    if extracted_date:
        print(f"  -> Date見つかりました: {extracted_date}")
    else:
        print("  -> !!!!Dateが見つかりません!!!!")                    

    # 5. 不要なタグの削除
    #html_text = re.sub(r'</?(font|b).*?>', '', html_text, flags=re.IGNORECASE) # まとめて削除
    html_text = re.sub(r'</?(font|span|strong).*?>', '', html_text, flags=re.IGNORECASE)
    html_text = re.sub(r'(</?b>|</b>|<b .*?>)', '', html_text, flags=re.IGNORECASE)

    patterns_to_remove = [
            r'<head.*?>.*?</head>',
            r'<script.*?>.*?</script>',
            r'<style.*?>.*?</style>',
            r'<title.*?>.*?</title>',
            # --- HTTrackのコメントを個別に、かつ確実に消すパターン ---
            r'', 
            r'',
            # --- 一般的なコメントを「改行を含めて」最短一致で消すパターン ---
            r'',
            r'<!--.*?-->',
            r'<meta.*?>',
            r'<!doctype.*?>' # ついでにdoctypeも消しておくと綺麗です
    ]
    for pattern in patterns_to_remove:
        # flags=re.DOTALL を付けることで、コメントが複数行にわたっても削除できます
        html_text = re.sub(pattern, '', html_text, flags=re.DOTALL | re.IGNORECASE)
 
     
    # 6. 特定の不要な属性を削除 (styleやbgcolorなど)
    bad_attrs = ['bgcolor', 'style', 'class', 'id', 'width', 'height', 'border', 'align', 'valign', 'cellspacing', 'cellpadding', 'lang', 'http-equiv', 'content','font-family','font color','!--']
    for attr in bad_attrs:
        pattern = rf'\s+{attr}\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)'
        html_text = re.sub(pattern, '', html_text, flags=re.IGNORECASE)

    # 7. body内を抽出(style, bgcolorなど)
    # bad_attrs = ['bgcolor', 'style', 'class', 'id', 'width', 'height', 'border', 'align', 'valign', 'cellspacing', 'cellpadding', 'lang', 'http-equiv', 'content','font-family','font color']
    # for attr in bad_attrs:
    #     pattern = rf'\s+{attr}\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)'
    #     html_text = re.sub(pattern, '', html_text, flags=re.IGNORECASE)

    # 8. 改行整理
    #html_text = re.sub(r'[\r\n\t]+', '\n', html_text) # 連続改行をスペース1つに
    html_text = re.sub(r'\s+', ' ', html_text).strip()
    #html_text = re.sub(r'<br.?*>', '<br />\n', html_text, flags=re.IGNORECASE)
    html_text = re.sub(r'(<br/>|</br>)', '<br/>\n', html_text)    

    # 9. テーブルやリストなどの構造タグの後にも改行を入れるとソースが見やすくなります
    html_text = re.sub(r'(</td>|</tr>|</table>|</h1>|</h2>|</h3>|</li>)', r'\1\n', html_text, flags=re.IGNORECASE)
    
    # 10. 画像処理 (figcaptionの修正)
    def replace_img(match):
        img_tag = match.group(0)
        alt_match = re.search(r'alt=["\'](.*?)["\']', img_tag, flags=re.IGNORECASE)
        alt_text = alt_match.group(1).strip() if alt_match else "Image"
        # centerタグを使わずstyleで調整
        figcaption = f'<figcaption style="text-align:center;">{alt_text}</figcaption>'
        return f'<figure style="text-align:center;">{img_tag}{figcaption}</figure>'

    html_text = re.sub(r'<img[^>]*>', replace_img, html_text, flags=re.IGNORECASE)
    
    # 情報を下から順に積み上げるように結合します
    # 本文の構成： [キーワード] -> [タイトル] -> [日付] -> [元の本文]
    # 10.本文の先頭にタイトルを挿入する
    # 最後にメタ情報を先頭に付与（Blogger APIで活用するための目印）
    # 最後に日付を入れる
    if extracted_date:
        html_text = f'<time datetime="{extracted_date}"></time>\n' + html_text
        
    # 次にタイトルを入れる
    if extracted_title:
        html_text = f'<title>{extracted_title}</title>\n' + html_text

    # 一番上にキーワード（ラベル）を入れる
    if extracted_keywords:
        # ここで確実に html_text の先頭に結合します
        html_text = f'{extracted_keywords}\n' + html_text
        print(f"  -> 出力確認: {extracted_keywords}")
                
    return html_text.strip()

# --- 実行セクション ---
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

if os.path.exists(ADD_KEYWORDS_DIR):
    SOURCE_DIR = ADD_KEYWORDS_DIR
else:   
    SOURCE_DIR = REPORTS_DIR

processed_count = 0
image_count = 0

print(f"--- 変換処理を開始します (対象フォルダ: {SOURCE_DIR}) ---")

for root, dirs, files in os.walk(SOURCE_DIR):
    rel_path = os.path.relpath(root, SOURCE_DIR)
    dest_dir = os.path.join(OUTPUT_DIR, rel_path)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    for filename in files:
        src_path = os.path.join(root, filename)
        if filename.lower().endswith(('.htm', '.html')):
            processed_count += 1
            base_name = os.path.splitext(filename)[0]
            dest_path = os.path.join(dest_dir, f"{base_name}.html")

            content = None
            # 文字コードの判定
            for encoding in ['utf-8', 'cp932', 'shift_jis']:
                try:
                    with open(src_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except:
                    continue

            if content:
                print(f"[{processed_count}] code {SOURCE_DIR}/{rel_path}/{filename}")
                cleaned = clean_html_for_blogger(content)
                with open(dest_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned)
                print(f" -->HTML変換成功: {dest_path}")
            else:
                print(f"[{processed_count}] ×失敗(文字コード不明): {rel_path}/{filename}")

        else:
            # 画像ファイルなどはそのままコピー
            image_count += 1
            dest_path = os.path.join(dest_dir, filename)
            shutil.copy2(src_path, dest_path)

print("-" * 30)
print(f"【処理完了】")
print(f"変換したHTML: {processed_count} 本")
print(f"コピーした画像他: {image_count} ファイル")


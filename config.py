# coding: utf-8
import os
import sys
import configparser
import subprocess

# --------------------------------------------------
# configparser の宣言と config.ini の読み込み
# --------------------------------------------------
config_ini = configparser.ConfigParser()

CONFIG_FILE = 'config.ini'
if not os.path.exists(CONFIG_FILE):
    print(f'エラー: {CONFIG_FILE} が見つかりません。')
    sys.exit(1)

try:
    config_ini.read(CONFIG_FILE, encoding='utf-8')
except Exception as e:
    print(f'エラー: {CONFIG_FILE} の読み込みに失敗しました: {e}')
    sys.exit(1)


# --------------------------------------------------
# デフォルト値の定義
# --------------------------------------------------
DEFAULTS = {
    'XML_FILE': 'keywords.xml',
    'ORIGINAL_DIR': './reports',
    'ADD_KEYWORDS_DIR': './addKeyword_upload',
    'REPORTS_DIR': './reports',
    'CLEANER_OUTPUT_DIR': './ready_to_upload',
    'SOURCE_PHOTOS_DIR': './ready_to_upload',
    'IMAGE_PREPARER_OUTPUT_DIR': './ready_to_upload_images',
    'BLOGGER_SIGNIN_URL': 'https://www.blogger.com/go/signin',
    'MEDIA_MANAGER_URL': 'http://blogger.com/mediamanager',
    'CONVERT_ATOM_INPUT_DIR': './ready_to_upload',
    'OUTPUT_FILE': 'feed.atom',
    'BLOG_TITLE': 'My Blog',
    'BLOG_URL': 'https://example.blogspot.com',
    'BLOG_ID': '',
    'MEDIA_MANAGER_FILE': 'Blogger メディア マネージャー_*.html',
    'LOG_FILE': 'uploaded_atom_ids.txt',
    'SCOPES': 'https://www.googleapis.com/auth/blogger',
    'DELAY_SECONDS': '15',
    'MAX_POSTS_PER_RUN': '5',
}


def get_config(section, key, default=None):
    """設定値を取得する（デフォルト値対応、コメント削除、引用符削除）"""
    try:
        value = config_ini.get(section, key)
        # コメント（#の後）を削除
        if '#' in value:
            value = value.split('#')[0].strip()
        # 引用符を削除 ('...' または "...")
        value = value.strip()
        if (value.startswith("'") and value.endswith("'")) or \
           (value.startswith('"') and value.endswith('"')):
            value = value[1:-1]
        return value
    except (configparser.NoSectionError, configparser.NoOptionError):
        if default is not None:
            return default
        # デフォルト値辞書から取得
        defaults_key = f'{section.upper()}_{key}'.lower()
        if defaults_key in DEFAULTS:
            return DEFAULTS[defaults_key]
        print(f'警告: [{section}] {key} が見つかりません。デフォルト値を使用します。')
        return None


# --------------------------------------------------
# config.ini から値取得
# --------------------------------------------------

# --- add_keywords.py 用設定 ---
XML_FILE = get_config('ADD_KEYWORDS', 'XML_FILE', DEFAULTS.get('XML_FILE'))
ORIGINAL_DIR = get_config('ADD_KEYWORDS', 'ORIGINAL_DIR', DEFAULTS.get('ORIGINAL_DIR'))
ADD_KEYWORDS_DIR = get_config('ADD_KEYWORDS', 'ADD_KEYWORDS_DIR', DEFAULTS.get('ADD_KEYWORDS_DIR'))

# --- cleaner.py 用設定 ---
REPORTS_DIR = get_config('CLEANER', 'REPORTS_DIR', DEFAULTS.get('REPORTS_DIR'))
CLEANER_ADD_KEYWORDS_DIR = get_config('CLEANER', 'ADD_KEYWORDS_DIR', ADD_KEYWORDS_DIR)
CLEANER_OUTPUT_DIR = get_config('CLEANER', 'OUTPUT_DIR', DEFAULTS.get('CLEANER_OUTPUT_DIR'))

# ---- OPEN_BLOGGER 用設定 ---
BLOGGER_SIGNIN_URL = get_config('OPEN_BLOGGER', 'BLOGGER_SIGNIN_URL', DEFAULTS.get('BLOGGER_SIGNIN_URL'))
MEDIA_MANAGER_URL = get_config('OPEN_BLOGGER', 'MEDIA_MANAGER_URL', DEFAULTS.get('MEDIA_MANAGER_URL'))

# --- image_preparer.py 用設定 ---
SOURCE_PHOTOS_DIR = get_config('IMAGE_PREPARER', 'SOURCE_PHOTOS_DIR', DEFAULTS.get('SOURCE_PHOTOS_DIR'))
IMAGE_PREPARER_OUTPUT_DIR = get_config('IMAGE_PREPARER', 'OUTPUT_DIR', DEFAULTS.get('IMAGE_PREPARER_OUTPUT_DIR'))
MEDIA_MANAGER_URL = get_config('IMAGE_PREPARER', 'MEDIA_MANAGER_URL', DEFAULTS.get('MEDIA_MANAGER_URL'))

# --- convert_atom.py 用設定 ---
CONVERT_ATOM_INPUT_DIR = get_config('CONVERT_ATOM', 'INPUT_DIR', DEFAULTS.get('CONVERT_ATOM_INPUT_DIR'))
OUTPUT_FILE = get_config('CONVERT_ATOM', 'OUTPUT_FILE', DEFAULTS.get('OUTPUT_FILE'))
BLOG_TITLE = get_config('CONVERT_ATOM', 'BLOG_TITLE', DEFAULTS.get('BLOG_TITLE'))
BLOG_URL = get_config('CONVERT_ATOM', 'BLOG_URL', DEFAULTS.get('BLOG_URL'))

# --- uploader.py 用設定 ---
BLOG_ID = get_config('UPLOADER', 'BLOG_ID', DEFAULTS.get('BLOG_ID'))
MEDIA_MANAGER_FILE = get_config('UPLOADER', 'MEDIA_MANAGER_FILE', DEFAULTS.get('MEDIA_MANAGER_FILE'))
LOG_FILE = get_config('UPLOADER', 'LOG_FILE', DEFAULTS.get('LOG_FILE'))
SCOPES_STR = get_config('UPLOADER', 'SCOPES', DEFAULTS.get('SCOPES'))
SCOPES = [s.strip() for s in SCOPES_STR.split(',')]
DELAY_SECONDS = int(get_config('UPLOADER', 'DELAY_SECONDS', DEFAULTS.get('DELAY_SECONDS')))
MAX_POSTS_PER_RUN = int(get_config('UPLOADER', 'MAX_POSTS_PER_RUN', DEFAULTS.get('MAX_POSTS_PER_RUN')))


# --------------------------------------------------
# 設定の検証
# --------------------------------------------------
def validate_config():
    """設定の整合性を検証"""
    issues = []
    
    if not BLOG_ID or BLOG_ID == 'あなたのブログID':
        issues.append('⚠️  BLOG_ID が設定されていません。')
    
    if not os.path.exists(REPORTS_DIR):
        issues.append(f'⚠️  REPORTS_DIR {REPORTS_DIR} が見つかりません。')
    
    if not os.path.exists(CLEANER_ADD_KEYWORDS_DIR):
        issues.append(f'⚠️  ADD_KEYWORDS_DIR {CLEANER_ADD_KEYWORDS_DIR} が見つかりません。')
    
    if DELAY_SECONDS < 1:
        issues.append('⚠️  DELAY_SECONDS は1以上である必要があります。')
    
    if MAX_POSTS_PER_RUN < 1:
        issues.append('⚠️  MAX_POSTS_PER_RUN は1以上である必要があります。')
    
    return issues


# 起動時に検証を実行（オプション）
if __name__ == '__main__':
    print('【設定の検証】')
    issues = validate_config()
    if issues:
        for issue in issues:
            print(issue)
    else:
        print('✅ 設定は正常です。')
    
    print('\n【読み込まれた設定値】')
    print(f'XML_FILE: {XML_FILE}')
    print(f'REPORTS_DIR: {REPORTS_DIR}')
    print(f'CLEANER_OUTPUT_DIR: {CLEANER_OUTPUT_DIR}')
    print(f'IMAGE_PREPARER_OUTPUT_DIR: {IMAGE_PREPARER_OUTPUT_DIR}')
    print(f'CONVERT_ATOM_INPUT_DIR: {CONVERT_ATOM_INPUT_DIR}')
    print(f'BLOG_TITLE: {BLOG_TITLE}')
    print(f'DELAY_SECONDS: {DELAY_SECONDS}')
    print(f'MAX_POSTS_PER_RUN: {MAX_POSTS_PER_RUN}')

def open_file_with_default_app(filepath):
    """ファイルパスを受け取り、OSの標準アプリで開く関数"""
    if sys.platform == 'win32': # Windows
        os.startfile(filepath)
    elif sys.platform == 'darwin': # macOS
        subprocess.call(['open', filepath])
    elif sys.platform.startswith('linux'): # Linux
        subprocess.call(['xdg-open', filepath])
    else:
        print(f"未対応のOS: {sys.platform}")

def open_keywords_app():
    """keywords.xml を標準アプリで開く"""
    xml_path = os.path.abspath(XML_FILE)
    if os.path.exists(xml_path):
        open_file_with_default_app(xml_path)
    else:
        print(f'エラー: {xml_path} が見つかりません。')

def open_config_file():
    """config.ini を標準アプリで開く"""
    config_path = os.path.abspath(CONFIG_FILE)
    if os.path.exists(config_path):
        open_file_with_default_app(config_path)
    else:
        print(f'エラー: {config_path} が見つかりません。')  
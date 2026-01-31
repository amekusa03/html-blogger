# -*- coding: utf-8 -*-
import os
import pickle
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from config import get_config

# --- ロギング設定 ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('google_auth.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
logger.addHandler(logging.StreamHandler())

# 外部ライブラリの技術的なログを抑制
logging.getLogger('googleapiclient').setLevel(logging.ERROR)
logging.getLogger('google_auth_oauthlib').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)

# --- 設定 ---
SCRIPT_DIR = Path(__file__).parent.resolve()
SCOPES = [get_config('UPLOADER', 'scopes', 'https://www.googleapis.com/auth/blogger')]

def get_blogger_service():
    """Google Blogger API サービスオブジェクトを取得"""
    credentials_file = SCRIPT_DIR / 'credentials.json'
    if not credentials_file.exists():
        raise FileNotFoundError('credentials.json が見つかりません。Google Cloud Console から OAuth2 認証情報をダウンロードしてください。')
    
    creds = None
    token_file = SCRIPT_DIR / 'token.pickle'
    if token_file.exists():
        try:
            with open(str(token_file), 'rb') as token:
                creds = pickle.load(token)
        except Exception as e:
            logger.warning(f'token.pickle の読み込みエラー: {e}')
            creds = None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info('トークンをリフレッシュしました。')
            except Exception as e:
                logger.warning(f'トークンリフレッシュエラー: {e}。新規認証を実施します。')
                creds = None
        
        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(SCRIPT_DIR / 'credentials.json'), SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info('新規認証に成功しました。')
            except Exception as e:
                raise Exception(f'Google 認証に失敗しました: {e}')
        
        try:
            with open(str(SCRIPT_DIR / 'token.pickle'), 'wb') as token:
                pickle.dump(creds, token)
        except Exception as e:
            logger.warning(f'token.pickle の保存エラー: {e}')
    
    return build('blogger', 'v3', credentials=creds)
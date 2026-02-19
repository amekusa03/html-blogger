# coding: utf-8
import logging
import pickle
from logging import config, getLogger
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from json5 import load

from parameter import config

# --- ロギング設定 ---
# logging設定
with open("./data/log_config.json5", "r") as f:
    logging.config.dictConfig(load(f))
logger = getLogger(__name__)

# --- 設定 ---
scopes = config["auth_google"]["scopes"]
credentials_file = config["auth_google"]["credentials_file"]
token_file = config["auth_google"]["token_file"]

def get_blogger_service():
    """Google Blogger API サービスオブジェクトを取得"""
    if not Path(credentials_file).exists():
        raise FileNotFoundError(
            "credentials.json が見つかりません。Google Cloud Console から OAuth2 認証情報をダウンロードしてください。"
        )

    creds = None
    if Path(token_file).exists():
        try:
            with open(str(token_file), "rb") as token:
                creds = pickle.load(token)
        except Exception as e:
            logger.warning(f"token.pickle の読み込みエラー: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("トークンをリフレッシュしました。")
            except Exception as e:
                logger.warning(
                    f"トークンリフレッシュエラー: {e}。新規認証を実施します。"
                )
                creds = None

        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_file), scopes
                )
                creds = flow.run_local_server(port=0)
                logger.info("新規認証に成功しました。")
            except Exception as e:
                raise Exception(f"Google 認証に失敗しました: {e}")

        try:
            with open(str(token_file), "wb") as token:
                pickle.dump(creds, token)
        except Exception as e:
            logger.warning(f"token.pickle の保存エラー: {e}")

    return build("blogger", "v3", credentials=creds)

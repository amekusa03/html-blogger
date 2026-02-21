# coding: utf-8
"""auth_google.py
Google 認証関連の処理を提供するモジュール
"""
import logging
import pickle
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from parameter import config

logger = logging.getLogger(__name__)

# --- 設定 ---
scopes = config["auth_google"]["scopes"]
credentials_file = config["auth_google"]["credentials_file"]
token_file = config["auth_google"]["token_file"]


class BloggerService:
    """Google 認証エラーのカスタム例外クラス"""

    creds = None
    resource_object = None

    def __init__(self):
        """Google Blogger API サービスオブジェクトを取得"""
        if not Path(credentials_file).exists():
            raise FileNotFoundError(
                "credentials.json が見つかりません。Google Cloud Console から OAuth2 認証情報をダウンロードしてください。"
            )

        self.creds = None
        if Path(token_file).exists():
            with open(str(token_file), "rb") as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    logger.info("トークンをリフレッシュしました。")
                except RefreshError as e:
                    logger.warning(
                        "トークンリフレッシュエラー: %s。新規認証を実施します。", e
                    )
                    self.creds = None

            if not self.creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(credentials_file), scopes
                    )
                    self.creds = flow.run_local_server(port=0)
                    logger.info("新規認証に成功しました。")
                except Exception as e:
                    logger.error("Google 認証エラー: %s", e, exc_info=True)
                    raise RefreshError(e) from e

            with open(str(token_file), "wb") as token:
                pickle.dump(self.creds, token)
        self.resource_object = build("blogger", "v3", credentials=self.creds)

    def posts(self):
        """Blogger API の posts() メソッドを呼び出すためのラッパー"""
        return self.resource_object.posts()  # pylint: disable=no-member

"""
認証ユーティリティモジュール

AWS Cognito JWT トークンの検証と、保護されたエンドポイントへのアクセス制御を行うユーティリティ関数を提供します。
ユーザー認証の検証とトークン内のクレーム（user_id など）の取得を行います。

@author 中井健登
@version 1.0.0
@date 2023-04-07
"""

import os
import json
import time
import jwt
import requests
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwk, jwt
from jose.utils import base64url_decode
from pydantic import BaseModel
from typing import Dict, Optional

# 環境変数から Cognito の設定を取得
REGION = os.getenv("AWS_REGION", "ap-northeast-1")
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID")

# JWT トークンの検証用セキュリティスキーマ
security = HTTPBearer()

class CognitoJWTVerifier:
    """
    AWS Cognito JWT トークンの検証を行うクラス
    """
    
    def __init__(self, region: str, user_pool_id: str, app_client_id: str):
        """
        CognitoJWTVerifier のコンストラクタ
        
        @param region AWS リージョン
        @param user_pool_id Cognito ユーザープールID
        @param app_client_id Cognito アプリクライアントID
        """
        self.region = region
        self.user_pool_id = user_pool_id
        self.app_client_id = app_client_id
        self.keys = self._get_public_keys()
        
    def _get_public_keys(self) -> Dict:
        """
        Cognito ユーザープールの公開鍵を取得する
        
        @returns Dict 公開鍵情報
        """
        keys_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
        try:
            response = requests.get(keys_url)
            response.raise_for_status()
            return {key["kid"]: key for key in response.json()["keys"]}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"公開鍵の取得に失敗しました: {str(e)}"
            )
    
    def verify_token(self, token: str) -> Dict:
        """
        JWT トークンを検証し、有効な場合はペイロードを返す
        
        @param token 検証する JWT トークン
        @returns Dict 検証済みのトークンペイロード
        """
        try:
            # トークンのヘッダーを取得
            headers = jwt.get_unverified_header(token)
            kid = headers["kid"]
            
            # 対応する公開鍵を取得
            if kid not in self.keys:
                self.keys = self._get_public_keys()  # 鍵が見つからない場合は再取得
                if kid not in self.keys:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="トークンの検証に失敗しました: 無効な鍵ID"
                    )
            
            public_key = self.keys[kid]
            
            # トークンの署名を検証
            message, encoded_signature = token.rsplit(".", 1)
            decoded_signature = base64url_decode(encoded_signature.encode())
            
            # 公開鍵を使用してトークンを検証
            payload = jwt.decode(
                token,
                jwk.construct(public_key),
                algorithms=["RS256"],
                audience=self.app_client_id,
                issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
            )
            
            # トークンの有効期限を確認
            current_time = time.time()
            if payload.get("exp", 0) < current_time:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="トークンの有効期限が切れています"
                )
            
            return payload
        except jwt.JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"トークンの検証に失敗しました: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"認証エラー: {str(e)}"
            )

# Cognito JWT 検証インスタンスの初期化
cognito_verifier = CognitoJWTVerifier(REGION, USER_POOL_ID, APP_CLIENT_ID)

class UserInfo(BaseModel):
    """
    認証されたユーザー情報を表すモデル
    """
    user_id: str
    username: str
    email: Optional[str] = None
    groups: Optional[list] = None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> UserInfo:
    """
    現在認証されているユーザーの情報を取得する FastAPI dependency

    @param credentials HTTPAuthorizationCredentials 認証情報
    @returns UserInfo 認証されたユーザー情報
    """
    try:
        token = credentials.credentials
        payload = cognito_verifier.verify_token(token)
        
        # ユーザー情報を抽出
        user_id = payload.get("sub")
        username = payload.get("username", payload.get("cognito:username"))
        email = payload.get("email")
        groups = payload.get("cognito:groups", [])
        
        return UserInfo(
            user_id=user_id,
            username=username,
            email=email,
            groups=groups
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"認証エラー: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def verify_user_id(provided_user_id: str, current_user: UserInfo = Depends(get_current_user)) -> bool:
    """
    リクエスト内のユーザーIDがJWTトークン内のユーザーIDと一致するか検証する
    
    @param provided_user_id リクエストで提供されたユーザーID
    @param current_user 現在認証されているユーザー情報
    @returns bool 検証結果
    """
    if provided_user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="リクエスト内のユーザーIDが認証されたユーザーIDと一致しません"
        )
    return True
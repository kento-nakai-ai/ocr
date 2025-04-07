"""
資格試験対策システム APIパッケージ

このパッケージは、資格試験対策システムのAPIを構成するモジュール群を含みます。
FastAPIフレームワークを使用してREST APIを実装し、AWS Cognitoによる認証を統合しています。

@author 中井健登
@version 1.0.0
@date 2023-04-07
"""

from .models import init_db

# アプリケーション起動時にデータベーススキーマを初期化
init_db() 
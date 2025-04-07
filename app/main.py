"""
資格試験対策システム API メインモジュール

このモジュールは、資格試験対策システムのWebAPIエントリーポイントです。
FastAPIフレームワークを使用して、頻出問題取得、苦手問題取得、回答登録などの機能を提供します。
認証はAWS Cognitoを使用し、JWTトークンの検証と保護されたエンドポイントへのアクセス制御を行います。

@author 中井健登
@version 1.0.0
@date 2023-04-07
"""

import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .routes import frequent_questions, user_answers, weak_questions
from .utils.auth import get_current_user

# FastAPIアプリケーションの初期化
app = FastAPI(
    title="資格試験対策システム API",
    description="資格試験の頻出問題、苦手問題を提供し、ユーザーの回答を記録・分析するAPI",
    version="1.0.0"
)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限すること
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルートURLへのエンドポイント
@app.get("/")
async def root():
    """
    APIのルートエンドポイント。システムの基本情報を返します。
    
    @returns dict システムの基本情報
    """
    return {
        "name": "資格試験対策システム API",
        "version": "1.0.0",
        "status": "running"
    }

# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    """
    ヘルスチェック用エンドポイント。システムの稼働状況を確認します。
    
    @returns dict ヘルスチェック結果
    """
    return {"status": "healthy"}

# 各ルーターの登録
app.include_router(frequent_questions.router, prefix="/api/v1")
app.include_router(weak_questions.router, prefix="/api/v1")
app.include_router(user_answers.router, prefix="/api/v1")

# アプリケーション起動コード（直接実行する場合）
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 
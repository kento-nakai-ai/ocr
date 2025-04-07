"""
データベース接続モジュール

SQLAlchemyを使用したデータベース接続とセッション管理機能を提供します。
データベースの設定はORM操作用のエンジンとセッションを初期化します。

@author 中井健登
@version 1.0.0
@date 2023-04-07
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator

# 環境変数からデータベースURLを取得
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./exam_api.db")

# SQLAlchemyエンジンの設定
# SQLiteの場合はcheck_same_threadをFalseに設定
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# SQLAlchemyエンジンの作成
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=os.getenv("SQL_DEBUG", "0") == "1"  # SQLデバッグを有効にするオプション
)

# セッションファクトリの作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# モデルの基底クラス
Base = declarative_base()

def get_db() -> Generator:
    """
    データベースセッションを取得するためのジェネレータ関数。
    FastAPIの依存性注入システムで使用します。
    
    @yields セッションオブジェクト
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 
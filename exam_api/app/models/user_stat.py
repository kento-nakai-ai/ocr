"""
ユーザー成績統計モデルモジュール

ユーザーの学習成績データを表すSQLAlchemyモデルとPydanticモデルを定義します。
合計スコア、正解数、不正解数などの統計情報を持ちます。

@author 中井健登
@version 1.0.0
@date 2023-04-07
"""

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from .database import Base

class UserStat(Base):
    """
    ユーザーの成績統計を表すSQLAlchemyモデル
    """
    __tablename__ = "user_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    total_score = Column(Float, nullable=False, default=0.0)
    correct_count = Column(Integer, nullable=False, default=0)
    wrong_count = Column(Integer, nullable=False, default=0)
    exam_type = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        """
        モデルのテキスト表現を提供
        
        @returns str テキスト表現
        """
        return f"<UserStat(id={self.id}, user_id={self.user_id}, total_score={self.total_score})>"


class UserStatBase(BaseModel):
    """
    ユーザー成績統計の基本情報を表すPydanticモデル
    """
    user_id: str = Field(..., title="ユーザーID")
    total_score: float = Field(..., title="合計スコア")
    correct_count: int = Field(..., title="正解数")
    wrong_count: int = Field(..., title="不正解数")
    exam_type: str = Field(..., title="試験種別", description="例: 1級電気")


class UserStatCreate(UserStatBase):
    """
    ユーザー成績統計作成用のPydanticモデル
    """
    pass


class UserStatUpdate(BaseModel):
    """
    ユーザー成績統計更新用のPydanticモデル
    """
    total_score: Optional[float] = None
    correct_count: Optional[int] = None
    wrong_count: Optional[int] = None


class UserStatResponse(UserStatBase):
    """
    ユーザー成績統計のレスポンス用Pydanticモデル
    """
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class UserAnswerStatResponse(BaseModel):
    """
    ユーザー回答登録後の成績統計レスポンス用Pydanticモデル
    """
    user_answer_ids: list[int] = Field(..., title="登録されたユーザー回答ID一覧")
    new_user_stat: UserStatResponse = Field(..., title="新しい成績統計")
    max_user_stat: Optional[UserStatResponse] = Field(None, title="最高スコアの成績統計")
    before_user_stat: Optional[UserStatResponse] = Field(None, title="直前の成績統計")

    class Config:
        orm_mode = True 
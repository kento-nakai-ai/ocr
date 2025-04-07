"""
ユーザー回答モデルモジュール

ユーザーの問題回答データを表すSQLAlchemyモデルとPydanticモデルを定義します。
ユーザーIDと問題ID、選択した回答ID、正誤情報などを持ちます。

@author 中井健登
@version 1.0.0
@date 2023-04-07
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from .database import Base

class UserAnswer(Base):
    """
    ユーザーの問題回答を表すSQLAlchemyモデル
    """
    __tablename__ = "user_answers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    answer_id = Column(Integer, nullable=False)
    status = Column(Boolean, nullable=False, comment="正解(True)か不正解(False)か")
    exam_type = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    question = relationship("Question", backref="user_answers")
    
    def __repr__(self):
        """
        モデルのテキスト表現を提供
        
        @returns str テキスト表現
        """
        return f"<UserAnswer(id={self.id}, user_id={self.user_id}, question_id={self.question_id}, status={self.status})>"


class UserAnswerItem(BaseModel):
    """
    ユーザー回答アイテムを表すPydanticモデル
    """
    question_id: int = Field(..., title="問題ID")
    answer_id: int = Field(..., title="選択肢ID")
    status: bool = Field(..., title="正誤", description="正解(True)か不正解(False)か")


class UserAnswerCreate(BaseModel):
    """
    ユーザー回答作成用のPydanticモデル（一括登録用）
    """
    user_id: str = Field(..., title="ユーザーID")
    questions: List[UserAnswerItem] = Field(..., title="回答した問題一覧")
    exam_type: str = Field(..., title="試験種別", description="例: 1級電気")


class UserAnswerResponse(BaseModel):
    """
    ユーザー回答のレスポンス用Pydanticモデル
    """
    id: int
    user_id: str
    question_id: int
    answer_id: int
    status: bool
    exam_type: str
    created_at: datetime

    class Config:
        orm_mode = True


class UserAnswerBatchResponse(BaseModel):
    """
    ユーザー回答一括登録のレスポンス用Pydanticモデル
    """
    user_answer_ids: List[int] = Field(..., title="登録されたユーザー回答ID一覧")

    class Config:
        orm_mode = True 
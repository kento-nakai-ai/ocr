"""
問題モデルモジュール

問題データを表すSQLAlchemyモデルとPydanticモデルを定義します。
問題はタイトル、本文、難易度、試験種別などの情報を持ちます。

@author 中井健登
@version 1.0.0
@date 2023-04-07
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .database import Base

class Question(Base):
    """
    問題を表すSQLAlchemyモデル
    """
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    difficulty = Column(String(50), nullable=False)
    is_mandatory = Column(Boolean, default=False)
    year_list = Column(String(255))
    exam_type = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        """
        モデルのテキスト表現を提供
        
        @returns str テキスト表現
        """
        return f"<Question(id={self.id}, title='{self.title}', exam_type='{self.exam_type}')>"


class QuestionBase(BaseModel):
    """
    問題の基本情報を表すPydanticモデル
    """
    title: str = Field(..., title="問題タイトル", description="例: 施工管理法に関する問題")
    body: str = Field(..., title="問題本文", description="マークダウン形式の問題文と解説")
    difficulty: str = Field(..., title="難易度", description="LOW, MID, HIGHのいずれか")
    is_mandatory: bool = Field(False, title="必須問題フラグ")
    year_list: Optional[str] = Field(None, title="出題年度リスト", description="例: 2021,2022,2023")
    exam_type: str = Field(..., title="試験種別", description="例: 1級電気")


class QuestionCreate(QuestionBase):
    """
    問題作成用のPydanticモデル
    """
    pass


class QuestionUpdate(BaseModel):
    """
    問題更新用のPydanticモデル
    """
    title: Optional[str] = None
    body: Optional[str] = None
    difficulty: Optional[str] = None
    is_mandatory: Optional[bool] = None
    year_list: Optional[str] = None
    exam_type: Optional[str] = None


class QuestionResponse(QuestionBase):
    """
    問題のレスポンス用Pydanticモデル
    """
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True 
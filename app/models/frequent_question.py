"""
頻出問題モデルモジュール

頻出問題データを表すSQLAlchemyモデルとPydanticモデルを定義します。
頻出問題は問題IDとスコア（出題頻度など）の情報を持ちます。

@author 中井健登
@version 1.0.0
@date 2023-04-07
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from .database import Base

class FrequentQuestion(Base):
    """
    頻出問題を表すSQLAlchemyモデル
    """
    __tablename__ = "frequent_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    final_score = Column(Float, nullable=False, comment="頻出度スコア（出題頻度×正答率など）")
    exam_type = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーションシップ
    question = relationship("Question", backref="frequent_questions")
    
    def __repr__(self):
        """
        モデルのテキスト表現を提供
        
        @returns str テキスト表現
        """
        return f"<FrequentQuestion(id={self.id}, question_id={self.question_id}, final_score={self.final_score})>"


class FrequentQuestionBase(BaseModel):
    """
    頻出問題の基本情報を表すPydanticモデル
    """
    question_id: int = Field(..., title="問題ID")
    final_score: float = Field(..., title="頻出度スコア", ge=0.0, le=1.0)
    exam_type: str = Field(..., title="試験種別", description="例: 1級電気")


class FrequentQuestionCreate(FrequentQuestionBase):
    """
    頻出問題作成用のPydanticモデル
    """
    pass


class FrequentQuestionUpdate(BaseModel):
    """
    頻出問題更新用のPydanticモデル
    """
    final_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    exam_type: Optional[str] = None


class FrequentQuestionResponse(FrequentQuestionBase):
    """
    頻出問題のレスポンス用Pydanticモデル
    """
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class FrequentQuestionBatchCreate(BaseModel):
    """
    頻出問題の一括登録用Pydanticモデル
    """
    questions: List[FrequentQuestionCreate] = Field(..., title="頻出問題リスト") 
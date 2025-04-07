"""
データモデルパッケージ

このパッケージは、資格試験対策システムで使用するデータモデルを定義します。
SQLAlchemyモデルとPydanticモデルの両方を含み、データベーススキーマとAPIスキーマを定義します。

@author 中井健登
@version 1.0.0
@date 2023-04-07
"""

from .database import Base, engine, SessionLocal
from .question import Question, QuestionCreate, QuestionResponse
from .frequent_question import FrequentQuestion, FrequentQuestionCreate
from .user_answer import UserAnswer, UserAnswerCreate, UserAnswerResponse
from .user_stat import UserStat, UserStatCreate, UserStatResponse

# データベース初期化関数
def init_db():
    """
    アプリケーション起動時にデータベーススキーマを初期化します。
    """
    Base.metadata.create_all(bind=engine) 
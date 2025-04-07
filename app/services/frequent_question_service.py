"""
頻出問題サービスモジュール

頻出問題の取得や管理に関するビジネスロジックを実装します。
SQLAlchemyを使用してデータベースとの連携を行い、頻出問題の抽出や登録を行います。

@author 中井健登
@version 1.0.0
@date 2023-04-07
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional, Tuple
from ..models.frequent_question import FrequentQuestion, FrequentQuestionCreate, FrequentQuestionBatchCreate
from ..models.question import Question
from ..models.user_answer import UserAnswer

class FrequentQuestionService:
    """
    頻出問題サービスクラス
    
    頻出問題の取得や管理に関するビジネスロジックを提供します。
    """
    
    @staticmethod
    def get_frequent_question_ids(
        db: Session, 
        user_id: str, 
        exam_type: str, 
        limit: int = 10,
        exclude_recent_answers: bool = True
    ) -> List[int]:
        """
        ユーザーの試験種別に対応する頻出問題IDのリストを取得します。
        
        @param db データベースセッション
        @param user_id ユーザーID
        @param exam_type 試験種別（例: 1級電気）
        @param limit 取得する問題数
        @param exclude_recent_answers 直近で回答した問題を除外するかどうか
        @returns List[int] 頻出問題IDリスト
        """
        # ユーザーが最近回答した問題IDを取得（必要な場合）
        recent_question_ids = []
        if exclude_recent_answers:
            recent_answers = db.query(UserAnswer.question_id) \
                .filter(UserAnswer.user_id == user_id, UserAnswer.exam_type == exam_type) \
                .order_by(desc(UserAnswer.created_at)) \
                .limit(20) \
                .all()
            recent_question_ids = [answer.question_id for answer in recent_answers]
        
        # 頻出問題を取得（最近回答した問題を除外）
        query = db.query(FrequentQuestion) \
            .filter(FrequentQuestion.exam_type == exam_type)
        
        if exclude_recent_answers and recent_question_ids:
            query = query.filter(~FrequentQuestion.question_id.in_(recent_question_ids))
        
        frequent_questions = query.order_by(desc(FrequentQuestion.final_score)) \
            .limit(limit) \
            .all()
        
        # 頻出問題IDリストを作成
        return [fq.question_id for fq in frequent_questions]
    
    @staticmethod
    def get_question_by_id(db: Session, question_id: int) -> Optional[Question]:
        """
        問題IDから問題詳細を取得します。
        
        @param db データベースセッション
        @param question_id 問題ID
        @returns Optional[Question] 問題詳細（存在しない場合はNone）
        """
        return db.query(Question).filter(Question.id == question_id).first()
    
    @staticmethod
    def get_frequent_questions(
        db: Session, 
        user_id: str, 
        exam_type: str, 
        limit: int = 10,
        exclude_recent_answers: bool = True
    ) -> Tuple[List[int], Optional[Question]]:
        """
        ユーザーの試験種別に対応する頻出問題を取得します。
        
        @param db データベースセッション
        @param user_id ユーザーID
        @param exam_type 試験種別（例: 1級電気）
        @param limit 取得する問題数
        @param exclude_recent_answers 直近で回答した問題を除外するかどうか
        @returns Tuple[List[int], Optional[Question]] 頻出問題IDリストと初回表示用1問
        """
        # 頻出問題IDリストを取得
        question_ids = FrequentQuestionService.get_frequent_question_ids(
            db=db,
            user_id=user_id,
            exam_type=exam_type,
            limit=limit,
            exclude_recent_answers=exclude_recent_answers
        )
        
        # 初回表示用の問題を取得
        first_question = None
        if question_ids:
            first_question = FrequentQuestionService.get_question_by_id(
                db=db,
                question_id=question_ids[0]
            )
        
        return question_ids, first_question
    
    @staticmethod
    def create_frequent_question(db: Session, frequent_question: FrequentQuestionCreate) -> FrequentQuestion:
        """
        頻出問題を登録します。
        
        @param db データベースセッション
        @param frequent_question 登録する頻出問題情報
        @returns FrequentQuestion 登録された頻出問題
        """
        # 既存の問題が存在するか確認
        question = db.query(Question).filter(Question.id == frequent_question.question_id).first()
        if not question:
            raise ValueError(f"指定された問題ID {frequent_question.question_id} は存在しません")
        
        # 既存の頻出問題が存在するか確認し、あれば更新、なければ新規作成
        db_frequent_question = db.query(FrequentQuestion) \
            .filter(
                FrequentQuestion.question_id == frequent_question.question_id,
                FrequentQuestion.exam_type == frequent_question.exam_type
            ) \
            .first()
        
        if db_frequent_question:
            # 既存の頻出問題を更新
            db_frequent_question.final_score = frequent_question.final_score
        else:
            # 新規頻出問題を作成
            db_frequent_question = FrequentQuestion(
                question_id=frequent_question.question_id,
                final_score=frequent_question.final_score,
                exam_type=frequent_question.exam_type
            )
            db.add(db_frequent_question)
        
        db.commit()
        db.refresh(db_frequent_question)
        return db_frequent_question
    
    @staticmethod
    def batch_create_frequent_questions(db: Session, batch: FrequentQuestionBatchCreate) -> int:
        """
        頻出問題を一括登録します。
        
        @param db データベースセッション
        @param batch 登録する頻出問題情報のバッチ
        @returns int 更新された問題数
        """
        updated_count = 0
        
        for frequent_question in batch.questions:
            try:
                FrequentQuestionService.create_frequent_question(db, frequent_question)
                updated_count += 1
            except ValueError:
                # 問題が存在しない場合はスキップして続行
                continue
        
        return updated_count 
"""
苦手問題サービスモジュール

ユーザーの苦手問題の特定と取得に関するビジネスロジックを実装します。
回答履歴や誤答率などを分析し、ユーザーが苦手とする問題を抽出します。

@author 中井健登
@version 1.0.0
@date 2023-04-07
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional, Dict
from ..models.user_answer import UserAnswer
from ..models.question import Question

class WeakQuestionService:
    """
    苦手問題サービスクラス
    
    ユーザーの苦手問題の特定と取得に関するビジネスロジックを提供します。
    """
    
    @staticmethod
    def get_weak_question_ids(
        db: Session, 
        user_id: str, 
        exam_type: str, 
        limit: int = 10
    ) -> List[int]:
        """
        ユーザーの苦手問題のIDリストを取得します。
        
        @param db データベースセッション
        @param user_id ユーザーID
        @param exam_type 試験種別（例: 1級電気）
        @param limit 取得する問題数
        @returns List[int] 苦手問題IDリスト
        """
        # 以下のロジックでユーザーの苦手問題を抽出：
        # 1. ユーザーが不正解した問題を優先
        # 2. 問題の難易度が高いものを優先
        # 3. 必須問題を優先
        
        # 不正解の問題を取得
        incorrect_answers = db.query(
                UserAnswer.question_id,
                func.count(UserAnswer.id).label('incorrect_count')
            ) \
            .filter(
                UserAnswer.user_id == user_id,
                UserAnswer.exam_type == exam_type,
                UserAnswer.status == False
            ) \
            .group_by(UserAnswer.question_id) \
            .order_by(desc('incorrect_count')) \
            .limit(limit * 2)  # 余裕を持って取得
        
        # 不正解の問題IDリスト
        incorrect_question_ids = [answer.question_id for answer in incorrect_answers]
        
        if not incorrect_question_ids:
            # 不正解の問題がない場合は難易度の高い問題を取得
            difficult_questions = db.query(Question) \
                .filter(Question.exam_type == exam_type) \
                .filter(Question.difficulty == "HIGH") \
                .order_by(Question.id) \
                .limit(limit) \
                .all()
            
            return [q.id for q in difficult_questions]
        
        # 不正解の問題から難易度と必須フラグを加味して優先度を計算
        questions = db.query(Question) \
            .filter(Question.id.in_(incorrect_question_ids)) \
            .all()
        
        # 問題の優先度を計算
        question_priorities = []
        for q in questions:
            # 優先度計算ロジック
            # - 難易度: LOW=1, MID=2, HIGH=3
            # - 必須フラグ: True=2, False=1
            difficulty_score = 1
            if q.difficulty == "MID":
                difficulty_score = 2
            elif q.difficulty == "HIGH":
                difficulty_score = 3
                
            mandatory_score = 2 if q.is_mandatory else 1
            
            # 総合的な優先度スコア
            priority = difficulty_score * mandatory_score
            
            question_priorities.append((q.id, priority))
        
        # 優先度の高い順にソート
        question_priorities.sort(key=lambda x: x[1], reverse=True)
        
        # 指定件数だけ取得
        result_ids = [qp[0] for qp in question_priorities[:limit]]
        
        return result_ids
    
    @staticmethod
    def get_question_by_id(db: Session, question_id: int) -> Optional[Question]:
        """
        問題IDから問題詳細を取得します。
        
        @param db データベースセッション
        @param question_id 問題ID
        @returns Optional[Question] 問題詳細（存在しない場合はNone）
        """
        return db.query(Question).filter(Question.id == question_id).first() 
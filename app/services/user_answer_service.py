"""
ユーザー回答サービスモジュール

ユーザーの問題回答データの登録と、成績統計の更新に関するビジネスロジックを実装します。
ユーザーの回答を保存し、それに基づいた統計情報（合格率スコア等）を計算します。

@author 中井健登
@version 1.0.0
@date 2023-04-07
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional, Tuple, Dict
from ..models.user_answer import UserAnswer, UserAnswerCreate, UserAnswerItem
from ..models.user_stat import UserStat, UserStatCreate
from ..models.question import Question

class UserAnswerService:
    """
    ユーザー回答サービスクラス
    
    ユーザーの問題回答データの登録と、成績統計の更新に関するビジネスロジックを提供します。
    """
    
    @staticmethod
    def save_user_answers(db: Session, user_answer_data: UserAnswerCreate) -> Tuple[List[int], UserStat, Optional[UserStat], Optional[UserStat]]:
        """
        ユーザーの問題回答を保存し、成績統計を更新します。
        
        @param db データベースセッション
        @param user_answer_data ユーザー回答データ
        @returns Tuple[List[int], UserStat, Optional[UserStat], Optional[UserStat]] 保存されたユーザー回答IDリスト、新しい成績統計、最高スコアの成績統計、直前の成績統計
        """
        # 既存のユーザー成績統計を取得
        existing_stats = db.query(UserStat) \
            .filter(
                UserStat.user_id == user_answer_data.user_id,
                UserStat.exam_type == user_answer_data.exam_type
            ) \
            .order_by(desc(UserStat.created_at)) \
            .all()
        
        # 直前の成績統計
        before_stat = existing_stats[0] if existing_stats else None
        
        # 最高スコアの成績統計
        max_stat = None
        if existing_stats:
            max_stat = max(existing_stats, key=lambda stat: stat.total_score)
        
        # ユーザー回答を保存
        user_answer_ids = []
        correct_count = 0
        wrong_count = 0
        
        # 回答する問題のIDリスト
        question_ids = [item.question_id for item in user_answer_data.questions]
        
        # 問題の難易度と必須フラグを取得
        questions = db.query(Question) \
            .filter(Question.id.in_(question_ids)) \
            .all()
        
        # 問題情報の辞書を作成（高速なルックアップのため）
        question_info: Dict[int, Dict] = {
            q.id: {
                "difficulty": q.difficulty,
                "is_mandatory": q.is_mandatory
            } for q in questions
        }
        
        for item in user_answer_data.questions:
            # 問題が存在するか確認
            if item.question_id not in question_info:
                continue
            
            # ユーザー回答を作成
            user_answer = UserAnswer(
                user_id=user_answer_data.user_id,
                question_id=item.question_id,
                answer_id=item.answer_id,
                status=item.status,
                exam_type=user_answer_data.exam_type
            )
            db.add(user_answer)
            db.flush()  # IDを生成するためにflushする
            
            user_answer_ids.append(user_answer.id)
            
            # 正解・不正解のカウント
            if item.status:
                correct_count += 1
            else:
                wrong_count += 1
        
        # 合格率スコアを計算
        total_score = UserAnswerService._calculate_score(
            correct_count, wrong_count, question_info, user_answer_data.questions
        )
        
        # 新しい成績統計を作成
        new_stat = UserStat(
            user_id=user_answer_data.user_id,
            total_score=total_score,
            correct_count=correct_count,
            wrong_count=wrong_count,
            exam_type=user_answer_data.exam_type
        )
        db.add(new_stat)
        
        # 変更をコミット
        db.commit()
        db.refresh(new_stat)
        
        return user_answer_ids, new_stat, max_stat, before_stat
    
    @staticmethod
    def _calculate_score(correct_count: int, wrong_count: int, question_info: Dict[int, Dict], answers: List[UserAnswerItem]) -> float:
        """
        回答に基づいて合格率スコアを計算します。
        必須問題の正解・難易度などを考慮したスコア計算を行います。
        
        @param correct_count 正解数
        @param wrong_count 不正解数
        @param question_info 問題情報の辞書
        @param answers 回答リスト
        @returns float 合格率スコア（0.0～100.0）
        """
        if not answers:
            return 0.0
        
        # 基本スコア（正解率）
        total_questions = correct_count + wrong_count
        base_score = (correct_count / total_questions) * 100 if total_questions > 0 else 0
        
        # 難易度による重み付け
        difficulty_weights = {
            "LOW": 0.8,
            "MID": 1.0,
            "HIGH": 1.2
        }
        
        # 必須問題の重み
        mandatory_weight = 1.5
        
        # 重み付けスコアの計算
        weighted_score = 0.0
        total_weight = 0.0
        
        for answer in answers:
            qid = answer.question_id
            if qid not in question_info:
                continue
                
            info = question_info[qid]
            
            # 難易度の重み
            diff_weight = difficulty_weights.get(info["difficulty"], 1.0)
            
            # 必須問題の場合は追加の重み
            if info["is_mandatory"]:
                diff_weight *= mandatory_weight
                
            # 正解・不正解に応じてスコアを加算
            if answer.status:
                weighted_score += 1.0 * diff_weight
            
            total_weight += diff_weight
        
        # 重み付けされた合格率スコアを計算
        weighted_percentage = (weighted_score / total_weight) * 100 if total_weight > 0 else 0
        
        # 基本スコアと重み付けスコアを組み合わせて最終スコアを計算
        final_score = (base_score * 0.4) + (weighted_percentage * 0.6)
        
        return round(final_score, 2)
    
    @staticmethod
    def get_user_stats(db: Session, user_id: str, exam_type: str) -> List[UserStat]:
        """
        ユーザーの成績統計履歴を取得します。
        
        @param db データベースセッション
        @param user_id ユーザーID
        @param exam_type 試験種別
        @returns List[UserStat] 成績統計履歴
        """
        return db.query(UserStat) \
            .filter(
                UserStat.user_id == user_id,
                UserStat.exam_type == exam_type
            ) \
            .order_by(desc(UserStat.created_at)) \
            .all() 
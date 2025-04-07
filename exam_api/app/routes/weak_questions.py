"""
苦手問題ルートモジュール

ユーザーの苦手問題に関連するエンドポイントを定義します。
ユーザーの回答履歴から苦手傾向の問題を特定し、提供するAPIを実装します。

@author 中井健登
@version 1.0.0
@date 2023-04-07
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..models.database import get_db
from ..models.question import QuestionResponse
from ..services.weak_question_service import WeakQuestionService
from ..utils.auth import get_current_user, verify_user_id, UserInfo

router = APIRouter(tags=["苦手問題"])

@router.get("/weak-questions", status_code=status.HTTP_200_OK)
async def get_weak_questions(
    user_id: str = Query(..., description="ユーザーID"),
    exam_type: str = Query(..., description="試験種別（例: 1級電気）"),
    limit: int = Query(10, description="取得する問題数", ge=1, le=50),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ユーザーの苦手問題を取得するエンドポイント。
    問題IDのリストを返します。
    
    @param user_id ユーザーID
    @param exam_type 試験種別（例: 1級電気）
    @param limit 取得する問題数
    @param current_user 認証済みユーザー情報
    @param db データベースセッション
    @returns dict 苦手問題IDリスト
    """
    # ユーザーIDの検証
    verify_user_id(user_id, current_user)
    
    try:
        # 苦手問題サービスから問題IDを取得
        question_ids = WeakQuestionService.get_weak_question_ids(
            db=db,
            user_id=user_id,
            exam_type=exam_type,
            limit=limit
        )
        
        # 問題が見つからない場合
        if not question_ids:
            return {
                "question_ids": []
            }
        
        # レスポンスの作成
        return {
            "question_ids": question_ids
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"苦手問題の取得中にエラーが発生しました: {str(e)}"
        ) 
"""
頻出問題ルートモジュール

頻出問題に関連するエンドポイントを定義します。
ユーザーの試験種別に応じた頻出問題を取得するAPI、および頻出問題を登録するAPIを提供します。

@author 中井健登
@version 1.0.0
@date 2023-04-07
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..models.database import get_db
from ..models.frequent_question import FrequentQuestionBatchCreate
from ..models.question import QuestionResponse
from ..services.frequent_question_service import FrequentQuestionService
from ..utils.auth import get_current_user, verify_user_id, UserInfo

router = APIRouter(tags=["頻出問題"])

@router.get("/frequent-questions", status_code=status.HTTP_200_OK)
async def get_frequent_questions(
    user_id: str = Query(..., description="ユーザーID"),
    exam_type: str = Query(..., description="試験種別（例: 1級電気）"),
    limit: int = Query(10, description="取得する問題数", ge=1, le=50),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    頻出問題を取得するエンドポイント。
    問題IDのリストを返します。
    
    @param user_id ユーザーID
    @param exam_type 試験種別（例: 1級電気）
    @param limit 取得する問題数
    @param current_user 認証済みユーザー情報
    @param db データベースセッション
    @returns dict 頻出問題IDリスト
    """
    # ユーザーIDの検証
    verify_user_id(user_id, current_user)
    
    try:
        # 頻出問題サービスから問題IDのみを取得
        question_ids = FrequentQuestionService.get_frequent_question_ids(
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
            detail=f"頻出問題の取得中にエラーが発生しました: {str(e)}"
        )

@router.get("/questions/{question_id}", status_code=status.HTTP_200_OK, response_model=QuestionResponse)
async def get_question(
    question_id: int,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    問題IDから問題詳細を取得するエンドポイント。
    
    @param question_id 問題ID
    @param current_user 認証済みユーザー情報
    @param db データベースセッション
    @returns QuestionResponse 問題詳細
    """
    try:
        # 問題を取得
        question = FrequentQuestionService.get_question_by_id(
            db=db,
            question_id=question_id
        )
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"問題ID {question_id} が見つかりません"
            )
        
        return question
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"問題の取得中にエラーが発生しました: {str(e)}"
        )

@router.post("/frequent-questions", status_code=status.HTTP_201_CREATED)
async def create_frequent_questions(
    batch: FrequentQuestionBatchCreate,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    頻出問題を一括登録するエンドポイント。（週次バッチ用）
    管理者権限を持つユーザーのみアクセス可能です。
    
    @param batch 登録する頻出問題情報のバッチ
    @param current_user 認証済みユーザー情報
    @param db データベースセッション
    @returns dict 更新された問題数と結果メッセージ
    """
    # 管理者権限チェック
    if "admin" not in current_user.groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このエンドポイントにアクセスする権限がありません"
        )
    
    try:
        # 頻出問題の一括登録
        updated_count = FrequentQuestionService.batch_create_frequent_questions(db, batch)
        
        return {
            "updated_count": updated_count,
            "message": "頻出問題が正常に更新されました"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"頻出問題の登録中にエラーが発生しました: {str(e)}"
        ) 
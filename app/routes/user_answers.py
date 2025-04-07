"""
ユーザー回答ルートモジュール

ユーザーの問題回答に関連するエンドポイントを定義します。
ユーザーが問題に回答したデータを登録し、成績統計を更新するAPIを提供します。

@author 中井健登
@version 1.0.0
@date 2023-04-07
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..models.database import get_db
from ..models.user_answer import UserAnswerCreate
from ..models.user_stat import UserAnswerStatResponse, UserStatResponse
from ..services.user_answer_service import UserAnswerService
from ..utils.auth import get_current_user, verify_user_id, UserInfo

router = APIRouter(tags=["ユーザー回答"])

@router.post("/user-answers", status_code=status.HTTP_201_CREATED, response_model=UserAnswerStatResponse)
async def create_user_answers(
    user_answer_data: UserAnswerCreate,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ユーザーの問題回答を登録し、成績統計を更新するエンドポイント。
    
    @param user_answer_data ユーザー回答データ
    @param current_user 認証済みユーザー情報
    @param db データベースセッション
    @returns UserAnswerStatResponse 登録結果と更新された成績統計
    """
    # ユーザーIDの検証
    verify_user_id(user_answer_data.user_id, current_user)
    
    try:
        # ユーザー回答の保存と成績統計の更新
        user_answer_ids, new_stat, max_stat, before_stat = UserAnswerService.save_user_answers(
            db=db,
            user_answer_data=user_answer_data
        )
        
        # レスポンスの作成
        response = {
            "user_answer_ids": user_answer_ids,
            "new_user_stat": new_stat
        }
        
        # 最高スコアと直前スコアがある場合は追加
        if max_stat:
            response["max_user_stat"] = max_stat
        
        if before_stat and before_stat.id != new_stat.id:
            response["before_user_stat"] = before_stat
        
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ユーザー回答の登録中にエラーが発生しました: {str(e)}"
        )

@router.get("/user-stats/{user_id}", status_code=status.HTTP_200_OK)
async def get_user_stats(
    user_id: str,
    exam_type: str,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ユーザーの成績統計履歴を取得するエンドポイント。
    
    @param user_id ユーザーID
    @param exam_type 試験種別
    @param current_user 認証済みユーザー情報
    @param db データベースセッション
    @returns dict 成績統計履歴
    """
    # ユーザーIDの検証
    verify_user_id(user_id, current_user)
    
    try:
        # ユーザーの成績統計を取得
        user_stats = UserAnswerService.get_user_stats(
            db=db,
            user_id=user_id,
            exam_type=exam_type
        )
        
        # レスポンスの作成
        return {
            "user_id": user_id,
            "exam_type": exam_type,
            "stats": [UserStatResponse.from_orm(stat) for stat in user_stats]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ユーザー成績統計の取得中にエラーが発生しました: {str(e)}"
        )
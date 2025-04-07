#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
タグ管理ユーティリティ

このモジュールは、データベース内のタグを管理するための機能を提供します。
タグの追加、更新、検索、問題へのタグ付けなどの操作が可能です。
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Any, Optional, Union
import logging
from datetime import datetime

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TagManager:
    """
    タグを管理するためのクラス
    
    タグの定義や問題へのタグ付け、タグベースの検索機能を提供します。
    """
    
    def __init__(self, db_config: Dict[str, str]):
        """
        TagManagerクラスの初期化
        
        Args:
            db_config: データベース接続設定の辞書
                {
                    'dbname': データベース名,
                    'user': ユーザー名,
                    'password': パスワード,
                    'host': ホスト名,
                    'port': ポート番号
                }
        """
        self.db_config = db_config
        self.conn = None
        self.cursor = None
    
    def connect(self) -> None:
        """
        データベースに接続する
        
        Raises:
            Exception: 接続エラーが発生した場合
        """
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            logger.info("データベースに接続しました")
        except Exception as e:
            logger.error(f"データベース接続エラー: {e}")
            raise
    
    def disconnect(self) -> None:
        """データベース接続を閉じる"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            logger.info("データベース接続を閉じました")
    
    def __enter__(self):
        """コンテキストマネージャーのエントリーポイント"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了処理"""
        self.disconnect()
    
    def get_tag_definitions(self) -> List[Dict[str, Any]]:
        """
        すべてのタグ定義を取得する
        
        Returns:
            タグ定義のリスト
        """
        try:
            self.cursor.execute("""
                SELECT id, tag_key, tag_type, description, possible_values, remarks
                FROM tag_definitions
                ORDER BY tag_key
            """)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"タグ定義の取得に失敗しました: {e}")
            self.conn.rollback()
            raise
    
    def get_tag_definition(self, tag_key: str) -> Optional[Dict[str, Any]]:
        """
        特定のタグ定義を取得する
        
        Args:
            tag_key: 取得するタグのキー
            
        Returns:
            タグ定義の辞書、存在しない場合はNone
        """
        try:
            self.cursor.execute("""
                SELECT id, tag_key, tag_type, description, possible_values, remarks
                FROM tag_definitions
                WHERE tag_key = %s
            """, (tag_key,))
            result = self.cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"タグ定義の取得に失敗しました: {e}")
            self.conn.rollback()
            raise
    
    def add_tag_definition(self, 
                          tag_key: str, 
                          tag_type: str, 
                          description: str, 
                          possible_values: Optional[List[str]] = None, 
                          remarks: Optional[str] = None) -> int:
        """
        新しいタグ定義を追加する
        
        Args:
            tag_key: タグのキー名
            tag_type: タグのタイプ ('Flag', 'Categorical', 'Array', 'Enum', 'Text')
            description: タグの説明
            possible_values: 可能な値のリスト（オプション）
            remarks: 備考（オプション）
            
        Returns:
            追加されたタグのID
            
        Raises:
            ValueError: タグキーが既に存在する場合
        """
        try:
            # 既存のタグ定義をチェック
            self.cursor.execute("""
                SELECT id FROM tag_definitions WHERE tag_key = %s
            """, (tag_key,))
            
            if self.cursor.fetchone():
                raise ValueError(f"タグキー '{tag_key}' は既に存在します")
            
            # 新しいタグ定義を挿入
            possible_values_json = json.dumps(possible_values) if possible_values else None
            
            self.cursor.execute("""
                INSERT INTO tag_definitions 
                (tag_key, tag_type, description, possible_values, remarks)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (tag_key, tag_type, description, possible_values_json, remarks))
            
            tag_id = self.cursor.fetchone()['id']
            self.conn.commit()
            logger.info(f"タグ定義 '{tag_key}' を追加しました (ID: {tag_id})")
            return tag_id
            
        except ValueError as e:
            logger.error(str(e))
            self.conn.rollback()
            raise
        except Exception as e:
            logger.error(f"タグ定義の追加に失敗しました: {e}")
            self.conn.rollback()
            raise
    
    def update_tag_definition(self, 
                             tag_key: str, 
                             tag_type: Optional[str] = None, 
                             description: Optional[str] = None, 
                             possible_values: Optional[List[str]] = None, 
                             remarks: Optional[str] = None) -> bool:
        """
        既存のタグ定義を更新する
        
        Args:
            tag_key: 更新するタグのキー
            tag_type: 新しいタグタイプ（変更する場合）
            description: 新しい説明（変更する場合）
            possible_values: 新しい可能な値のリスト（変更する場合）
            remarks: 新しい備考（変更する場合）
            
        Returns:
            更新が成功したかどうか
            
        Raises:
            ValueError: 指定されたタグキーが存在しない場合
        """
        try:
            # 既存のタグ定義をチェック
            self.cursor.execute("""
                SELECT id FROM tag_definitions WHERE tag_key = %s
            """, (tag_key,))
            
            if not self.cursor.fetchone():
                raise ValueError(f"タグキー '{tag_key}' は存在しません")
            
            # 更新対象フィールドの構築
            update_fields = []
            params = []
            
            if tag_type is not None:
                update_fields.append("tag_type = %s")
                params.append(tag_type)
                
            if description is not None:
                update_fields.append("description = %s")
                params.append(description)
                
            if possible_values is not None:
                update_fields.append("possible_values = %s")
                params.append(json.dumps(possible_values))
                
            if remarks is not None:
                update_fields.append("remarks = %s")
                params.append(remarks)
                
            if not update_fields:
                logger.warning("更新するフィールドが指定されていません")
                return False
                
            # 更新タイムスタンプを追加
            update_fields.append("updated_at = %s")
            params.append(datetime.now())
            
            # パラメータにタグキーを追加
            params.append(tag_key)
            
            # 更新クエリの実行
            query = f"""
                UPDATE tag_definitions
                SET {', '.join(update_fields)}
                WHERE tag_key = %s
            """
            
            self.cursor.execute(query, params)
            self.conn.commit()
            logger.info(f"タグ定義 '{tag_key}' を更新しました")
            return True
            
        except ValueError as e:
            logger.error(str(e))
            self.conn.rollback()
            raise
        except Exception as e:
            logger.error(f"タグ定義の更新に失敗しました: {e}")
            self.conn.rollback()
            raise
    
    def add_tag_to_question(self, 
                           question_id: str, 
                           tag_key: str, 
                           tag_value: str, 
                           ai_inference: Optional[str] = None, 
                           remarks: Optional[str] = None) -> int:
        """
        問題にタグを追加する
        
        Args:
            question_id: 対象の問題ID
            tag_key: タグのキー
            tag_value: タグの値
            ai_inference: AI推論の種類（手動, AI, 専門家など）
            remarks: 備考
            
        Returns:
            追加されたタグのID
            
        Raises:
            ValueError: タグキーが存在しない場合や問題IDが存在しない場合
        """
        try:
            # タグキーの存在確認
            self.cursor.execute("""
                SELECT id FROM tag_definitions WHERE tag_key = %s
            """, (tag_key,))
            
            if not self.cursor.fetchone():
                raise ValueError(f"タグキー '{tag_key}' は存在しません")
                
            # 問題IDの存在確認
            self.cursor.execute("""
                SELECT question_id FROM questions WHERE question_id = %s
            """, (question_id,))
            
            if not self.cursor.fetchone():
                raise ValueError(f"問題ID '{question_id}' は存在しません")
                
            # 既存のタグをチェック（重複防止）
            self.cursor.execute("""
                SELECT id FROM question_tags 
                WHERE question_id = %s AND tag_key = %s
            """, (question_id, tag_key))
            
            existing_tag = self.cursor.fetchone()
            if existing_tag:
                # 既存のタグを更新
                self.cursor.execute("""
                    UPDATE question_tags
                    SET tag_value = %s, 
                        ai_inference = %s, 
                        remarks = %s,
                        updated_at = %s
                    WHERE id = %s
                    RETURNING id
                """, (tag_value, ai_inference, remarks, datetime.now(), existing_tag['id']))
                
                tag_id = self.cursor.fetchone()['id']
                self.conn.commit()
                logger.info(f"問題 '{question_id}' のタグ '{tag_key}' を更新しました (ID: {tag_id})")
                return tag_id
            
            # 新しいタグを追加
            self.cursor.execute("""
                INSERT INTO question_tags
                (question_id, tag_key, tag_value, ai_inference, remarks)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (question_id, tag_key, tag_value, ai_inference, remarks))
            
            tag_id = self.cursor.fetchone()['id']
            self.conn.commit()
            logger.info(f"問題 '{question_id}' にタグ '{tag_key}={tag_value}' を追加しました (ID: {tag_id})")
            return tag_id
            
        except ValueError as e:
            logger.error(str(e))
            self.conn.rollback()
            raise
        except Exception as e:
            logger.error(f"問題へのタグ追加に失敗しました: {e}")
            self.conn.rollback()
            raise
    
    def remove_tag_from_question(self, question_id: str, tag_key: str) -> bool:
        """
        問題からタグを削除する
        
        Args:
            question_id: 問題ID
            tag_key: 削除するタグのキー
            
        Returns:
            削除が成功したかどうか
        """
        try:
            self.cursor.execute("""
                DELETE FROM question_tags
                WHERE question_id = %s AND tag_key = %s
                RETURNING id
            """, (question_id, tag_key))
            
            result = self.cursor.fetchone()
            if result:
                self.conn.commit()
                logger.info(f"問題 '{question_id}' からタグ '{tag_key}' を削除しました")
                return True
            else:
                logger.warning(f"問題 '{question_id}' にタグ '{tag_key}' は存在しません")
                return False
                
        except Exception as e:
            logger.error(f"問題からのタグ削除に失敗しました: {e}")
            self.conn.rollback()
            raise
    
    def get_question_tags(self, question_id: str) -> List[Dict[str, Any]]:
        """
        問題に付けられたすべてのタグを取得する
        
        Args:
            question_id: 問題ID
            
        Returns:
            タグの辞書のリスト
        """
        try:
            self.cursor.execute("""
                SELECT qt.tag_key, qt.tag_value, qt.ai_inference, qt.remarks,
                       td.tag_type, td.description
                FROM question_tags qt
                JOIN tag_definitions td ON qt.tag_key = td.tag_key
                WHERE qt.question_id = %s
                ORDER BY qt.tag_key
            """, (question_id,))
            
            return self.cursor.fetchall()
            
        except Exception as e:
            logger.error(f"問題タグの取得に失敗しました: {e}")
            self.conn.rollback()
            raise
    
    def search_questions_by_tag(self, tag_key: str, tag_value: str) -> List[Dict[str, Any]]:
        """
        指定したタグを持つ問題を検索する
        
        Args:
            tag_key: タグのキー
            tag_value: タグの値
            
        Returns:
            問題の辞書のリスト
        """
        try:
            self.cursor.execute("""
                SELECT q.question_id, q.year, q.content
                FROM questions q
                JOIN question_tags qt ON q.question_id = qt.question_id
                WHERE qt.tag_key = %s AND qt.tag_value = %s
                ORDER BY q.question_id
            """, (tag_key, tag_value))
            
            return self.cursor.fetchall()
            
        except Exception as e:
            logger.error(f"タグによる問題検索に失敗しました: {e}")
            self.conn.rollback()
            raise
    
    def search_questions_by_multiple_tags(self, tag_conditions: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        複数のタグ条件で問題を検索する (AND条件)
        
        Args:
            tag_conditions: タグキーと値のペアを含む辞書
                例: {"difficulty": "HIGH", "category": "law"}
                
        Returns:
            問題の辞書のリスト
        """
        try:
            if not tag_conditions:
                return []
                
            # 複数タグ検索関数を呼び出す
            self.cursor.execute("""
                SELECT * FROM get_questions_by_multiple_tags(%s)
            """, (json.dumps(tag_conditions),))
            
            return self.cursor.fetchall()
            
        except Exception as e:
            logger.error(f"複数タグによる問題検索に失敗しました: {e}")
            self.conn.rollback()
            raise
    
    def get_questions_with_mandatory_flag(self) -> List[Dict[str, Any]]:
        """
        必須フラグ(is_mandatory=true)が付いている問題を取得する
        
        Returns:
            問題の辞書のリスト
        """
        return self.search_questions_by_tag("is_mandatory", "true")
    
    def get_questions_by_difficulty(self, level: str) -> List[Dict[str, Any]]:
        """
        指定した難易度の問題を取得する
        
        Args:
            level: 難易度 ("LOW", "MID", "HIGH")
            
        Returns:
            問題の辞書のリスト
        """
        valid_levels = ["LOW", "MID", "HIGH"]
        if level not in valid_levels:
            raise ValueError(f"無効な難易度: {level}。有効な値は {valid_levels} です")
            
        return self.search_questions_by_tag("difficulty", level)
    
    def get_questions_by_problem_type_and_category(self, problem_type: str, category: str) -> List[Dict[str, Any]]:
        """
        問題タイプとカテゴリの両方に一致する問題を取得する
        
        Args:
            problem_type: 問題タイプ ("calc", "memorization" など)
            category: カテゴリ ("law", "safety", "equipment" など)
            
        Returns:
            問題の辞書のリスト
        """
        tag_conditions = {
            "problem_type": problem_type,
            "category": category
        }
        return self.search_questions_by_multiple_tags(tag_conditions)
    
    def get_frequently_asked_questions(self, min_years: int = 2) -> List[Dict[str, Any]]:
        """
        頻出問題（複数年度で出題された問題）を取得する
        
        Args:
            min_years: 最低出題年数
            
        Returns:
            問題の辞書のリスト
        """
        try:
            self.cursor.execute("""
                SELECT q.question_id, q.year, q.content, qt.tag_value AS year_list
                FROM questions q
                JOIN question_tags qt ON q.question_id = qt.question_id
                WHERE qt.tag_key = 'year_list'
                AND json_array_length(qt.tag_value::json) >= %s
                ORDER BY json_array_length(qt.tag_value::json) DESC
            """, (min_years,))
            
            return self.cursor.fetchall()
            
        except Exception as e:
            logger.error(f"頻出問題の取得に失敗しました: {e}")
            self.conn.rollback()
            raise
    
    def get_questions_by_exam_type(self, exam_type: str) -> List[Dict[str, Any]]:
        """
        指定した試験種別の問題を取得する
        
        Args:
            exam_type: 試験種別 ("1級電気", "1級管", "2級電気", "2級管" など)
            
        Returns:
            問題の辞書のリスト
        """
        return self.search_questions_by_tag("exam_type", exam_type)
    
    def get_stats_by_tag(self, tag_key: str) -> Dict[str, int]:
        """
        指定したタグキーの値ごとの問題数を集計する
        
        Args:
            tag_key: 集計するタグのキー
            
        Returns:
            タグ値と問題数のペアを含む辞書
        """
        try:
            self.cursor.execute("""
                SELECT tag_value, COUNT(*) as count
                FROM question_tags
                WHERE tag_key = %s
                GROUP BY tag_value
                ORDER BY count DESC
            """, (tag_key,))
            
            result = self.cursor.fetchall()
            stats = {item['tag_value']: item['count'] for item in result}
            return stats
            
        except Exception as e:
            logger.error(f"タグ統計の取得に失敗しました: {e}")
            self.conn.rollback()
            raise 
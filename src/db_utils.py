#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
データベース操作ユーティリティ

このモジュールは、PostgreSQL/Aurora DBへの接続とエンベディングベクトルの
保存などのデータベース操作を行うための関数を提供します。
pgvector拡張を利用してベクトル検索に対応します。
"""

import os
import json
import logging
import psycopg2
import numpy as np
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from contextlib import contextmanager

# 環境変数の読み込み
load_dotenv()

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# DB接続情報を環境変数から取得
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'questions_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

@contextmanager
def get_db_connection():
    """
    データベース接続のコンテキストマネージャ

    Returns:
        connection: DBコネクション
    """
    conn = None
    try:
        # 接続情報の設定
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        yield conn
    except Exception as e:
        logger.error(f"DB接続エラー: {str(e)}")
        raise
    finally:
        if conn is not None:
            conn.close()

def initialize_db():
    """
    データベースの初期化
    pgvector拡張のインストールとテーブルの作成を行います。
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                # トランザクション開始
                conn.autocommit = True
                
                # pgvector拡張の有効化
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # コミット
                conn.commit()
                
                # Drop existing table if it exists
                cursor.execute("DROP TABLE IF EXISTS embeddings;")
                
                # embeddingsテーブルの作成
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id SERIAL PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    image_path TEXT,
                    text_content TEXT,
                    embedding_type TEXT NOT NULL,
                    embedding VECTOR(768),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """)
                
                # インデックスの作成
                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_embeddings_file_name ON embeddings (file_name);
                """)
                
                # embeddingにインデックスを作成（近傍検索用）
                cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
                """)
                
                # コミット
                conn.commit()
                
                logger.info("データベースの初期化が完了しました。")
                
            except Exception as e:
                conn.rollback()
                logger.error(f"データベース初期化エラー: {str(e)}")
                raise

def save_embedding_to_db(file_name, embedding_array, embedding_type="text", 
                         image_path=None, text_content=None, metadata=None):
    """
    エンベディングベクトルをデータベースに保存する

    Args:
        file_name (str): ファイル名
        embedding_array (numpy.ndarray): エンベディングベクトル
        embedding_type (str): エンベディングの種類 ("text", "image", "multimodal")
        image_path (str): 画像ファイルのパス（オプション）
        text_content (str): テキスト内容（オプション）
        metadata (dict): メタデータ（オプション）

    Returns:
        int: 挿入されたレコードのID、エラー時は-1
    """
    # nullチェック
    if embedding_array is None:
        logger.error("エンベディング配列がNoneです。")
        return -1
    
    # 型チェック
    if not isinstance(embedding_array, np.ndarray):
        logger.error(f"embedding_arrayはnumpy.ndarrayである必要があります。現在の型: {type(embedding_array)}")
        return -1
    
    # メタデータをJSON文字列に変換
    metadata_json = json.dumps(metadata) if metadata else None
    
    # エンベディングベクトルを文字列に変換
    embedding_str = "[" + ",".join(str(x) for x in embedding_array.tolist()) + "]"
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                # クエリの準備
                query = """
                INSERT INTO embeddings (file_name, image_path, text_content, embedding_type, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s::vector, %s)
                RETURNING id;
                """
                
                # 実行
                cursor.execute(query, (
                    file_name,
                    image_path,
                    text_content,
                    embedding_type,
                    embedding_str,
                    metadata_json
                ))
                
                # IDを取得
                result = cursor.fetchone()
                
                # コミット
                conn.commit()
                
                if result:
                    logger.info(f"エンベディングをDBに保存しました: ID={result[0]}, ファイル={file_name}")
                    return result[0]
                else:
                    logger.warning(f"エンベディングの保存に成功しましたが、IDを取得できませんでした: {file_name}")
                    return -1
                
            except Exception as e:
                conn.rollback()
                logger.error(f"エンベディング保存エラー: {str(e)}")
                return -1

def save_multiple_embeddings_to_db(embeddings_data):
    """
    複数のエンベディングをバッチで保存する

    Args:
        embeddings_data (list): 保存するエンベディングのリスト
            各項目は(file_name, embedding_array, embedding_type, image_path, text_content, metadata)のタプル

    Returns:
        int: 保存に成功したレコードの数
    """
    if not embeddings_data:
        logger.warning("保存するエンベディングがありません。")
        return 0
    
    # データの前処理
    values = []
    for item in embeddings_data:
        file_name, embedding_array, embedding_type, image_path, text_content, metadata = item
        
        if embedding_array is None or not isinstance(embedding_array, np.ndarray):
            logger.warning(f"無効なエンベディング: {file_name} - スキップします")
            continue
        
        # メタデータをJSON文字列に変換
        metadata_json = json.dumps(metadata) if metadata else None
        
        # エンベディングベクトルを文字列に変換
        embedding_str = "[" + ",".join(str(x) for x in embedding_array.tolist()) + "]"
        
        values.append((
            file_name,
            image_path,
            text_content,
            embedding_type,
            embedding_str,
            metadata_json
        ))
    
    if not values:
        logger.warning("有効なエンベディングデータがありません。")
        return 0
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                # クエリの準備
                query = """
                INSERT INTO embeddings (file_name, image_path, text_content, embedding_type, embedding, metadata)
                VALUES %s
                """
                
                # テンプレート
                template = "((%s), (%s), (%s), (%s), (%s)::vector, (%s))"
                
                # 実行
                execute_values(cursor, query, values, template=template)
                
                # 影響を受けた行数
                affected = cursor.rowcount
                
                # コミット
                conn.commit()
                
                logger.info(f"{affected}件のエンベディングをDBに保存しました")
                return affected
                
            except Exception as e:
                conn.rollback()
                logger.error(f"バッチエンベディング保存エラー: {str(e)}")
                return 0

def find_similar_items(query_embedding, limit=10, threshold=0.8, embedding_type=None):
    """
    クエリエンベディングに類似したアイテムを検索する

    Args:
        query_embedding (numpy.ndarray): 検索クエリのエンベディングベクトル
        limit (int): 取得する結果の最大数
        threshold (float): 類似度の閾値（0-1）
        embedding_type (str): エンベディングタイプでフィルタリング（オプション）

    Returns:
        list: 類似アイテムのリスト（ID、ファイル名、類似度を含む）
    """
    if query_embedding is None or not isinstance(query_embedding, np.ndarray):
        logger.error("無効なクエリエンベディング")
        return []
    
    # エンベディングベクトルを文字列に変換
    embedding_str = "[" + ",".join(str(x) for x in query_embedding.tolist()) + "]"
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                # クエリの構築
                query = """
                SELECT id, file_name, image_path, 1 - (embedding <=> %s::vector) AS similarity
                FROM embeddings
                """
                
                params = [embedding_str]
                
                # エンベディングタイプによるフィルタリング（オプション）
                if embedding_type:
                    query += " WHERE embedding_type = %s"
                    params.append(embedding_type)
                
                # 類似度でソートして結果を返す
                query += """
                ORDER BY similarity DESC
                LIMIT %s
                """
                params.append(limit)
                
                # 実行
                cursor.execute(query, params)
                
                # 結果を取得
                results = []
                for row in cursor.fetchall():
                    id_, file_name, image_path, similarity = row
                    if similarity >= threshold:
                        results.append({
                            "id": id_,
                            "file_name": file_name,
                            "image_path": image_path,
                            "similarity": similarity
                        })
                
                return results
                
            except Exception as e:
                logger.error(f"類似検索エラー: {str(e)}")
                return []

if __name__ == "__main__":
    # DBの初期化（テスト用）
    initialize_db()
    logger.info("データベースの初期化が完了しました。") 
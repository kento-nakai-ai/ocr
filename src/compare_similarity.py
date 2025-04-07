#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
エンベディングの類似度比較スクリプト

このスクリプトは、データベースに保存されたエンベディングを使用して
異なる画像間の類似度を計算・比較します。コサイン類似度を使用して
問題間の関連性を分析します。

使用方法:
    python src/compare_similarity.py --query <query_file_name> [--type <embedding_type>] [--limit <n>]

引数:
    --query: 比較元の画像ファイル名
    --type: エンベディングタイプ（デフォルト: image_extracted_text）
    --limit: 表示する類似結果の最大数（デフォルト: 10）
"""

import os
import argparse
import logging
import sys
import numpy as np
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

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

def get_db_connection():
    """データベース接続を取得"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        logger.error(f"DB接続エラー: {str(e)}")
        sys.exit(1)

def get_embedding_by_filename(file_name, embedding_type='image_extracted_text'):
    """
    ファイル名からエンベディングを取得する

    Args:
        file_name (str): 取得するファイル名
        embedding_type (str): エンベディングのタイプ

    Returns:
        dict: エンベディング情報を含む辞書
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            query = """
            SELECT id, file_name, embedding_type, embedding, text_content
            FROM embeddings
            WHERE file_name = %s AND embedding_type = %s
            LIMIT 1;
            """
            
            cursor.execute(query, (file_name, embedding_type))
            result = cursor.fetchone()
            
            if result:
                return dict(result)
            else:
                return None

def find_similar_items(query_embedding, limit=10, threshold=0.7, embedding_type=None, exclude_file_name=None):
    """
    クエリエンベディングに類似したアイテムを検索する

    Args:
        query_embedding (list): 検索クエリのエンベディングベクトル
        limit (int): 取得する結果の最大数
        threshold (float): 類似度の閾値（0-1）
        embedding_type (str): エンベディングタイプでフィルタリング
        exclude_file_name (str): 除外するファイル名

    Returns:
        list: 類似アイテムのリスト
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # クエリの構築
            query = """
            SELECT id, file_name, image_path, text_content, 1 - (embedding <=> %s::vector) AS similarity
            FROM embeddings
            WHERE 1=1
            """
            
            params = [str(query_embedding)]
            
            # エンベディングタイプによるフィルタリング
            if embedding_type:
                query += " AND embedding_type = %s"
                params.append(embedding_type)
            
            # 特定のファイル名を除外
            if exclude_file_name:
                query += " AND file_name != %s"
                params.append(exclude_file_name)
            
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
                if row['similarity'] >= threshold:
                    results.append(dict(row))
            
            return results

def display_similarities(query_file, similar_items):
    """
    類似度の結果を表示する

    Args:
        query_file (dict): クエリファイルの情報
        similar_items (list): 類似アイテムのリスト
    """
    print(f"\n===== 類似度比較: {query_file['file_name']} =====")
    print(f"ID: {query_file['id']}")
    print(f"エンベディングタイプ: {query_file['embedding_type']}")
    print("\n----- 検索元テキスト抜粋 -----")
    print(query_file['text_content'][:300] + "..." if len(query_file['text_content']) > 300 else query_file['text_content'])
    
    print("\n----- 類似度が高い問題 -----")
    for i, item in enumerate(similar_items):
        print(f"\n{i+1}. {item['file_name']} (類似度: {item['similarity']:.4f})")
        print("----- テキスト抜粋 -----")
        print(item['text_content'][:300] + "..." if len(item['text_content']) > 300 else item['text_content'])
        print("-" * 50)

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='エンベディングの類似度比較')
    parser.add_argument('--query', '-q', required=True, help='比較元のファイル名')
    parser.add_argument('--type', '-t', default='image_extracted_text', help='エンベディングタイプ')
    parser.add_argument('--limit', '-l', type=int, default=10, help='表示する類似結果の最大数')
    
    args = parser.parse_args()
    
    try:
        # クエリファイルのエンベディングを取得
        query_file = get_embedding_by_filename(args.query, args.type)
        
        if not query_file:
            logger.error(f"指定されたファイル '{args.query}' が見つかりません。")
            return 1
        
        # 類似アイテムを検索
        query_embedding = query_file['embedding']
        similar_items = find_similar_items(
            query_embedding=query_embedding,
            limit=args.limit,
            embedding_type=args.type,
            exclude_file_name=args.query  # 自分自身を除外
        )
        
        # 結果を表示
        display_similarities(query_file, similar_items)
        
        return 0
        
    except Exception as e:
        logger.error(f"実行中にエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
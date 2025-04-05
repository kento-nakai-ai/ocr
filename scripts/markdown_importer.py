#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Markdownファイルの内容をPostgreSQLデータベースにインポートするスクリプト

このスクリプトは、Markdown形式のファイルを読み込み、PostgreSQLデータベースの
questionsテーブルにインポートします。既存のレコードがある場合はUPDATEし、
なければINSERTします。

要件:
    - psycopg2: PostgreSQL用のPythonアダプタ
    - python-dotenv: 環境変数管理のためのライブラリ

使用例:
    python markdown_importer.py file.md 2025 "Q001"
    python markdown_importer.py --batch folder/ 2025
"""

import os
import argparse
import logging
import glob
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MarkdownImporter:
    """
    Markdownファイルの内容をPostgreSQLデータベースにインポートするクラス
    """
    
    def __init__(self, db_config=None):
        """
        初期化
        
        Args:
            db_config (dict, optional): データベース接続設定
                以下のキーを含む辞書:
                - host: ホスト名
                - port: ポート番号
                - database: データベース名
                - user: ユーザー名
                - password: パスワード
        """
        # 環境変数から設定を読み込む
        load_dotenv()
        
        # 接続設定
        self.db_config = db_config or {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'questions_db'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '')
        }
        
        logger.info(f"データベース接続設定: {self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}")
    
    def get_connection(self):
        """
        データベース接続を取得します
        
        Returns:
            psycopg2.connection: データベース接続オブジェクト
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            logger.error(f"データベース接続エラー: {str(e)}")
            raise
    
    def import_markdown(self, markdown_path, year, question_id):
        """
        Markdownファイルの内容をデータベースにインポートします
        
        Args:
            markdown_path (str): Markdownファイルのパス
            year (str): 年度
            question_id (str): 問題ID
            
        Returns:
            bool: インポートが成功したかどうか
        """
        # ファイルの存在確認
        if not os.path.exists(markdown_path):
            logger.error(f"ファイルが見つかりません: {markdown_path}")
            return False
        
        try:
            # ファイル内容の読み込み
            with open(markdown_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # データベース接続
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # questionsテーブルの存在を確認
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'questions'
                );
            """)
            table_exists = cursor.fetchone()[0]
            
            # テーブルが存在しない場合は作成
            if not table_exists:
                logger.info("questionsテーブルが存在しないため作成します")
                cursor.execute("""
                    CREATE TABLE questions (
                        id VARCHAR(50) PRIMARY KEY,
                        body TEXT NOT NULL,
                        year_list TEXT DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
            
            # 既存レコードの確認
            cursor.execute(
                "SELECT id, year_list FROM questions WHERE id = %s",
                (question_id,)
            )
            existing_record = cursor.fetchone()
            
            if existing_record:
                # 既存の年度リストに年度を追加（重複なし）
                year_list = existing_record[1]
                years = set(year_list.split(',')) if year_list else set()
                years.add(year)
                new_year_list = ','.join(sorted(years))
                
                # UPDATEクエリの実行
                cursor.execute(
                    """
                    UPDATE questions 
                    SET body = %s, year_list = %s, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = %s
                    """,
                    (markdown_content, new_year_list, question_id)
                )
                logger.info(f"レコードを更新しました: {question_id} (年度: {new_year_list})")
            else:
                # INSERTクエリの実行
                cursor.execute(
                    """
                    INSERT INTO questions (id, body, year_list) 
                    VALUES (%s, %s, %s)
                    """,
                    (question_id, markdown_content, year)
                )
                logger.info(f"レコードを挿入しました: {question_id} (年度: {year})")
            
            # コミット
            conn.commit()
            
            # 接続のクローズ
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"インポートエラー: {str(e)}")
            return False
    
    def batch_import(self, folder_path, year):
        """
        フォルダ内のすべてのMarkdownファイルをインポートします
        
        Args:
            folder_path (str): Markdownファイルを含むフォルダのパス
            year (str): 年度
            
        Returns:
            tuple: (成功件数, 失敗件数)
        """
        # フォルダの存在確認
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            logger.error(f"フォルダが見つかりません: {folder_path}")
            return 0, 0
        
        # Markdownファイルのリストを取得
        markdown_files = glob.glob(os.path.join(folder_path, "*.md"))
        total_files = len(markdown_files)
        
        if total_files == 0:
            logger.warning(f"インポート対象のMarkdownファイルが見つかりません: {folder_path}")
            return 0, 0
        
        logger.info(f"バッチインポート開始: {folder_path} ({total_files}ファイル)")
        
        success_count = 0
        failure_count = 0
        
        for file_path in markdown_files:
            file_name = os.path.basename(file_path)
            question_id = os.path.splitext(file_name)[0]
            
            if self.import_markdown(file_path, year, question_id):
                success_count += 1
            else:
                failure_count += 1
                
            logger.info(f"進捗: {success_count+failure_count}/{total_files} (成功: {success_count}, 失敗: {failure_count})")
        
        logger.info(f"バッチインポート完了: 成功={success_count}, 失敗={failure_count}")
        return success_count, failure_count


def main():
    """
    コマンドライン引数を解析し、Markdownインポートを実行
    """
    parser = argparse.ArgumentParser(description='MarkdownファイルをPostgreSQLにインポートします')
    parser.add_argument('path', help='Markdownファイルまたはフォルダのパス')
    parser.add_argument('year', help='年度 (例: 2025)')
    parser.add_argument('question_id', nargs='?', help='問題ID (例: Q001) - バッチモードでは不要')
    parser.add_argument('--batch', '-b', action='store_true', help='バッチモード (フォルダ内の全ファイルを処理)')
    parser.add_argument('--host', help='データベースホスト')
    parser.add_argument('--port', help='データベースポート')
    parser.add_argument('--dbname', help='データベース名')
    parser.add_argument('--user', help='データベースユーザー')
    parser.add_argument('--password', help='データベースパスワード')
    
    args = parser.parse_args()
    
    # DB設定の準備
    db_config = {}
    if args.host:
        db_config['host'] = args.host
    if args.port:
        db_config['port'] = args.port
    if args.dbname:
        db_config['database'] = args.dbname
    if args.user:
        db_config['user'] = args.user
    if args.password:
        db_config['password'] = args.password
    
    # インポーターの初期化
    importer = MarkdownImporter(db_config)
    
    # バッチモードかどうかで処理を分岐
    if args.batch or os.path.isdir(args.path):
        importer.batch_import(args.path, args.year)
    else:
        if not args.question_id:
            logger.error("単一ファイルモードでは問題IDが必要です")
            return
        
        importer.import_markdown(args.path, args.year, args.question_id)


if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Markdownファイルをデータベースにインポートするスクリプト

このスクリプトは、Markdown形式のファイルをPostgreSQL（またはAurora）
データベースにインポートします。問題文や年度、問題IDなどのメタデータを
questionsテーブルに格納します。

仕様:
- 入力: Markdownファイル
- 出力: PostgreSQLデータベースへのインポート
- テーブル: questions（問題テキスト、年度、問題ID等を格納）

制限事項:
- データベーステーブルが事前に作成されている必要があります
- .envファイルにデータベース接続情報が設定されている必要があります
"""

import os
import argparse
import logging
import re
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

class MarkdownImporter:
    """
    Markdownファイルをデータベースにインポートするクラス
    
    @param {string} input_path - 入力Markdownファイルまたはディレクトリのパス
    @param {number} year - 問題の年度
    @param {string} question_prefix - 問題IDのプレフィックス
    @param {boolean} create_table - テーブルが存在しない場合に作成するかどうか
    """
    def __init__(self, input_path, year=None, question_prefix="Q", create_table=True):
        self.input_path = input_path
        self.year = year
        self.question_prefix = question_prefix
        self.create_table = create_table
        self.logger = logging.getLogger(__name__)
        
        # DBの接続情報を環境変数から取得
        self.db_host = os.getenv('DB_HOST', 'localhost')
        self.db_port = os.getenv('DB_PORT', '5432')
        self.db_name = os.getenv('DB_NAME', 'questions_db')
        self.db_user = os.getenv('DB_USER', 'postgres')
        self.db_password = os.getenv('DB_PASSWORD', '')
        
        # データベース接続を初期化
        self.conn = None
    
    def connect_db(self):
        """
        データベースに接続
        
        @return {Connection} データベース接続オブジェクト
        """
        try:
            self.logger.info(f"データベースに接続: {self.db_host}:{self.db_port}/{self.db_name}")
            
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                dbname=self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            
            self.logger.info("データベース接続成功")
            return conn
            
        except Exception as e:
            self.logger.error(f"データベース接続エラー: {str(e)}")
            raise
    
    def create_questions_table(self):
        """
        questionsテーブルを作成（存在しない場合）
        """
        if not self.create_table:
            return
            
        try:
            cursor = self.conn.cursor()
            
            # questionsテーブルの作成
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id SERIAL PRIMARY KEY,
                    question_id VARCHAR(50) UNIQUE NOT NULL,
                    year INTEGER,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 既にベクトル型の拡張機能がある場合は、embeddings用のテーブルも作成
            try:
                # まずpgvector拡張が存在するか確認
                cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                extension_exists = cursor.fetchone()
                
                if extension_exists:
                    # pgvector拡張が存在する場合はembeddingsテーブル作成
                    self.logger.info("pgvector拡張が検出されました。embeddingsテーブルを作成します。")
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS embeddings (
                            id SERIAL PRIMARY KEY,
                            question_id VARCHAR(50) REFERENCES questions(question_id),
                            embedding vector(1536),
                            metadata JSONB,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # インデックス作成
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS embeddings_question_id_idx 
                        ON embeddings (question_id)
                    """)
                    
                    # ベクトル検索用インデックス
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS embeddings_vector_idx 
                        ON embeddings USING ivfflat (embedding vector_l2_ops)
                    """)
            except:
                self.logger.warning("pgvector拡張が存在しないか、テーブル作成に失敗しました。embeddingsテーブルはスキップします。")
            
            self.conn.commit()
            self.logger.info("テーブル作成完了")
            
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"テーブル作成エラー: {str(e)}")
            raise
    
    def extract_question_number(self, filename):
        """
        ファイル名から問題番号を抽出
        
        @param {string} filename - ファイル名
        @return {string} 問題番号
        """
        # ファイル名から問題番号を抽出する正規表現
        # 例: sample_page_001.md → 001
        match = re.search(r'_page_(\d+)', filename)
        if match:
            return match.group(1)
        
        # 他のパターン: question_001.md → 001
        match = re.search(r'[_-](\d+)', filename)
        if match:
            return match.group(1)
        
        # 数字だけの場合: 001.md → 001
        match = re.search(r'^(\d+)', filename)
        if match:
            return match.group(1)
        
        # どのパターンにも一致しない場合は000を返す
        return "000"
    
    def insert_markdown(self, file_path, year=None, question_id=None):
        """
        Markdownファイルをデータベースに挿入
        
        @param {string} file_path - Markdownファイルのパス
        @param {number} year - 問題の年度（指定がない場合はインスタンス変数を使用）
        @param {string} question_id - 問題ID（指定がない場合はファイル名から生成）
        @return {boolean} 挿入が成功したかどうか
        """
        try:
            # 年度の設定
            if year is None:
                year = self.year
            
            # 問題IDの生成
            if question_id is None:
                # ファイル名から問題番号を抽出
                file_name = os.path.basename(file_path)
                question_number = self.extract_question_number(file_name)
                
                # 問題IDを生成（例: Q001）
                question_id = f"{self.question_prefix}{question_number.zfill(3)}"
            
            # Markdownファイルの内容を読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # データベースにINSERT
            cursor = self.conn.cursor()
            
            # UPSERT（INSERT または UPDATE）
            cursor.execute("""
                INSERT INTO questions (question_id, year, content)
                VALUES (%s, %s, %s)
                ON CONFLICT (question_id) 
                DO UPDATE SET 
                    year = EXCLUDED.year,
                    content = EXCLUDED.content,
                    updated_at = CURRENT_TIMESTAMP
            """, (question_id, year, content))
            
            self.conn.commit()
            self.logger.info(f"挿入完了: 問題ID={question_id}, 年度={year}, ファイル={file_path}")
            return True
            
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"データ挿入エラー（{file_path}）: {str(e)}")
            return False
    
    def import_files(self):
        """
        指定されたパスからMarkdownファイルをインポート
        
        @return {dict} 処理結果の統計情報
        """
        try:
            # データベースに接続
            self.conn = self.connect_db()
            
            # テーブルが存在しない場合は作成
            self.create_questions_table()
            
            # 結果カウンター
            results = {
                'success': 0,
                'failure': 0,
                'total': 0
            }
            
            if os.path.isfile(self.input_path):
                # 単一ファイルの場合
                success = self.insert_markdown(self.input_path)
                results['total'] = 1
                if success:
                    results['success'] = 1
                else:
                    results['failure'] = 1
                    
            elif os.path.isdir(self.input_path):
                # ディレクトリの場合
                input_dir = Path(self.input_path)
                
                # Markdownファイルのみを対象とする
                md_files = [f for f in input_dir.glob('*.md')]
                results['total'] = len(md_files)
                
                for md_file in sorted(md_files):
                    self.logger.info(f"処理中: {md_file}")
                    success = self.insert_markdown(str(md_file))
                    if success:
                        results['success'] += 1
                    else:
                        results['failure'] += 1
                        
            else:
                self.logger.error(f"入力パスが見つかりません: {self.input_path}")
            
            # データベース接続を閉じる
            self.conn.close()
            
            self.logger.info(f"インポート完了: 成功={results['success']}, 失敗={results['failure']}, 合計={results['total']}")
            return results
            
        except Exception as e:
            if self.conn:
                self.conn.close()
            self.logger.error(f"インポート処理でエラーが発生しました: {str(e)}")
            raise


def main():
    """メイン関数"""
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='MarkdownファイルをDB（PostgreSQL/Aurora）にインポート')
    parser.add_argument('input', help='入力Markdownファイルまたはディレクトリのパス')
    parser.add_argument('--year', '-y', type=int, help='問題の年度（例: 2024）')
    parser.add_argument('--prefix', '-p', default='Q', help='問題IDのプレフィックス（デフォルト: Q）')
    parser.add_argument('--question-id', '-q', help='問題ID（指定時は年度とプレフィックスは無視）')
    parser.add_argument('--no-create-table', action='store_true', help='テーブルを自動作成しない')
    parser.add_argument('--batch', '-b', action='store_true', help='バッチモードで実行（ディレクトリ内の全ファイルを処理）')
    
    args = parser.parse_args()
    
    try:
        # バッチモードの場合は入力をディレクトリとして扱う
        if args.batch and not os.path.isdir(args.input):
            logger.error(f"バッチモードではディレクトリを指定してください: {args.input}")
            return 1
        
        # 単一ファイル+問題ID指定の場合
        if not args.batch and os.path.isfile(args.input) and args.question_id:
            # 単一ファイルのインポート
            importer = MarkdownImporter(
                input_path=args.input,
                year=args.year,
                question_prefix=args.prefix,
                create_table=not args.no_create_table
            )
            
            # データベースに接続
            conn = importer.connect_db()
            importer.conn = conn
            
            # テーブルの作成
            importer.create_questions_table()
            
            # ファイルのインポート
            success = importer.insert_markdown(
                file_path=args.input,
                year=args.year,
                question_id=args.question_id
            )
            
            # 接続を閉じる
            conn.close()
            
            if success:
                logger.info(f"ファイルを正常にインポートしました: {args.input} → 問題ID: {args.question_id}")
                return 0
            else:
                logger.error(f"ファイルのインポートに失敗しました: {args.input}")
                return 1
        
        else:
            # 通常のインポート処理
            importer = MarkdownImporter(
                input_path=args.input,
                year=args.year,
                question_prefix=args.prefix,
                create_table=not args.no_create_table
            )
            
            results = importer.import_files()
            
            if results['failure'] > 0:
                logger.warning(f"一部のファイルのインポートに失敗しました: 失敗={results['failure']}/{results['total']}")
                return 1 if results['success'] == 0 else 0
            else:
                logger.info(f"全てのファイルが正常にインポートされました: {results['success']}/{results['total']}")
                return 0
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main()) 
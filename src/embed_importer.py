#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
エンベディングデータをデータベースにインポートするスクリプト

このスクリプトは、エンベディング（埋め込みベクトル）データを
PostgreSQL/Auroraデータベースにインポートします。pgvector拡張を使用して
ベクトルデータを格納し、後でベクトル類似度検索を行えるようにします。

仕様:
- 入力: .npy形式のエンベディングファイル
- 出力: PostgreSQL/Auroraデータベースへのインポート
- テーブル: embeddings（エンベディング、問題ID、メタデータを格納）

制限事項:
- pgvector拡張がデータベースにインストールされている必要があります
- .envファイルにデータベース接続情報が設定されている必要があります
"""

import os
import argparse
import logging
import json
import glob
from pathlib import Path
import numpy as np
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

class EmbeddingImporter:
    """
    エンベディングデータをデータベースにインポートするクラス
    
    @param {string} input_path - 入力エンベディングファイルまたはディレクトリのパス
    @param {string} table_name - 格納先テーブル名
    @param {boolean} create_table - テーブルが存在しない場合に作成するかどうか
    @param {string} question_table - 問題テーブル名（問題IDの参照先）
    """
    def __init__(self, input_path, table_name="embeddings", create_table=True, question_table="questions"):
        self.input_path = input_path
        self.table_name = table_name
        self.create_table = create_table
        self.question_table = question_table
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
    
    def check_pgvector_extension(self):
        """
        pgvector拡張がインストールされているか確認
        
        @return {boolean} pgvector拡張が利用可能かどうか
        """
        try:
            cursor = self.conn.cursor()
            
            # pgvector拡張が存在するか確認
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            result = cursor.fetchone()
            
            if result:
                self.logger.info("pgvector拡張が利用可能です")
                return True
            else:
                self.logger.warning("pgvector拡張がインストールされていません")
                
                # 拡張のインストールを試みる
                try:
                    self.logger.info("pgvector拡張のインストールを試みます...")
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    self.conn.commit()
                    self.logger.info("pgvector拡張をインストールしました")
                    return True
                except Exception as e:
                    self.logger.error(f"pgvector拡張のインストールに失敗しました: {str(e)}")
                    return False
                
        except Exception as e:
            self.logger.error(f"pgvector拡張の確認中にエラーが発生しました: {str(e)}")
            return False
    
    def create_embeddings_table(self):
        """
        embeddingsテーブルを作成（存在しない場合）
        
        @return {boolean} テーブル作成が成功したかどうか
        """
        if not self.create_table:
            return True
            
        try:
            cursor = self.conn.cursor()
            
            # pgvector拡張が利用可能か確認
            if not self.check_pgvector_extension():
                self.logger.error("pgvector拡張が利用できないため、テーブルを作成できません")
                return False
            
            # エンベディングの次元数を推定
            if os.path.isdir(self.input_path):
                # ディレクトリ内の最初のnpyファイルを探す
                embedding_files = list(Path(self.input_path).glob('**/*_embedding.npy'))
                if not embedding_files and os.path.isdir(self.input_path):
                    embedding_files = list(Path(self.input_path).glob('**/*.npy'))
                
                if embedding_files:
                    # 最初のファイルから次元数を取得
                    sample_embedding = np.load(str(embedding_files[0]))
                    if sample_embedding.ndim > 1:
                        sample_embedding = sample_embedding[0]
                    embedding_dim = len(sample_embedding)
                    self.logger.info(f"エンベディングの次元数を検出: {embedding_dim}")
                else:
                    # デフォルト値を使用
                    embedding_dim = 1536
                    self.logger.warning(f"エンベディングファイルが見つかりません。デフォルトの次元数を使用: {embedding_dim}")
            else:
                # 単一ファイル
                if os.path.isfile(self.input_path) and self.input_path.lower().endswith('.npy'):
                    sample_embedding = np.load(self.input_path)
                    if sample_embedding.ndim > 1:
                        sample_embedding = sample_embedding[0]
                    embedding_dim = len(sample_embedding)
                    self.logger.info(f"エンベディングの次元数を検出: {embedding_dim}")
                else:
                    # デフォルト値を使用
                    embedding_dim = 1536
                    self.logger.warning(f"有効なエンベディングファイルではありません。デフォルトの次元数を使用: {embedding_dim}")
            
            # embeddingsテーブルの作成
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id SERIAL PRIMARY KEY,
                    question_id VARCHAR(50) REFERENCES {self.question_table}(question_id),
                    embedding_type VARCHAR(50) NOT NULL,
                    embedding vector({embedding_dim}),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # インデックス作成
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_question_id_idx 
                ON {self.table_name} (question_id)
            """)
            
            # ベクトル検索用インデックス
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_vector_idx 
                ON {self.table_name} USING ivfflat (embedding vector_l2_ops)
            """)
            
            self.conn.commit()
            self.logger.info(f"{self.table_name}テーブルを作成しました")
            return True
            
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"テーブル作成エラー: {str(e)}")
            return False
    
    def extract_question_id(self, file_name):
        """
        ファイル名から問題IDを抽出または生成
        
        @param {string} file_name - エンベディングファイル名（拡張子なし）
        @return {string} 問題ID
        """
        # エンベディング形式: filename_embedding.npy → filename
        # Geminiの場合: filename_analysis.json, filename_embedding.npy → filename
        
        # "_embedding"サフィックスがある場合は除去
        if file_name.endswith("_embedding"):
            file_name = file_name[:-10]
        
        # データベースから問題IDの一覧を取得
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT question_id FROM {self.question_table}")
        question_ids = [row[0] for row in cursor.fetchall()]
        
        # 完全一致する問題IDがあれば、それを返す
        if file_name in question_ids:
            return file_name
        
        # プレフィックス+数字の形式の問題IDパターンと照合
        # 例: Q001, PROB123 など
        import re
        pattern = r"^([A-Za-z]+)(\d+)$"
        match = re.match(pattern, file_name)
        
        if match:
            prefix, number = match.groups()
            return f"{prefix}{number}"
        
        # ページ番号パターンと照合（例: sample_page_001 → Q001）
        page_pattern = r".*_page_(\d+)"
        page_match = re.match(page_pattern, file_name)
        
        if page_match:
            page_num = page_match.group(1)
            question_id = f"Q{page_num}"
            
            # 該当する問題IDが存在するか確認
            if question_id in question_ids:
                return question_id
        
        # どのパターンにも一致しない場合はファイル名をそのまま返す
        return file_name
    
    def load_metadata(self, file_name):
        """
        エンベディングに関連するメタデータの読み込み
        
        @param {string} file_name - エンベディングファイル名（拡張子なし）
        @return {dict} メタデータ辞書
        """
        # 関連するJSONファイルのパスを生成
        base_dir = os.path.dirname(self.input_path) if os.path.isfile(self.input_path) else self.input_path
        
        # "filename_embedding.npy"に対応する"filename_analysis.json"を探す
        if file_name.endswith("_embedding"):
            base_name = file_name[:-10]
        else:
            base_name = file_name
            
        json_path = os.path.join(base_dir, f"{base_name}_analysis.json")
        
        # JSONファイルがあれば読み込む
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"メタデータファイルの読み込みに失敗しました: {json_path} - {str(e)}")
                return {}
        
        # JSONファイルがなければ空のメタデータを返す
        return {}
    
    def import_embedding(self, file_path, question_id=None):
        """
        単一エンベディングファイルをデータベースにインポート
        
        @param {string} file_path - エンベディングファイルのパス
        @param {string} question_id - 問題ID（指定がない場合はファイル名から抽出）
        @return {boolean} インポートが成功したかどうか
        """
        try:
            # エンベディングファイルの読み込み
            embedding = np.load(file_path)
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # 問題IDの取得または生成
            if question_id is None:
                question_id = self.extract_question_id(file_name)
            
            # メタデータの読み込み
            metadata = self.load_metadata(file_name)
            
            # エンベディングの次元数とサイズを確認
            if embedding.ndim > 1:
                # 多次元配列の場合は最初の次元を使用
                self.logger.warning(f"多次元エンベディングが検出されました: {embedding.shape} - 最初の次元を使用します")
                embedding = embedding[0]
            
            # エンベディングをデータベースに挿入
            cursor = self.conn.cursor()
            
            # まず同じquestion_idのエンベディングを削除（UPSERT的動作）
            cursor.execute(f"""
                DELETE FROM {self.table_name}
                WHERE question_id = %s
            """, (question_id,))
            
            # 新しいエンベディングを挿入
            cursor.execute(f"""
                INSERT INTO {self.table_name} (question_id, embedding_type, embedding, metadata)
                VALUES (%s, %s, %s, %s)
            """, (
                question_id,
                "text",  # デフォルトのembedding_type値を設定
                embedding.tolist(),  # pgvector用にリスト形式に変換
                Json(metadata) if metadata else None
            ))
            
            self.conn.commit()
            self.logger.info(f"エンベディングを挿入しました: {file_path} → 問題ID: {question_id}")
            return True
            
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"エンベディングのインポートに失敗しました（{file_path}）: {str(e)}")
            return False
    
    def import_embeddings(self):
        """
        エンベディングファイルをデータベースにインポート
        
        @return {dict} 処理結果の統計情報
        """
        try:
            # データベースに接続
            self.conn = self.connect_db()
            
            # テーブルが存在しない場合は作成
            if not self.create_embeddings_table():
                self.logger.error("テーブルの作成に失敗しました。処理を中止します。")
                if self.conn:
                    self.conn.close()
                return {'success': 0, 'failure': 0, 'total': 0}
            
            # 結果カウンター
            results = {
                'success': 0,
                'failure': 0,
                'total': 0
            }
            
            if os.path.isfile(self.input_path):
                # 単一ファイルの場合
                if self.input_path.lower().endswith('.npy'):
                    success = self.import_embedding(self.input_path)
                    results['total'] = 1
                    if success:
                        results['success'] = 1
                    else:
                        results['failure'] = 1
                else:
                    self.logger.error(f"サポートされていないファイル形式です: {self.input_path}")
                    results['total'] = 1
                    results['failure'] = 1
                    
            elif os.path.isdir(self.input_path):
                # ディレクトリの場合
                # .npy形式のエンベディングファイルを検索
                embedding_files = list(Path(self.input_path).glob('**/*_embedding.npy'))
                if not embedding_files:
                    # 通常のnpyファイルも検索
                    embedding_files = list(Path(self.input_path).glob('**/*.npy'))
                
                results['total'] = len(embedding_files)
                
                for emb_file in sorted(embedding_files):
                    self.logger.info(f"処理中: {emb_file}")
                    success = self.import_embedding(str(emb_file))
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
    parser = argparse.ArgumentParser(description='エンベディングデータをデータベースにインポート')
    parser.add_argument('--input', '-i', required=True, help='入力エンベディングファイルまたはディレクトリのパス')
    parser.add_argument('--table', '-t', default='embeddings', help='格納先テーブル名（デフォルト: embeddings）')
    parser.add_argument('--question-table', '-q', default='questions', help='問題テーブル名（デフォルト: questions）')
    parser.add_argument('--question-id', '-qid', help='問題ID（単一ファイル処理時にのみ有効）')
    parser.add_argument('--no-create-table', action='store_true', help='テーブルを自動作成しない')
    
    args = parser.parse_args()
    
    try:
        # 入力パスの確認
        if not os.path.exists(args.input):
            logger.error(f"入力パスが存在しません: {args.input}")
            return 1
        
        # 単一ファイル+問題ID指定の場合
        if os.path.isfile(args.input) and args.question_id:
            # インポーターの初期化
            importer = EmbeddingImporter(
                input_path=args.input,
                table_name=args.table,
                create_table=not args.no_create_table,
                question_table=args.question_table
            )
            
            # データベースに接続
            conn = importer.connect_db()
            importer.conn = conn
            
            # テーブルの作成
            if not importer.create_embeddings_table():
                logger.error("テーブルの作成に失敗しました。処理を中止します。")
                conn.close()
                return 1
            
            # ファイルのインポート
            success = importer.import_embedding(
                file_path=args.input,
                question_id=args.question_id
            )
            
            # 接続を閉じる
            conn.close()
            
            if success:
                logger.info(f"エンベディングを正常にインポートしました: {args.input} → 問題ID: {args.question_id}")
                return 0
            else:
                logger.error(f"エンベディングのインポートに失敗しました: {args.input}")
                return 1
        
        else:
            # 通常のインポート処理
            importer = EmbeddingImporter(
                input_path=args.input,
                table_name=args.table,
                create_table=not args.no_create_table,
                question_table=args.question_table
            )
            
            results = importer.import_embeddings()
            
            if results['failure'] > 0:
                logger.warning(f"一部のエンベディングのインポートに失敗しました: 失敗={results['failure']}/{results['total']}")
                return 1 if results['success'] == 0 else 0
            else:
                if results['success'] > 0:
                    logger.info(f"全てのエンベディングが正常にインポートされました: {results['success']}/{results['total']}")
                    return 0
                else:
                    logger.warning("インポートするエンベディングがありませんでした")
                    return 0
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main()) 
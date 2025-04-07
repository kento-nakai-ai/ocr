#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
JSONファイルからnumpyエンベディングファイルを生成するスクリプト

このスクリプトは、Claude APIやGemini APIによる画像解析の結果JSONファイルから
エンベディングベクトルを生成し、.npy形式で保存します。
Gemini APIを使用して実際のエンベディングを取得するように実装されています。
"""

import os
import argparse
import json
import logging
import glob
import numpy as np
import requests
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import datetime

# 環境変数の読み込み
load_dotenv()

# ロギング設定
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_gemini_embedding(text, api_key=None, retry_count=3):
    """
    Gemini APIを使用してテキストのエンベディングを取得する
    
    Args:
        text (str): エンベディングを取得するテキスト
        api_key (str): Gemini APIキー。未指定の場合は環境変数から読み込む
        retry_count (int): 失敗時の再試行回数
        
    Returns:
        numpy.ndarray: エンベディングベクトル。失敗時はNone
    """
    # APIキーの取得
    api_key = api_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEYが設定されていません。")
        return None
    
    # APIエンドポイントとヘッダー
    embedding_api_url = "https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    
    # リクエストデータ
    data = {
        "model": "embedding-001",
        "content": {
            "parts": [
                {"text": text}
            ]
        }
    }
    
    # リトライループ
    for attempt in range(retry_count):
        try:
            # APIリクエスト送信
            response = requests.post(
                embedding_api_url,
                headers=headers,
                json=data
            )
            
            # レスポンスチェック
            if response.status_code != 200:
                logger.error(f"Gemini API エラー ({attempt+1}/{retry_count}): {response.status_code} {response.text}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)  # 指数バックオフ
                    continue
                else:
                    return None
            
            # レスポンスを解析
            embedding_json = response.json()
            
            if "embedding" not in embedding_json or "values" not in embedding_json["embedding"]:
                logger.error(f"Gemini API レスポンスに有効なデータがありません: {embedding_json}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return None
            
            # エンベディング値を取得
            embedding = np.array(embedding_json["embedding"]["values"], dtype=np.float32)
            return embedding
            
        except Exception as e:
            logger.error(f"Gemini API処理中にエラーが発生しました ({attempt+1}/{retry_count}): {str(e)}")
            if attempt < retry_count - 1:
                time.sleep(2 ** attempt)
            else:
                return None
    
    return None

def process_file(json_path, embedding_dim=1536, use_api=True, api_key=None, direct_db=False):
    """
    単一のJSONファイルからエンベディングを生成して保存する
    
    Args:
        json_path (str): 処理するJSONファイルのパス
        embedding_dim (int): 生成するエンベディングの次元数
        use_api (bool): Gemini APIを使用するかどうか
        api_key (str): Gemini APIキー
        direct_db (bool): エンベディングを直接DBに保存するかどうか
        
    Returns:
        bool: 処理成功ならTrue、失敗ならFalse
    """
    try:
        # 出力ファイル名を生成（.jsonを.npyに置き換え）
        base_name = os.path.splitext(json_path)[0]
        if base_name.endswith('_analysis'):
            base_name = base_name[:-9]
        npy_path = f"{base_name}_embedding.npy"
        
        # JSONファイルを読み込む
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # テキスト内容を取得
        text_content = data.get('text_content', '')
        
        if not text_content:
            logger.warning(f"JSONファイルにテキスト内容がありません: {json_path}")
            return False
        
        # エンベディングの取得
        embedding = None
        
        if use_api:
            # Gemini APIを使用してエンベディングを取得
            logger.info(f"Gemini APIを使用してエンベディングを取得: {json_path}")
            embedding = get_gemini_embedding(text_content, api_key)
            
            if embedding is None:
                logger.error(f"エンベディングの取得に失敗しました。ダミーエンベディングを生成します: {json_path}")
                # APIが失敗した場合はダミーエンベディングを使用
                use_api = False
        
        if not use_api:
            # ダミーのエンベディングを生成
            logger.info(f"ダミーエンベディングを生成: {json_path}")
            text_length = min(len(text_content), 100) if text_content else 50
            seed = hash(text_content) % 10000 if text_content else 42
            np.random.seed(seed)
            
            embedding = np.random.normal(0, 1/np.sqrt(embedding_dim), embedding_dim)
            embedding = embedding / np.linalg.norm(embedding)  # 正規化
        
        # エンベディングをDBに直接保存する場合
        if direct_db:
            try:
                from src.db_utils import save_embedding_to_db
                
                # ファイル名を取得
                file_name = os.path.basename(base_name)
                
                # 画像パスを取得（JSONファイルから）
                image_path = data.get('image_path', '')
                
                # メタデータを取得（JSONファイルから）
                metadata = {
                    "source_json": json_path,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                
                # 問題情報がある場合はメタデータに追加
                problems_data = None
                if '```json' in text_content and '```' in text_content:
                    try:
                        json_part = text_content.split('```json')[1].split('```')[0].strip()
                        problems_data = json.loads(json_part)
                        metadata["problems"] = problems_data
                    except:
                        pass
                
                # DBに保存
                result_id = save_embedding_to_db(
                    file_name=file_name,
                    embedding_array=embedding,
                    embedding_type="text",
                    image_path=image_path,
                    text_content=text_content,
                    metadata=metadata
                )
                
                if result_id > 0:
                    logger.info(f"エンベディングをDBに保存しました: {file_name}, ID={result_id}")
                else:
                    logger.error(f"エンベディングのDB保存に失敗しました: {file_name}")
                    # 失敗した場合はnpyファイルとして保存する
                    np.save(npy_path, embedding)
                    logger.info(f"代わりにnpyファイルとして保存しました: {npy_path}")
            
            except Exception as e:
                logger.error(f"DB保存中にエラーが発生しました: {str(e)}")
                # エラーが発生した場合はnpyファイルとして保存
                np.save(npy_path, embedding)
                logger.info(f"代わりにnpyファイルとして保存しました: {npy_path}")
        else:
            # numpyファイルとして保存
            np.save(npy_path, embedding)
            logger.info(f"エンベディングを生成しました: {json_path} → {npy_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"ファイル処理エラー ({json_path}): {str(e)}")
        return False

def process_directory(directory_path, max_workers=4, embedding_dim=1536, use_api=True, api_key=None, direct_db=False):
    """
    ディレクトリ内のすべてのJSONファイルを処理
    
    Args:
        directory_path (str): 処理するディレクトリのパス
        max_workers (int): 並列処理のワーカー数
        embedding_dim (int): 生成するエンベディングの次元数
        use_api (bool): Gemini APIを使用するかどうか
        api_key (str): Gemini APIキー
        direct_db (bool): エンベディングを直接DBに保存するかどうか
        
    Returns:
        tuple: (成功件数, 失敗件数)
    """
    # 分析結果のJSONファイルを検索
    json_files = list(Path(directory_path).glob('**/*_analysis.json'))
    total_files = len(json_files)
    
    if total_files == 0:
        logger.warning(f"処理対象のJSONファイルが見つかりません: {directory_path}")
        return 0, 0
    
    logger.info(f"ディレクトリ処理を開始: {directory_path} ({total_files}ファイル)")
    
    # 並列処理でファイルを処理
    success_count = 0
    failure_count = 0
    
    # APIを使用する場合はレート制限を考慮して並行数を制限
    if use_api:
        effective_workers = min(max_workers, 2)  # APIを使う場合は並行数を抑える
        logger.info(f"APIを使用するため、並列処理数を{effective_workers}に制限します")
    else:
        effective_workers = max_workers
    
    with ThreadPoolExecutor(max_workers=effective_workers) as executor:
        # すべてのファイルに対して処理を実行
        futures = {}
        
        for json_file in json_files:
            future = executor.submit(
                process_file, 
                str(json_file), 
                embedding_dim,
                use_api,
                api_key,
                direct_db
            )
            futures[future] = str(json_file)
        
        # 結果を収集
        for i, future in enumerate(futures):
            json_file = futures[future]
            try:
                success = future.result()
                if success:
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                logger.error(f"処理失敗 ({json_file}): {str(e)}")
                failure_count += 1
            
            # 進捗状況を表示
            if (i + 1) % 10 == 0 or (i + 1) == total_files:
                logger.info(f"進捗: {i + 1}/{total_files} (成功: {success_count}, 失敗: {failure_count})")
    
    logger.info(f"ディレクトリ処理完了: 成功={success_count}, 失敗={failure_count}")
    return success_count, failure_count

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='JSONファイルからnumpyエンベディングファイルを生成')
    parser.add_argument('--input', '-i', required=True, help='入力JSONファイルまたはディレクトリのパス')
    parser.add_argument('--dimension', '-d', type=int, default=1536, help='エンベディングの次元数（デフォルト: 1536）')
    parser.add_argument('--parallel', '-p', type=int, default=4, help='並列処理数（デフォルト: 4）')
    parser.add_argument('--api-key', help='Gemini APIキー（指定しない場合は環境変数から取得）')
    parser.add_argument('--no-api', action='store_true', help='Gemini APIを使用せず、ダミーエンベディングを生成する')
    parser.add_argument('--direct-db', action='store_true', help='エンベディングを直接DBに保存する')
    parser.add_argument('--initialize-db', action='store_true', help='DBを初期化する（pgvector拡張のインストールとテーブル作成）')
    
    args = parser.parse_args()
    
    try:
        # DBの初期化が必要な場合
        if args.initialize_db:
            try:
                from src.db_utils import initialize_db
                initialize_db()
                logger.info("データベースの初期化が完了しました。")
            except Exception as e:
                logger.error(f"データベース初期化中にエラーが発生しました: {str(e)}")
                return 1
        
        # 入力パスの確認
        if not os.path.exists(args.input):
            logger.error(f"入力パスが存在しません: {args.input}")
            return 1
        
        # APIキーの確認
        use_api = not args.no_api
        api_key = args.api_key or os.getenv('GEMINI_API_KEY')
        
        if use_api and not api_key:
            logger.warning("Gemini APIキーが設定されていません。ダミーエンベディングを生成します。")
            logger.warning(".envファイルまたは--api-keyオプションでGEMINI_API_KEYを設定してください。")
            use_api = False
        
        # 単一ファイルかディレクトリかの判定
        if os.path.isfile(args.input):
            if args.input.lower().endswith('_analysis.json'):
                success = process_file(
                    args.input, 
                    args.dimension,
                    use_api,
                    api_key,
                    args.direct_db
                )
                return 0 if success else 1
            else:
                logger.error(f"サポートされていないファイル形式です: {args.input}")
                return 1
                
        elif os.path.isdir(args.input):
            success_count, failure_count = process_directory(
                args.input, 
                max_workers=args.parallel,
                embedding_dim=args.dimension,
                use_api=use_api,
                api_key=api_key,
                direct_db=args.direct_db
            )
            
            return 0 if success_count > 0 else 1
            
        else:
            logger.error(f"無効な入力パスです: {args.input}")
            return 1
            
    except Exception as e:
        logger.error(f"実行中にエラーが発生しました: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main()) 
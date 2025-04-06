#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
JSONファイルからnumpyエンベディングファイルを生成するスクリプト

このスクリプトは、Claude APIによる画像解析の結果JSONファイルから
ダミーのエンベディングベクトルを生成し、.npy形式で保存します。
実際のシステムでは、APIから真のエンベディングを取得することを想定しています。
"""

import os
import argparse
import json
import logging
import glob
import numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# ロギング設定
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_file(json_path, embedding_dim=1536):
    """
    単一のJSONファイルからエンベディングを生成して保存する
    
    Args:
        json_path (str): 処理するJSONファイルのパス
        embedding_dim (int): 生成するエンベディングの次元数
        
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
        
        # 実際のアプリケーションでは、以下のようにAPIを呼び出して
        # テキストからエンベディングを取得する
        # embedding = api.get_embedding(text_content)
        
        # ここではダミーのエンベディングを生成（文字列の長さを使用）
        # 実際のアプリケーションでは、これをAPIからの真のエンベディングに置き換える
        text_length = min(len(text_content), 100) if text_content else 50
        seed = hash(text_content) % 10000 if text_content else 42
        np.random.seed(seed)
        
        # ダミーのエンベディングベクトルを生成
        embedding = np.random.normal(0, 1/np.sqrt(embedding_dim), embedding_dim)
        embedding = embedding / np.linalg.norm(embedding)  # 正規化
        
        # numpyファイルとして保存
        np.save(npy_path, embedding)
        logger.info(f"エンベディングを生成しました: {json_path} → {npy_path}")
        return True
        
    except Exception as e:
        logger.error(f"ファイル処理エラー ({json_path}): {str(e)}")
        return False

def process_directory(directory_path, max_workers=4, embedding_dim=1536):
    """
    ディレクトリ内のすべてのJSONファイルを処理
    
    Args:
        directory_path (str): 処理するディレクトリのパス
        max_workers (int): 並列処理のワーカー数
        embedding_dim (int): 生成するエンベディングの次元数
        
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
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # すべてのファイルに対して処理を実行
        for success in executor.map(lambda f: process_file(str(f), embedding_dim), json_files):
            if success:
                success_count += 1
            else:
                failure_count += 1
                
            # 進捗状況を表示
            if (success_count + failure_count) % 10 == 0 or (success_count + failure_count) == total_files:
                logger.info(f"進捗: {success_count + failure_count}/{total_files} (成功: {success_count}, 失敗: {failure_count})")
    
    logger.info(f"ディレクトリ処理完了: 成功={success_count}, 失敗={failure_count}")
    return success_count, failure_count

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='JSONファイルからnumpyエンベディングファイルを生成')
    parser.add_argument('--input', '-i', required=True, help='入力JSONファイルまたはディレクトリのパス')
    parser.add_argument('--dimension', '-d', type=int, default=1536, help='エンベディングの次元数（デフォルト: 1536）')
    parser.add_argument('--parallel', '-p', type=int, default=4, help='並列処理数（デフォルト: 4）')
    
    args = parser.parse_args()
    
    try:
        # 入力パスの確認
        if not os.path.exists(args.input):
            logger.error(f"入力パスが存在しません: {args.input}")
            return 1
        
        # 単一ファイルかディレクトリかの判定
        if os.path.isfile(args.input):
            if args.input.lower().endswith('_analysis.json'):
                success = process_file(args.input, args.dimension)
                return 0 if success else 1
            else:
                logger.error(f"サポートされていないファイル形式です: {args.input}")
                return 1
                
        elif os.path.isdir(args.input):
            success_count, failure_count = process_directory(
                args.input, 
                max_workers=args.parallel,
                embedding_dim=args.dimension
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
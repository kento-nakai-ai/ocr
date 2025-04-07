#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
エンベディングファイルの距離分析スクリプト

このスクリプトは、複数の問題のエンベディングファイル間の類似度を計算し、
似ている問題と似ていない問題を視覚的に確認するためのツールです。
コサイン類似度やユークリッド距離を用いて、エンベディング間の距離を測定し、
結果をJSON形式で保存したり、可視化したりします。
"""

import os
import sys
import json
import argparse
import logging
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from tqdm import tqdm
import pandas as pd
import seaborn as sns
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_embedding(embedding_path):
    """
    エンベディングファイルを読み込む

    Args:
        embedding_path (str): エンベディングファイルのパス

    Returns:
        tuple: (numpy.ndarray, str) - エンベディングデータとファイル名
    """
    try:
        embedding = np.load(embedding_path)
        file_name = os.path.basename(embedding_path).replace('_embedding.npy', '')
        return embedding, file_name
    except Exception as e:
        logger.error(f"エンベディングの読み込みに失敗しました: {embedding_path} - {e}")
        return None, None

def load_text_content(json_path):
    """
    関連するJSONファイルからテキスト内容を読み込む

    Args:
        json_path (str): JSONファイルのパス

    Returns:
        str: テキスト内容
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('text_content', '')
    except Exception as e:
        logger.error(f"JSONファイルの読み込みに失敗しました: {json_path} - {e}")
        return ""

def calculate_distance_matrix(embeddings, method='cosine'):
    """
    エンベディングデータの距離行列を計算する

    Args:
        embeddings (list): (embedding, name) のタプルのリスト
        method (str): 距離計算方法 ('cosine' または 'euclidean')

    Returns:
        tuple: (距離行列, ファイル名リスト)
    """
    embedding_data = np.array([e[0] for e in embeddings])
    file_names = [e[1] for e in embeddings]
    
    if method == 'cosine':
        # コサイン類似度を計算（1 - 類似度で距離に変換）
        similarity_matrix = cosine_similarity(embedding_data)
        distance_matrix = 1 - similarity_matrix
    elif method == 'euclidean':
        # ユークリッド距離を計算
        distance_matrix = euclidean_distances(embedding_data)
        # 正規化（オプション）
        # distance_matrix = distance_matrix / np.max(distance_matrix)
    else:
        raise ValueError(f"不明な距離計算方法: {method}")
    
    return distance_matrix, file_names

def export_distance_matrix(distance_matrix, file_names, output_path, method='cosine'):
    """
    距離行列をJSONファイルとして出力する

    Args:
        distance_matrix (numpy.ndarray): 距離行列
        file_names (list): ファイル名リスト
        output_path (str): 出力先パス
        method (str): 使用した距離計算方法
    """
    # 結果をJSON形式に変換
    result = {
        "method": method,
        "file_names": file_names,
        "distance_matrix": distance_matrix.tolist()
    }
    
    # JSONファイルとして保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logger.info(f"距離行列をエクスポートしました: {output_path}")

def visualize_distance_matrix(distance_matrix, file_names, output_path, method='cosine'):
    """
    距離行列をヒートマップとして可視化する

    Args:
        distance_matrix (numpy.ndarray): 距離行列
        file_names (list): ファイル名リスト
        output_path (str): 出力先パス
        method (str): 使用した距離計算方法
    """
    plt.figure(figsize=(12, 10))
    
    # ヒートマップを作成
    sns.heatmap(
        distance_matrix,
        annot=True,
        xticklabels=file_names,
        yticklabels=file_names,
        fmt='.2f',
        cmap='viridis'
    )
    
    # タイトルと軸ラベルの設定
    title = f"エンベディング間の{method}距離"
    if method == 'cosine':
        title = f"エンベディング間のコサイン距離"
    elif method == 'euclidean':
        title = f"エンベディング間のユークリッド距離"
    
    plt.title(title)
    plt.xlabel('問題')
    plt.ylabel('問題')
    
    # 保存
    plt.tight_layout()
    plt.savefig(output_path)
    logger.info(f"距離行列の可視化を保存しました: {output_path}")
    plt.close()

def visualize_embeddings_2d(embeddings, output_path, method='tsne'):
    """
    エンベディングを2次元に縮約して可視化する

    Args:
        embeddings (list): (embedding, name) のタプルのリスト 
        output_path (str): 出力先パス
        method (str): 次元削減手法 ('tsne' または 'pca')
    """
    embedding_data = np.array([e[0] for e in embeddings])
    file_names = [e[1] for e in embeddings]
    
    # 高次元データを2次元に縮約
    if method == 'tsne':
        reducer = TSNE(n_components=2, random_state=42)
        embedding_2d = reducer.fit_transform(embedding_data)
        title = "t-SNEによるエンベディングの2次元可視化"
    elif method == 'pca':
        reducer = PCA(n_components=2, random_state=42)
        embedding_2d = reducer.fit_transform(embedding_data)
        title = "PCAによるエンベディングの2次元可視化"
    else:
        raise ValueError(f"不明な次元削減手法: {method}")
    
    # 可視化
    plt.figure(figsize=(12, 10))
    
    # 各ポイントをプロット
    for i, name in enumerate(file_names):
        plt.scatter(embedding_2d[i, 0], embedding_2d[i, 1], s=100)
        plt.text(embedding_2d[i, 0] + 0.02, embedding_2d[i, 1] + 0.02, name, fontsize=9)
    
    plt.title(title)
    plt.xlabel('Dimension 1')
    plt.ylabel('Dimension 2')
    plt.grid(True)
    
    # 保存
    plt.tight_layout()
    plt.savefig(output_path)
    logger.info(f"エンベディングの2次元可視化を保存しました: {output_path}")
    plt.close()

def analyze_sample_embeddings(embedding_files, output_dir, distance_method='cosine', dim_reduction='tsne'):
    """
    サンプルのエンベディングファイルを分析する

    Args:
        embedding_files (list): エンベディングファイルのパスリスト
        output_dir (str): 出力ディレクトリ
        distance_method (str): 距離計算方法 ('cosine' または 'euclidean')
        dim_reduction (str): 次元削減手法 ('tsne' または 'pca')
    """
    # 出力ディレクトリの作成
    os.makedirs(output_dir, exist_ok=True)
    
    # エンベディングデータの読み込み
    embeddings = []
    for file_path in tqdm(embedding_files, desc="エンベディングの読み込み"):
        embedding, name = load_embedding(file_path)
        if embedding is not None:
            embeddings.append((embedding, name))
    
    if len(embeddings) < 2:
        logger.error(f"分析に必要な数のエンベディングが読み込めませんでした。最低2個必要です。")
        return
    
    logger.info(f"{len(embeddings)}個のエンベディングを読み込みました。")
    
    # 距離行列の計算
    distance_matrix, file_names = calculate_distance_matrix(embeddings, method=distance_method)
    
    # 結果のエクスポート
    output_json = os.path.join(output_dir, f"embedding_analysis.json")
    export_distance_matrix(distance_matrix, file_names, output_json, method=distance_method)
    
    # 距離行列の可視化
    output_heatmap = os.path.join(output_dir, f"embedding_heatmap_{distance_method}.png")
    visualize_distance_matrix(distance_matrix, file_names, output_heatmap, method=distance_method)
    
    # エンベディングの2次元可視化
    output_2d = os.path.join(output_dir, f"embedding_2d_{dim_reduction}.png")
    visualize_embeddings_2d(embeddings, output_2d, method=dim_reduction)
    
    # 最も類似した問題と最も類似していない問題のペアを見つける
    if distance_method == 'cosine':
        np.fill_diagonal(distance_matrix, 1.0)  # 自分自身との距離を最大に設定
    else:
        np.fill_diagonal(distance_matrix, np.max(distance_matrix))  # 自分自身との距離を最大に設定
    
    # 最も類似したペア（距離が最小）
    min_idx = np.unravel_index(distance_matrix.argmin(), distance_matrix.shape)
    min_distance = distance_matrix[min_idx]
    most_similar_pair = (file_names[min_idx[0]], file_names[min_idx[1]])
    
    # 最も類似していないペア（距離が最大）
    max_idx = np.unravel_index(distance_matrix.argmax(), distance_matrix.shape)
    max_distance = distance_matrix[max_idx]
    most_dissimilar_pair = (file_names[max_idx[0]], file_names[max_idx[1]])
    
    # 結果の詳細をJSONファイルとして出力
    analysis_details = {
        "most_similar_pair": {
            "files": most_similar_pair,
            "distance": float(min_distance),
        },
        "most_dissimilar_pair": {
            "files": most_dissimilar_pair,
            "distance": float(max_distance),
        },
        "distance_method": distance_method,
        "total_embeddings": len(embeddings)
    }
    
    with open(os.path.join(output_dir, "embedding_analysis_result.json"), 'w', encoding='utf-8') as f:
        json.dump(analysis_details, f, ensure_ascii=False, indent=2)
    
    logger.info(f"最も類似したペア: {most_similar_pair} - 距離: {min_distance:.4f}")
    logger.info(f"最も類似していないペア: {most_dissimilar_pair} - 距離: {max_distance:.4f}")
    logger.info(f"分析結果を {output_dir} に保存しました。")

def find_sample_files(base_files, num_similar=5, num_dissimilar=5, output_dir=None):
    """
    ベースファイルに対して類似/非類似のファイルを見つける

    Args:
        base_files (list): ベースとなるファイルのパスリスト
        num_similar (int): 取得する類似ファイルの数
        num_dissimilar (int): 取得する非類似ファイルの数
        output_dir (str): 結果を出力するディレクトリ（指定なしの場合は出力なし）

    Returns:
        dict: 類似/非類似ファイルの情報
    """
    # ベースファイルのディレクトリを特定
    base_dir = os.path.dirname(base_files[0])
    
    # ディレクトリ内のすべてのエンベディングファイルを取得
    all_embedding_files = list(Path(base_dir).glob('*_embedding.npy'))
    logger.info(f"{len(all_embedding_files)}個のエンベディングファイルが見つかりました。")
    
    # ベースファイルを読み込む
    base_embeddings = []
    for file_path in base_files:
        embedding, name = load_embedding(file_path)
        if embedding is not None:
            base_embeddings.append((embedding, name, file_path))
    
    if not base_embeddings:
        logger.error("ベースとなるエンベディングが読み込めませんでした。")
        return None
    
    # すべてのエンベディングとの距離を計算
    results = {}
    
    for base_embedding, base_name, base_path in base_embeddings:
        # ベース以外のファイルを読み込む
        other_embeddings = []
        for file_path in all_embedding_files:
            if file_path.name != os.path.basename(base_path) and file_path not in base_files:
                embedding, name = load_embedding(str(file_path))
                if embedding is not None:
                    # コサイン類似度を計算
                    similarity = cosine_similarity([base_embedding], [embedding])[0][0]
                    distance = 1 - similarity
                    other_embeddings.append((embedding, name, str(file_path), distance))
        
        # 距離でソート
        other_embeddings.sort(key=lambda x: x[3])
        
        # 最も類似した問題と最も類似していない問題を取得
        most_similar = other_embeddings[:num_similar]
        most_dissimilar = other_embeddings[-num_dissimilar:]
        
        # 結果を格納
        results[base_name] = {
            "base_file": base_path,
            "similar_files": [(name, path, distance) for _, name, path, distance in most_similar],
            "dissimilar_files": [(name, path, distance) for _, name, path, distance in most_dissimilar]
        }
        
        logger.info(f"ベースファイル {base_name} の分析完了")
    
    # 結果をJSONとして出力（オプション）
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "sample_files.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"サンプルファイル情報を保存しました: {output_path}")
    
    return results

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='エンベディングファイルの距離分析')
    parser.add_argument('--input', '-i', help='入力ディレクトリまたはエンベディングファイル（複数指定可）', nargs='+')
    parser.add_argument('--output', '-o', default='data/embedding', help='出力ディレクトリ（デフォルト: data/embedding）')
    parser.add_argument('--mode', '-m', choices=['analyze', 'sample'], default='analyze', 
                        help='モード選択（analyze: 分析、sample: サンプル選定、デフォルト: analyze）')
    parser.add_argument('--distance', '-d', choices=['cosine', 'euclidean'], default='cosine',
                        help='距離計算方法（cosine: コサイン距離、euclidean: ユークリッド距離、デフォルト: cosine）')
    parser.add_argument('--reduction', '-r', choices=['tsne', 'pca'], default='tsne',
                        help='次元削減手法（tsne: t-SNE, pca: PCA, デフォルト: tsne）')
    parser.add_argument('--similar', '-s', type=int, default=5,
                        help='サンプルモード時の類似ファイル数（デフォルト: 5）')
    parser.add_argument('--dissimilar', '-ds', type=int, default=5,
                        help='サンプルモード時の非類似ファイル数（デフォルト: 5）')
    
    args = parser.parse_args()
    
    # 入力がディレクトリの場合はエンベディングファイルのリストを取得
    embedding_files = []
    if args.input:
        for input_path in args.input:
            if os.path.isdir(input_path):
                files = list(Path(input_path).glob('*_embedding.npy'))
                embedding_files.extend([str(f) for f in files])
            elif input_path.endswith('_embedding.npy'):
                embedding_files.append(input_path)
    
    if not embedding_files:
        logger.error("エンベディングファイルが見つかりませんでした。")
        return 1
    
    # モードに応じた処理を実行
    if args.mode == 'analyze':
        analyze_sample_embeddings(
            embedding_files, 
            args.output,
            distance_method=args.distance,
            dim_reduction=args.reduction
        )
    elif args.mode == 'sample':
        find_sample_files(
            embedding_files,
            num_similar=args.similar,
            num_dissimilar=args.dissimilar,
            output_dir=args.output
        )
    
    logger.info("処理が完了しました。")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
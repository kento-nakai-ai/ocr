#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
似ている問題と似ていない問題のサンプル比較スクリプト

このスクリプトは、embedding_analyzer.pyで抽出した類似/非類似問題サンプルを
視覚的に比較するためのツールです。問題の画像とマークダウンテキストを並べて表示し、
エンベディング距離を確認できます。
"""

import os
import sys
import json
import argparse
import logging
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import shutil
from PIL import Image
from matplotlib.gridspec import GridSpec

# ロギング設定
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_sample_data(sample_file):
    """
    サンプルファイルのJSONデータを読み込む

    Args:
        sample_file (str): サンプルファイルのパス

    Returns:
        dict: サンプルデータ
    """
    try:
        with open(sample_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"サンプルファイルの読み込みに失敗しました: {sample_file} - {e}")
        return None

def get_image_path(embedding_file_path):
    """
    エンベディングファイルパスから画像ファイルパスを取得する

    Args:
        embedding_file_path (str): エンベディングファイルのパス

    Returns:
        str: 画像ファイルパス
    """
    # _embedding.npyを削除してベース名を取得
    base_name = embedding_file_path.replace('_embedding.npy', '')
    
    # 画像拡張子のリスト
    image_extensions = ['.png', '.jpg', '.jpeg']
    
    # 各拡張子で試す
    for ext in image_extensions:
        image_path = f"{base_name}{ext}"
        if os.path.exists(image_path):
            return image_path
    
    # imagesディレクトリ内に画像がある可能性がある
    base_dir = os.path.dirname(embedding_file_path)
    root_dir = os.path.dirname(os.path.dirname(base_dir))
    
    image_name = os.path.basename(base_name)
    images_dir = os.path.join(root_dir, 'images')
    
    if os.path.exists(images_dir):
        for ext in image_extensions:
            image_path = os.path.join(images_dir, f"{image_name}{ext}")
            if os.path.exists(image_path):
                return image_path
    
    logger.warning(f"画像ファイルが見つかりませんでした: {base_name}")
    return None

def get_analysis_path(embedding_file_path):
    """
    エンベディングファイルパスから分析JSONファイルパスを取得する

    Args:
        embedding_file_path (str): エンベディングファイルのパス

    Returns:
        str: 分析JSONファイルパス
    """
    # エンベディングファイルの拡張子を置換
    analysis_path = embedding_file_path.replace('_embedding.npy', '_analysis.json')
    
    if os.path.exists(analysis_path):
        return analysis_path
    
    logger.warning(f"分析JSONファイルが見つかりませんでした: {analysis_path}")
    return None

def extract_markdown_from_json(json_path):
    """
    JSONファイルからマークダウンテキストを抽出する

    Args:
        json_path (str): JSONファイルのパス

    Returns:
        str: マークダウンテキスト
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        text_content = data.get('text_content', '')
        
        # マークダウン部分を抽出（```json ... ``` の形式）
        if '```json' in text_content and '```' in text_content:
            json_part = text_content.split('```json')[1].split('```')[0].strip()
            try:
                # JSONとして解析
                problem_data = json.loads(json_part)
                
                # マークダウン形式に整形
                markdown = ""
                for problem in problem_data.get('problems', []):
                    markdown += f"## 問題 {problem.get('id', 'N/A')}\n\n"
                    markdown += f"{problem.get('question', '')}\n\n"
                    
                    markdown += "### 選択肢\n\n"
                    for choice in problem.get('choices', []):
                        markdown += f"{choice.get('number', '')}. {choice.get('text', '')}\n"
                    
                    markdown += f"\n### 正解\n\n{problem.get('correct_answer', 'N/A')}\n\n"
                    
                    if 'explanation' in problem:
                        markdown += f"### 解説\n\n{problem.get('explanation', '')}\n\n"
                    
                    markdown += "---\n\n"
                
                return markdown
            except json.JSONDecodeError:
                logger.warning(f"JSONデータの解析に失敗しました: {json_path}")
                return text_content
        
        return text_content
    except Exception as e:
        logger.error(f"JSONファイルからマークダウンの抽出に失敗しました: {json_path} - {e}")
        return ""

def create_comparison_report(sample_data, output_dir, max_samples=3):
    """
    比較レポートを作成する

    Args:
        sample_data (dict): サンプルデータ
        output_dir (str): 出力ディレクトリ
        max_samples (int): 表示するサンプル数の上限
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 各ベースファイルに対して処理
    for base_name, data in sample_data.items():
        base_file = data['base_file']
        similar_files = data['similar_files'][:max_samples]  # 上限まで
        dissimilar_files = data['dissimilar_files'][:max_samples]  # 上限まで
        
        # ベースファイルの情報
        base_image_path = get_image_path(base_file)
        base_analysis_path = get_analysis_path(base_file)
        base_markdown = ""
        if base_analysis_path:
            base_markdown = extract_markdown_from_json(base_analysis_path)
        
        # マークダウンレポート作成
        report_md = f"# {base_name} の類似・非類似問題比較\n\n"
        
        # ベース問題
        report_md += "## ベース問題\n\n"
        if base_image_path:
            # 画像をコピー
            base_image_name = os.path.basename(base_image_path)
            shutil.copy(base_image_path, os.path.join(output_dir, base_image_name))
            report_md += f"![{base_name}](./{base_image_name})\n\n"
        
        report_md += base_markdown + "\n\n"
        
        # 類似問題
        report_md += "## 類似問題\n\n"
        for name, path, distance in similar_files:
            report_md += f"### {name} (距離: {distance:.4f})\n\n"
            
            image_path = get_image_path(path)
            analysis_path = get_analysis_path(path)
            
            if image_path:
                # 画像をコピー
                image_name = os.path.basename(image_path)
                shutil.copy(image_path, os.path.join(output_dir, image_name))
                report_md += f"![{name}](./{image_name})\n\n"
            
            if analysis_path:
                markdown = extract_markdown_from_json(analysis_path)
                report_md += markdown + "\n\n"
        
        # 非類似問題
        report_md += "## 非類似問題\n\n"
        for name, path, distance in dissimilar_files:
            report_md += f"### {name} (距離: {distance:.4f})\n\n"
            
            image_path = get_image_path(path)
            analysis_path = get_analysis_path(path)
            
            if image_path:
                # 画像をコピー
                image_name = os.path.basename(image_path)
                shutil.copy(image_path, os.path.join(output_dir, image_name))
                report_md += f"![{name}](./{image_name})\n\n"
            
            if analysis_path:
                markdown = extract_markdown_from_json(analysis_path)
                report_md += markdown + "\n\n"
        
        # レポートを保存
        report_path = os.path.join(output_dir, f"{base_name}_comparison.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_md)
        
        logger.info(f"比較レポートを作成しました: {report_path}")
        
        # 可視化画像の作成
        create_visual_comparison(
            base_name, base_file, base_image_path,
            similar_files, dissimilar_files,
            output_dir
        )

def create_visual_comparison(base_name, base_file, base_image_path, similar_files, dissimilar_files, output_dir):
    """
    問題の視覚的な比較画像を作成する

    Args:
        base_name (str): ベース問題の名前
        base_file (str): ベース問題のファイルパス
        base_image_path (str): ベース問題の画像パス
        similar_files (list): 類似問題のリスト (name, path, distance)
        dissimilar_files (list): 非類似問題のリスト (name, path, distance)
        output_dir (str): 出力ディレクトリ
    """
    # 類似・非類似問題の画像パスを取得
    similar_images = []
    for _, path, distance in similar_files:
        img_path = get_image_path(path)
        if img_path:
            similar_images.append((img_path, distance))
    
    dissimilar_images = []
    for _, path, distance in dissimilar_files:
        img_path = get_image_path(path)
        if img_path:
            dissimilar_images.append((img_path, distance))
    
    # 画像が見つからない場合はスキップ
    if not base_image_path or not similar_images or not dissimilar_images:
        logger.warning(f"比較に必要な画像が見つかりませんでした: {base_name}")
        return
    
    # 画像の行数を決定（最大3行）
    n_similar = len(similar_images)
    n_dissimilar = len(dissimilar_images)
    n_rows = 1 + min(max(n_similar, n_dissimilar), 3)
    
    # プロット作成
    fig = plt.figure(figsize=(15, 5 * n_rows))
    gs = GridSpec(n_rows, 3, figure=fig)
    
    # ベース画像
    ax_base = fig.add_subplot(gs[0, 1])
    base_img = Image.open(base_image_path)
    ax_base.imshow(np.array(base_img))
    ax_base.set_title(f"ベース問題: {base_name}", fontsize=12)
    ax_base.axis('off')
    
    # 類似画像
    for i, (img_path, distance) in enumerate(similar_images):
        if i >= 3:  # 最大3枚まで
            break
        ax = fig.add_subplot(gs[i+1, 0])
        img = Image.open(img_path)
        ax.imshow(np.array(img))
        ax.set_title(f"類似問題 {i+1} (距離: {distance:.4f})", fontsize=12)
        ax.axis('off')
    
    # 非類似画像
    for i, (img_path, distance) in enumerate(dissimilar_images):
        if i >= 3:  # 最大3枚まで
            break
        ax = fig.add_subplot(gs[i+1, 2])
        img = Image.open(img_path)
        ax.imshow(np.array(img))
        ax.set_title(f"非類似問題 {i+1} (距離: {distance:.4f})", fontsize=12)
        ax.axis('off')
    
    # 保存
    plt.tight_layout()
    output_path = os.path.join(output_dir, f"{base_name}_visual_comparison.png")
    plt.savefig(output_path, dpi=150)
    plt.close()
    
    logger.info(f"視覚的比較画像を作成しました: {output_path}")

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='似ている問題と似ていない問題のサンプル比較')
    parser.add_argument('--input', '-i', required=True, help='サンプルファイル (sample_files.json) のパス')
    parser.add_argument('--output', '-o', default='data/embedding/comparison', help='出力ディレクトリ（デフォルト: data/embedding/comparison）')
    parser.add_argument('--max-samples', '-m', type=int, default=3, help='表示するサンプル数の上限（デフォルト: 3）')
    
    args = parser.parse_args()
    
    # サンプルデータの読み込み
    sample_data = load_sample_data(args.input)
    if not sample_data:
        logger.error(f"サンプルデータが読み込めませんでした: {args.input}")
        return 1
    
    # 比較レポート作成
    create_comparison_report(sample_data, args.output, max_samples=args.max_samples)
    
    logger.info("処理が完了しました。")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
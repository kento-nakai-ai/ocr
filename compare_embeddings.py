#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
画像とマルチモーダルEmbeddingの比較スクリプト

このスクリプトは、以下の分析を行います：
1. 画像のみのembeddingの場合、似ている問題と似ていない問題のL2距離を計算・比較
2. 画像+問題文Markdownのマルチモーダルembeddingの場合、同様の比較
3. それぞれの結果を分析し、似ている問題同士のL2距離が小さくなっているかを検証

使用するライブラリ：
- openai: OpenAIのAPIを利用してembeddingを取得
- PIL: 画像の読み込み
- numpy: 数値計算
- scipy: L2距離の計算
- matplotlib: 結果の可視化
- json: JSONファイルの読み込み
- dotenv: 環境変数の読み込み
"""

import os
import json
import glob
import base64
from io import BytesIO
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from scipy.spatial.distance import euclidean
import openai
import time
from dotenv import load_dotenv
import matplotlib
from matplotlib import font_manager

# 日本語フォントの設定
# macOSの場合はヒラギノフォントを使用
font_path = '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
if os.path.exists(font_path):
    font_manager.fontManager.addfont(font_path)
    matplotlib.rc('font', family='Hiragino Sans GB')
else:
    # ヒラギノフォントがない場合は代替フォントを検索
    font_dirs = ['/System/Library/Fonts', '/Library/Fonts', os.path.expanduser('~/Library/Fonts')]
    fonts = []
    for font_dir in font_dirs:
        if os.path.exists(font_dir):
            for font_file in os.listdir(font_dir):
                if any(keyword in font_file.lower() for keyword in ['hiragino', 'osaka', 'gothic', 'meiryo', 'yu', 'ms']):
                    font_path = os.path.join(font_dir, font_file)
                    fonts.append(font_path)
    
    if fonts:
        font_manager.fontManager.addfont(fonts[0])
        matplotlib.rc('font', family='sans-serif')

# 日本語表示の代替手段（フォールバック）
plt.rcParams['font.sans-serif'] = ['Hiragino Sans GB', 'Arial Unicode MS', 'DejaVu Sans', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

# .envファイルから環境変数を読み込む
load_dotenv()

# OpenAI APIキーを設定
openai.api_key = os.getenv("OPENAI_API_KEY")

# 対象となるディレクトリのパス
SIMILAR_DIR = "/Users/nakaikento/dev/ocr/data/images/似ている問題"
DISSIMILAR_DIR = "/Users/nakaikento/dev/ocr/data/images/似てない問題"

def encode_image(image_path):
    """画像をbase64エンコードする関数"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_image_embedding(image_path):
    """OpenAI APIを使用して画像のembeddingを取得する関数"""
    try:
        client = openai.OpenAI()
        base64_image = encode_image(image_path)
        
        # chat completionsを使用して画像のembeddingを取得
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "以下の画像の特徴を抽出して、それをベクトル表現してください。"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )
        
        # レスポンスからテキスト抽出
        embedding_text = response.choices[0].message.content
        
        # テキストをembedding化
        embedding_response = client.embeddings.create(
            model="text-embedding-3-large",
            input=embedding_text,
            dimensions=1536
        )
        
        return np.array(embedding_response.data[0].embedding)
    except Exception as e:
        print(f"画像embedding取得中にエラーが発生しました: {e}")
        return None

def get_multimodal_embedding(image_path, text_content):
    """OpenAI APIを使用して画像+テキストのマルチモーダルembeddingを取得する関数"""
    try:
        client = openai.OpenAI()
        base64_image = encode_image(image_path)
        
        # chat completionsを使用して画像+テキストの特徴を抽出
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"以下の画像と問題文の特徴を抽出して、それをベクトル表現してください。\n\n問題文: {text_content}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )
        
        # レスポンスからテキスト抽出
        embedding_text = response.choices[0].message.content
        
        # テキストをembedding化
        embedding_response = client.embeddings.create(
            model="text-embedding-3-large",
            input=embedding_text,
            dimensions=1536
        )
        
        return np.array(embedding_response.data[0].embedding)
    except Exception as e:
        print(f"マルチモーダルembedding取得中にエラーが発生しました: {e}")
        return None

def get_text_content(json_path):
    """JSONファイルから問題文を取得する関数"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('text_content', '')
    except Exception as e:
        print(f"JSONファイル読み込み中にエラーが発生しました: {e}")
        return ''

def calculate_l2_distances(embeddings):
    """与えられたembeddingのリストからすべてのペア間のL2距離を計算する関数"""
    num_embeddings = len(embeddings)
    distances = np.zeros((num_embeddings, num_embeddings))
    
    for i in range(num_embeddings):
        for j in range(num_embeddings):
            if i != j:
                distances[i, j] = euclidean(embeddings[i], embeddings[j])
    
    return distances

def plot_distances(similar_distances, dissimilar_distances, title):
    """L2距離のヒストグラムをプロットする関数"""
    plt.figure(figsize=(12, 6))
    
    # 英語のラベルで表示（文字化け回避）
    similar_label = 'Similar Problems'
    dissimilar_label = 'Dissimilar Problems'
    
    plt.hist(similar_distances.flatten(), bins=20, alpha=0.5, label=similar_label)
    plt.hist(dissimilar_distances.flatten(), bins=20, alpha=0.5, label=dissimilar_label)
    
    plt.xlabel('L2 Distance', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.title(title, fontsize=14)
    plt.legend(fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # 平均値を表示
    similar_mean = np.mean(similar_distances[similar_distances > 0])
    dissimilar_mean = np.mean(dissimilar_distances[dissimilar_distances > 0])
    
    plt.axvline(similar_mean, color='blue', linestyle='dashed', linewidth=1)
    plt.axvline(dissimilar_mean, color='orange', linestyle='dashed', linewidth=1)
    
    # 英語で平均値を表示
    plt.text(similar_mean, plt.ylim()[1]*0.9, f'Mean: {similar_mean:.4f}', 
             color='blue', ha='right', fontsize=10)
    plt.text(dissimilar_mean, plt.ylim()[1]*0.8, f'Mean: {dissimilar_mean:.4f}', 
             color='orange', ha='left', fontsize=10)
    
    return plt

def main():
    # 画像ファイルのパスを取得
    similar_images = glob.glob(os.path.join(SIMILAR_DIR, "*.png"))
    dissimilar_images = glob.glob(os.path.join(DISSIMILAR_DIR, "*.png"))
    
    # 画像のembeddingを取得
    print("画像のembeddingを取得中...")
    similar_image_embeddings = []
    for img_path in similar_images:
        print(f"処理中: {os.path.basename(img_path)}")
        embedding = get_image_embedding(img_path)
        if embedding is not None:
            similar_image_embeddings.append(embedding)
        time.sleep(1)  # APIレート制限を避けるための遅延
    
    dissimilar_image_embeddings = []
    for img_path in dissimilar_images:
        print(f"処理中: {os.path.basename(img_path)}")
        embedding = get_image_embedding(img_path)
        if embedding is not None:
            dissimilar_image_embeddings.append(embedding)
        time.sleep(1)  # APIレート制限を避けるための遅延
    
    # 画像embeddingのL2距離を計算
    similar_image_distances = calculate_l2_distances(similar_image_embeddings)
    dissimilar_image_distances = calculate_l2_distances(dissimilar_image_embeddings)
    
    # 画像+テキストのマルチモーダルembeddingを取得
    print("\n画像+テキストのマルチモーダルembeddingを取得中...")
    similar_multimodal_embeddings = []
    for img_path in similar_images:
        base_name = os.path.splitext(img_path)[0]
        json_path = f"{base_name}_analysis.json"
        
        if os.path.exists(json_path):
            print(f"処理中: {os.path.basename(img_path)} + テキスト")
            text_content = get_text_content(json_path)
            embedding = get_multimodal_embedding(img_path, text_content)
            if embedding is not None:
                similar_multimodal_embeddings.append(embedding)
            time.sleep(1)  # APIレート制限を避けるための遅延
    
    dissimilar_multimodal_embeddings = []
    for img_path in dissimilar_images:
        base_name = os.path.splitext(img_path)[0]
        json_path = f"{base_name}_analysis.json"
        
        if os.path.exists(json_path):
            print(f"処理中: {os.path.basename(img_path)} + テキスト")
            text_content = get_text_content(json_path)
            embedding = get_multimodal_embedding(img_path, text_content)
            if embedding is not None:
                dissimilar_multimodal_embeddings.append(embedding)
            time.sleep(1)  # APIレート制限を避けるための遅延
    
    # マルチモーダルembeddingのL2距離を計算
    similar_multimodal_distances = calculate_l2_distances(similar_multimodal_embeddings)
    dissimilar_multimodal_distances = calculate_l2_distances(dissimilar_multimodal_embeddings)
    
    # 結果の表示
    print("\n=== 画像embeddingのL2距離 ===")
    print(f"似ている問題の平均L2距離: {np.mean(similar_image_distances[similar_image_distances > 0]):.4f}")
    print(f"似ていない問題の平均L2距離: {np.mean(dissimilar_image_distances[dissimilar_image_distances > 0]):.4f}")
    
    print("\n=== マルチモーダルembeddingのL2距離 ===")
    print(f"似ている問題の平均L2距離: {np.mean(similar_multimodal_distances[similar_multimodal_distances > 0]):.4f}")
    print(f"似ていない問題の平均L2距離: {np.mean(dissimilar_multimodal_distances[dissimilar_multimodal_distances > 0]):.4f}")
    
    # クロスチェック：似ている問題と似ていない問題の間のL2距離
    cross_image_distances = []
    for similar_emb in similar_image_embeddings:
        for dissimilar_emb in dissimilar_image_embeddings:
            cross_image_distances.append(euclidean(similar_emb, dissimilar_emb))
    
    cross_multimodal_distances = []
    for similar_emb in similar_multimodal_embeddings:
        for dissimilar_emb in dissimilar_multimodal_embeddings:
            cross_multimodal_distances.append(euclidean(similar_emb, dissimilar_emb))
    
    print("\n=== クロスチェック: 似ている問題 vs 似ていない問題 ===")
    print(f"画像embeddingの平均L2距離: {np.mean(cross_image_distances):.4f}")
    print(f"マルチモーダルembeddingの平均L2距離: {np.mean(cross_multimodal_distances):.4f}")
    
    # 結果の可視化
    plot_img = plot_distances(similar_image_distances, dissimilar_image_distances, 
                         "Image Embedding L2 Distance Comparison")
    plot_img.savefig("image_embedding_distances.png")
    
    plot_multi = plot_distances(similar_multimodal_distances, dissimilar_multimodal_distances, 
                           "Multimodal Embedding L2 Distance Comparison")
    plot_multi.savefig("multimodal_embedding_distances.png")
    
    # クロスチェックのヒストグラム
    plt.figure(figsize=(12, 6))
    plt.hist(cross_image_distances, bins=20, alpha=0.5, label='Image Embedding')
    plt.hist(cross_multimodal_distances, bins=20, alpha=0.5, label='Multimodal Embedding')
    plt.xlabel('L2 Distance', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.title('Similar vs Dissimilar Problems L2 Distance', fontsize=14)
    plt.legend(fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.savefig("cross_distances.png")
    
    print("\n分析が完了しました。結果は以下のファイルに保存されました：")
    print("- image_embedding_distances.png")
    print("- multimodal_embedding_distances.png")
    print("- cross_distances.png")

if __name__ == "__main__":
    main() 
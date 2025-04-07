#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gemini APIを使用した画像解析・エンベディング取得スクリプト

このスクリプトは、Google Gemini APIを使用して画像を解析し、
テキスト情報や埋め込みベクトル（Embedding）を取得します。
取得したデータは、後でベクターサーチのためにデータベースに格納できます。
また、マルチモーダルのエンベディングAPIを使用して、画像とテキストのセットから
エンベディングを取得することも可能です。

仕様:
- 入力: 画像ファイルまたはディレクトリ、関連テキスト（オプション）
- 出力: 解析結果（JSON）、エンベディング（.npy形式）
- API: Google Gemini API（マルチモーダルモデル）

制限事項:
- Google Cloud APIキーが.envファイルに設定されている必要があります
- 画像の形式はJPEG/PNG等の一般的な形式である必要があります
- APIの利用制限（レートリミット）に注意する必要があります
"""

import os
import base64
import json
import argparse
import logging
import time
from pathlib import Path
import numpy as np
from dotenv import load_dotenv
import requests
from concurrent.futures import ThreadPoolExecutor

# Google Cloud APIの設定
try:
    import google.generativeai as genai
except ImportError:
    print("Google AI SDKがインストールされていません。以下のコマンドでインストールしてください：")
    print("pip install google-generativeai")
    exit(1)

# .envファイルから環境変数を読み込む
load_dotenv()

class GeminiImageAnalyzer:
    """
    Gemini APIを使用して画像を解析し、エンベディングを取得するクラス
    
    @param {string} api_key - Gemini APIキー
    @param {string} model_name - 使用するモデル名
    @param {number} embedding_dim - エンベディングの次元数
    @param {boolean} extract_text - テキスト抽出を行うかどうか
    @param {boolean} get_embedding - エンベディングを取得するかどうか
    @param {boolean} use_multimodal_embedding - マルチモーダルエンベディングを使用するかどうか
    """
    def __init__(self, api_key=None, model_name="gemini-2.5-pro-exp-03-25", embedding_dim=1536, 
                 extract_text=True, get_embedding=True, use_multimodal_embedding=False):
        self.logger = logging.getLogger(__name__)
        
        # APIキーの設定
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini APIキーが設定されていません。.envファイルでGEMINI_API_KEYを設定してください。")
        
        # モデル設定
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.extract_text = extract_text
        self.get_embedding = get_embedding
        self.use_multimodal_embedding = use_multimodal_embedding
        
        # APIエンドポイント設定
        self.vision_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        self.embedding_api_url = "https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedContent"
        self.multimodal_embedding_api_url = "https://generativelanguage.googleapis.com/v1beta/models/multimodalembedding@001:embedContent"
        
        # APIヘッダー設定
        self.headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
    
    def encode_image(self, image_path):
        """
        画像をBase64エンコード
        
        @param {string} image_path - 画像ファイルのパス
        @return {string} Base64エンコードされた画像データ
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    
    def get_mime_type(self, file_path):
        """
        ファイルのMIMEタイプを取得
        
        @param {string} file_path - ファイルのパス
        @return {string} MIMEタイプ
        """
        extension = os.path.splitext(file_path)[1].lower()
        
        if extension in ['.png']:
            return 'image/png'
        elif extension in ['.jpg', '.jpeg']:
            return 'image/jpeg'
        elif extension in ['.webp']:
            return 'image/webp'
        elif extension in ['.gif']:
            return 'image/gif'
        else:
            return 'application/octet-stream'
    
    def analyze_image(self, image_path, associated_text=None, output_dir=None, retry_count=3):
        """
        画像を解析してテキスト情報とエンベディングを取得
        
        @param {string} image_path - 解析する画像ファイルのパス
        @param {string} associated_text - 画像に関連するテキスト（オプション）
        @param {string} output_dir - 出力ディレクトリ
        @param {number} retry_count - 失敗時の再試行回数
        @return {dict} 解析結果
        """
        try:
            # ファイル名（拡張子なし）
            file_name = os.path.splitext(os.path.basename(image_path))[0]
            
            # モデル情報を表示
            self.logger.info(f"使用モデル: {self.model_name}")
            print(f"画像解析に使用するモデル: {self.model_name}")
            
            # 出力ディレクトリの設定
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                json_path = os.path.join(output_dir, f"{file_name}_analysis.json")
                npy_path = os.path.join(output_dir, f"{file_name}_embedding.npy")
                multimodal_npy_path = os.path.join(output_dir, f"{file_name}_multimodal_embedding.npy")
            
            # 結果格納用の辞書
            result = {
                "image_path": image_path,
                "file_name": file_name,
                "success": False,
                "text_content": None,
                "embedding": None,
                "multimodal_embedding": None,
                "error": None
            }
            
            # 画像のMIMEタイプを取得
            mime_type = self.get_mime_type(image_path)
            
            # 画像をBase64エンコード
            image_data = self.encode_image(image_path)
            
            # テキスト抽出（設定されている場合）
            if self.extract_text:
                self.logger.info(f"画像からテキストを抽出: {image_path}")
                
                # プロンプト作成
                if associated_text:
                    prompt = f"この画像について詳細に分析してください。関連テキスト: {associated_text}"
                else:
                    prompt = """
                    提供された日本語の試験問題を抽出し、以下の要件に従ってJSON形式で構造化してください：

                    1. 各問題について：
                      - 問題番号（例：No.1）を抽出する
                      - 問題文全体を抽出する
                      - すべての選択肢（1～4番）を抽出する
                      - 解説がある場合は抽出する
                      - 正解がある場合は抽出する
                      - 回路図や図表がある場合は「[図：（説明）]」の形式で記述する
                      - 数式は適切なLaTeX形式で表現する

                    2. 以下の形式でJSONとして構造化する：
                      ```json
                      {
                        "problems": [
                          {
                            "id": 1,
                            "question": "問題文...$Q = R I^2 t$...続く問題文",
                            "has_circuit_diagram": true, 
                            "circuit_description": "コンデンサとトランジスタを含む回路",
                            "has_table": false,
                            "choices": [
                              {
                                "number": 1,
                                "text": "選択肢1..."
                              },
                              {
                                "number": 2,
                                "text": "選択肢2..."
                              },
                              {
                                "number": 3,
                                "text": "選択肢3..."
                              },
                              {
                                "number": 4,
                                "text": "選択肢4..."
                              }
                            ],
                            "explanation": "解説文...$M = -e_2 \\frac{\\Delta t}{\\Delta i_1}$...続く解説文",
                            "correct_answer": X
                          }
                        ]
                      }  ```
                    """
                
                # APIリクエストのデータを構築
                data = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"text": prompt},
                                {
                                    "inline_data": {
                                        "mime_type": mime_type,
                                        "data": image_data
                                    }
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.4,
                        "topK": 32,
                        "topP": 0.95,
                        "maxOutputTokens": 8192
                    }
                }
                
                # リトライループ
                for attempt in range(retry_count):
                    try:
                        # APIリクエスト送信
                        response = requests.post(
                            self.vision_api_url,
                            headers=self.headers,
                            json=data
                        )
                        
                        # レスポンスをチェック
                        if response.status_code != 200:
                            self.logger.error(f"Gemini API エラー ({attempt+1}/{retry_count}): {response.status_code} {response.text}")
                            if attempt < retry_count - 1:
                                time.sleep(2 ** attempt)  # 指数バックオフ
                                continue
                            else:
                                result["error"] = f"Gemini API エラー: {response.status_code} {response.text}"
                                return result
                        
                        # レスポンスを解析
                        response_json = response.json()
                        
                        if "candidates" not in response_json or len(response_json["candidates"]) == 0:
                            self.logger.error(f"Gemini API レスポンスにcandidatesがありません: {response_json}")
                            if attempt < retry_count - 1:
                                time.sleep(2 ** attempt)
                                continue
                            else:
                                result["error"] = "Gemini API レスポンスに有効なcandidatesがありません"
                                return result
                        
                        # テキスト部分を抽出
                        text_parts = []
                        for part in response_json["candidates"][0]["content"]["parts"]:
                            if "text" in part:
                                text_parts.append(part["text"])
                        
                        result["text_content"] = "\n".join(text_parts)
                        break  # 成功したらループを抜ける
                        
                    except Exception as e:
                        self.logger.error(f"Gemini API処理中にエラーが発生しました ({attempt+1}/{retry_count}): {str(e)}")
                        if attempt < retry_count - 1:
                            time.sleep(2 ** attempt)
                        else:
                            result["error"] = f"Gemini API処理エラー: {str(e)}"
                            return result
            
            # エンベディング取得（設定されている場合）
            if self.get_embedding and result["text_content"]:
                if self.use_multimodal_embedding:
                    # マルチモーダルエンベディングを取得（テキストと画像の両方を使用）
                    self.logger.info(f"テキストと画像からマルチモーダルエンベディングを取得: {image_path}")
                    
                    # マルチモーダルエンベディング用のAPIリクエストのデータを構築
                    multimodal_embedding_data = {
                        "model": "multimodalembedding@001",
                        "content": {
                            "parts": [
                                {"text": result["text_content"]},
                                {
                                    "inlineData": {
                                        "mimeType": mime_type,
                                        "data": image_data
                                    }
                                }
                            ]
                        }
                    }
                    
                    # リトライループ
                    for attempt in range(retry_count):
                        try:
                            # APIリクエスト送信
                            multimodal_embedding_response = requests.post(
                                self.multimodal_embedding_api_url,
                                headers=self.headers,
                                json=multimodal_embedding_data
                            )
                            
                            # レスポンスをチェック
                            if multimodal_embedding_response.status_code != 200:
                                self.logger.error(f"Multimodal Embedding API エラー ({attempt+1}/{retry_count}): {multimodal_embedding_response.status_code} {multimodal_embedding_response.text}")
                                if attempt < retry_count - 1:
                                    time.sleep(2 ** attempt)
                                    continue
                                else:
                                    result["error"] = f"Multimodal Embedding API エラー: {multimodal_embedding_response.status_code} {multimodal_embedding_response.text}"
                                    # テキストのみのエンベディングを続行するため、ここではreturnしない
                            else:
                                # レスポンスを解析
                                multimodal_embedding_json = multimodal_embedding_response.json()
                                
                                if "embedding" not in multimodal_embedding_json or "values" not in multimodal_embedding_json["embedding"]:
                                    self.logger.error(f"Multimodal Embedding API レスポンスに有効なデータがありません: {multimodal_embedding_json}")
                                    if attempt < retry_count - 1:
                                        time.sleep(2 ** attempt)
                                        continue
                                else:
                                    # マルチモーダルエンベディング値を取得
                                    result["multimodal_embedding"] = np.array(multimodal_embedding_json["embedding"]["values"], dtype=np.float32)
                                    
                                    # 出力ディレクトリが指定されている場合は保存
                                    if output_dir and result["multimodal_embedding"] is not None:
                                        np.save(multimodal_npy_path, result["multimodal_embedding"])
                                    
                                    break  # 成功したらループを抜ける
                            
                        except Exception as e:
                            self.logger.error(f"Multimodal Embedding API処理中にエラーが発生しました ({attempt+1}/{retry_count}): {str(e)}")
                            if attempt < retry_count - 1:
                                time.sleep(2 ** attempt)
                            # テキストのみのエンベディングを続行するため、ここではresultにエラーは設定しない
                
                # テキストのみのエンベディングも取得
                self.logger.info(f"テキストからエンベディングを取得: {image_path}")
                
                # エンベディング用のAPIリクエストのデータを構築
                embedding_data = {
                    "model": "embedding-001",
                    "content": {
                        "parts": [
                            {"text": result["text_content"]}
                        ]
                    }
                }
                
                # リトライループ
                for attempt in range(retry_count):
                    try:
                        # APIリクエスト送信
                        embedding_response = requests.post(
                            self.embedding_api_url,
                            headers=self.headers,
                            json=embedding_data
                        )
                        
                        # レスポンスをチェック
                        if embedding_response.status_code != 200:
                            self.logger.error(f"Embedding API エラー ({attempt+1}/{retry_count}): {embedding_response.status_code} {embedding_response.text}")
                            if attempt < retry_count - 1:
                                time.sleep(2 ** attempt)
                                continue
                            else:
                                result["error"] = f"Embedding API エラー: {embedding_response.status_code} {embedding_response.text}"
                                return result
                        
                        # レスポンスを解析
                        embedding_json = embedding_response.json()
                        
                        if "embedding" not in embedding_json or "values" not in embedding_json["embedding"]:
                            self.logger.error(f"Embedding API レスポンスに有効なデータがありません: {embedding_json}")
                            if attempt < retry_count - 1:
                                time.sleep(2 ** attempt)
                                continue
                            else:
                                result["error"] = "Embedding API レスポンスに有効なデータがありません"
                                return result
                        
                        # エンベディング値を取得
                        result["embedding"] = np.array(embedding_json["embedding"]["values"], dtype=np.float32)
                        break  # 成功したらループを抜ける
                        
                    except Exception as e:
                        self.logger.error(f"Embedding API処理中にエラーが発生しました ({attempt+1}/{retry_count}): {str(e)}")
                        if attempt < retry_count - 1:
                            time.sleep(2 ** attempt)
                        else:
                            result["error"] = f"Embedding API処理エラー: {str(e)}"
                            return result
            
            # 結果が取得できたかどうか
            result["success"] = (result["text_content"] is not None) or (result["embedding"] is not None) or (result["multimodal_embedding"] is not None)
            
            # 結果をファイルに保存（出力ディレクトリが指定されている場合）
            if output_dir and result["success"]:
                # JSON形式のテキスト解析結果を保存
                if result["text_content"]:
                    analysis_data = {
                        "image_path": image_path,
                        "file_name": file_name,
                        "text_content": result["text_content"]
                    }
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(analysis_data, f, ensure_ascii=False, indent=2)
                
                # エンベディングベクトルを保存（numpy形式）
                if result["embedding"] is not None:
                    np.save(npy_path, result["embedding"])
                
                # マルチモーダルエンベディングを保存（numpy形式）
                if result["multimodal_embedding"] is not None:
                    np.save(multimodal_npy_path, result["multimodal_embedding"])
            
            return result
        
        except Exception as e:
            self.logger.error(f"画像解析中に予期せぬエラーが発生しました: {str(e)}")
            return {
                "image_path": image_path,
                "file_name": os.path.splitext(os.path.basename(image_path))[0],
                "success": False,
                "text_content": None,
                "embedding": None,
                "multimodal_embedding": None,
                "error": f"処理エラー: {str(e)}"
            }
    
    def process_directory(self, input_dir, output_dir=None, associated_texts=None, max_workers=4):
        """
        ディレクトリ内の全ての画像を処理
        
        @param {string} input_dir - 入力画像ディレクトリ
        @param {string} output_dir - 出力ディレクトリ
        @param {dict} associated_texts - ファイル名とテキストのマッピング辞書
        @param {number} max_workers - 並列処理の最大ワーカー数
        @return {list} 処理結果のリスト
        """
        # ディレクトリの存在確認
        if not os.path.exists(input_dir) or not os.path.isdir(input_dir):
            raise ValueError(f"入力ディレクトリが存在しません: {input_dir}")
        
        # 出力ディレクトリの作成
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 画像ファイルの一覧を取得
        image_paths = []
        for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif']:
            image_paths.extend(list(Path(input_dir).glob(f"*{ext}")))
        
        if not image_paths:
            self.logger.warning(f"処理対象の画像ファイルが見つかりません: {input_dir}")
            return []
        
        self.logger.info(f"処理対象: {len(image_paths)}個の画像ファイル")
        
        # 処理結果の格納リスト
        results = []
        
        # 並列処理で画像を解析
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            
            for image_path in image_paths:
                image_path_str = str(image_path)
                file_name = os.path.splitext(os.path.basename(image_path_str))[0]
                
                # 関連テキストがある場合は取得
                associated_text = None
                if associated_texts and file_name in associated_texts:
                    associated_text = associated_texts[file_name]
                
                # 非同期で処理を実行
                future = executor.submit(
                    self.analyze_image,
                    image_path_str,
                    associated_text,
                    output_dir
                )
                futures[future] = image_path_str
            
            # 結果を収集
            for i, future in enumerate(futures):
                image_path = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    status = "成功" if result["success"] else "失敗"
                    self.logger.info(f"処理完了 [{i+1}/{len(futures)}]: {image_path} - {status}")
                    
                except Exception as e:
                    self.logger.error(f"処理失敗 [{i+1}/{len(futures)}]: {image_path} - {str(e)}")
                    results.append({
                        "image_path": image_path,
                        "file_name": os.path.splitext(os.path.basename(image_path))[0],
                        "success": False,
                        "error": f"実行エラー: {str(e)}"
                    })
        
        # 成功・失敗件数のカウント
        success_count = sum(1 for r in results if r["success"])
        failure_count = len(results) - success_count
        
        self.logger.info(f"処理完了: 成功={success_count}, 失敗={failure_count}, 合計={len(results)}")
        
        return results

def get_multimodal_embedding(image_path, api_key=None, retry_count=3):
    """
    画像ファイルからマルチモーダルエンベディングを取得する

    Args:
        image_path (str): 画像ファイルのパス
        api_key (str): Gemini APIキー。未指定の場合は環境変数から読み込む
        retry_count (int): 失敗時の再試行回数
        
    Returns:
        numpy.ndarray: マルチモーダルエンベディングベクトル。失敗時はNone
    """
    # APIキーの取得
    api_key = api_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEYが設定されていません。")
        return None
    
    # 画像ファイルの読み込み
    try:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        logger.error(f"画像ファイルの読み込みに失敗しました: {image_path} - {e}")
        return None
    
    # APIエンドポイントとヘッダー
    embedding_api_url = "https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    
    # リクエストデータ（画像のみのマルチモーダルリクエスト）
    data = {
        "model": "embedding-001",
        "content": {
            "parts": [
                {
                    "inlineData": {
                        "mimeType": "image/png" if image_path.lower().endswith(".png") else "image/jpeg",
                        "data": image_base64
                    }
                }
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
            logger.error(f"Gemini マルチモーダルAPI処理中にエラーが発生しました ({attempt+1}/{retry_count}): {str(e)}")
            if attempt < retry_count - 1:
                time.sleep(2 ** attempt)
            else:
                return None
    
    return None

def get_text_and_image_embedding(image_path, text_content, api_key=None, retry_count=3):
    """
    画像とテキストの両方を含むマルチモーダルエンベディングを取得する

    Args:
        image_path (str): 画像ファイルのパス
        text_content (str): 関連するテキスト内容
        api_key (str): Gemini APIキー。未指定の場合は環境変数から読み込む
        retry_count (int): 失敗時の再試行回数
        
    Returns:
        numpy.ndarray: マルチモーダルエンベディングベクトル。失敗時はNone
    """
    # APIキーの取得
    api_key = api_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEYが設定されていません。")
        return None
    
    # 画像ファイルの読み込み
    try:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        logger.error(f"画像ファイルの読み込みに失敗しました: {image_path} - {e}")
        return None
    
    # APIエンドポイントとヘッダー
    embedding_api_url = "https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    
    # リクエストデータ（画像とテキストを含むマルチモーダルリクエスト）
    data = {
        "model": "embedding-001",
        "content": {
            "parts": [
                {
                    "inlineData": {
                        "mimeType": "image/png" if image_path.lower().endswith(".png") else "image/jpeg",
                        "data": image_base64
                    }
                },
                {
                    "text": text_content
                }
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
            logger.error(f"Gemini マルチモーダルAPI処理中にエラーが発生しました ({attempt+1}/{retry_count}): {str(e)}")
            if attempt < retry_count - 1:
                time.sleep(2 ** attempt)
            else:
                return None
    
    return None

def analyze_image(image_path, output_dir=None, model="gemini-1.5-pro-latest", api_key=None, 
                 include_prompt=False, max_tokens=None, temperature=0.2, top_p=0.95, top_k=40,
                 extract_json=True, save_embedding=False, multimodal_embedding=False):
    """
    画像をGemini APIで解析し、結果を保存する

    Args:
        image_path (str): 画像ファイルのパス
        output_dir (str): 出力先ディレクトリ（指定がなければ画像と同じ場所）
        model (str): 使用するGeminiモデル名
        api_key (str): Gemini APIキー（指定がなければ環境変数から取得）
        include_prompt (bool): プロンプトを結果に含めるかどうか
        max_tokens (int): 生成する最大トークン数
        temperature (float): 生成時の温度パラメータ
        top_p (float): top-pサンプリングのパラメータ
        top_k (int): top-kサンプリングのパラメータ
        extract_json (bool): 解析結果からJSONを抽出するかどうか
        save_embedding (bool): テキストエンベディングを保存するかどうか
        multimodal_embedding (bool): マルチモーダルエンベディングを生成するかどうか
        
    Returns:
        tuple: (解析結果, 成功フラグ, 出力先ディレクトリ, 抽出されたJSON)
    """
    # ...既存のコード...
    
    # 保存先の設定
    if output_dir is None:
        output_dir = os.path.dirname(image_path)
    elif not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    output_json_path = os.path.join(output_dir, f"{base_name}_analysis.json")
    output_txt_path = os.path.join(output_dir, f"{base_name}_analysis.txt")
    
    # ...既存のコード...
    
    if success:
        # ...既存のコード...
        
        # テキストエンベディングの保存
        if save_embedding:
            from src.generate_embedding import process_file
            process_file(output_json_path, embedding_dim=1536, use_api=True, api_key=api_key)
        
        # マルチモーダルエンベディングの生成と保存
        if multimodal_embedding:
            # 1. 画像のみのエンベディング
            image_embedding = get_multimodal_embedding(image_path, api_key)
            if image_embedding is not None:
                image_embedding_path = os.path.join(output_dir, f"{base_name}_image_embedding.npy")
                np.save(image_embedding_path, image_embedding)
                logger.info(f"画像エンベディングを保存しました: {image_embedding_path}")
            
            # 2. 画像とテキストを組み合わせたエンベディング
            if extracted_text:
                text_and_image_embedding = get_text_and_image_embedding(image_path, extracted_text, api_key)
                if text_and_image_embedding is not None:
                    combined_embedding_path = os.path.join(output_dir, f"{base_name}_combined_embedding.npy")
                    np.save(combined_embedding_path, text_and_image_embedding)
                    logger.info(f"画像とテキストの組み合わせエンベディングを保存しました: {combined_embedding_path}")
    
    # ...既存のコード...

def main():
    """コマンドライン実行のメイン処理"""
    parser = argparse.ArgumentParser(description='Gemini APIを使用して画像を解析します')
    parser.add_argument('--input', '-i', help='入力画像ファイルまたはディレクトリ', required=True)
    parser.add_argument('--output', '-o', help='出力先ディレクトリ（指定なしなら入力と同じ場所）')
    parser.add_argument('--model', '-m', default='gemini-1.5-pro-latest', 
                        help='使用するGeminiモデル名（デフォルト: gemini-1.5-pro-latest）')
    parser.add_argument('--api-key', help='Gemini APIキー（指定なしなら環境変数から取得）')
    parser.add_argument('--include-prompt', action='store_true', help='プロンプトを結果に含める')
    parser.add_argument('--max-tokens', type=int, help='生成する最大トークン数')
    parser.add_argument('--temperature', type=float, default=0.2, help='生成時の温度パラメータ')
    parser.add_argument('--top-p', type=float, default=0.95, help='top-pサンプリングのパラメータ')
    parser.add_argument('--top-k', type=int, default=40, help='top-kサンプリングのパラメータ')
    parser.add_argument('--no-json', action='store_true', help='JSONの抽出をスキップする')
    parser.add_argument('--save-embedding', action='store_true', help='テキストエンベディングを保存する')
    parser.add_argument('--multimodal-embedding', action='store_true', help='マルチモーダルエンベディングを生成する')
    parser.add_argument('--recursive', '-r', action='store_true', help='ディレクトリを再帰的に処理する')
    parser.add_argument('--direct-db', action='store_true', help='生成したエンベディングを直接DBに格納する')
    parser.add_argument('--concurrency', '-c', type=int, default=2, 
                        help='並列処理数（デフォルト: 2、APIレート制限に注意）')
    
    args = parser.parse_args()
    
    # ...既存のコード...
    
    # 処理関数を定義
    def process_image(image_path, output_subdir=None):
        # ...既存のコード...
        
        return analyze_image(
            image_path, 
            output_dir=output_subdir,
            model=args.model,
            api_key=args.api_key,
            include_prompt=args.include_prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            top_k=args.top_k,
            extract_json=not args.no_json,
            save_embedding=args.save_embedding,
            multimodal_embedding=args.multimodal_embedding
        )
    
    # ...既存のコード...

if __name__ == "__main__":
    exit(main()) 
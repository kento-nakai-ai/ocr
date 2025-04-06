#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gemini APIを使用した画像解析・エンベディング取得スクリプト

このスクリプトは、Google Gemini APIを使用して画像を解析し、
テキスト情報や埋め込みベクトル（Embedding）を取得します。
取得したデータは、後でベクターサーチのためにデータベースに格納できます。

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
    """
    def __init__(self, api_key=None, model_name="gemini-2.5-pro-exp-03-25", embedding_dim=1536, 
                 extract_text=True, get_embedding=True):
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
        
        # APIエンドポイント設定
        self.vision_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        self.embedding_api_url = "https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedContent"
        
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
            
            # 結果格納用の辞書
            result = {
                "image_path": image_path,
                "file_name": file_name,
                "success": False,
                "text_content": None,
                "embedding": None,
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

                    2. 以下の形式でJSONとして構造化する：
                      ```json
                      {
                        "problems": [
                          {
                            "id": 1,
                            "question": "問題文...$Q = R I^2 t$...続く問題文",
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
            result["success"] = (result["text_content"] is not None) or (result["embedding"] is not None)
            
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
            
            return result
        
        except Exception as e:
            self.logger.error(f"画像解析中に予期せぬエラーが発生しました: {str(e)}")
            return {
                "image_path": image_path,
                "file_name": os.path.splitext(os.path.basename(image_path))[0],
                "success": False,
                "text_content": None,
                "embedding": None,
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


def main():
    """メイン関数"""
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='Gemini APIを使用した画像解析・エンベディング取得')
    parser.add_argument('--input', '-i', required=True, help='入力画像ファイルまたはディレクトリのパス')
    parser.add_argument('--output', '-o', required=True, help='出力ディレクトリのパス')
    parser.add_argument('--text', '-t', help='画像に関連するテキスト（単一ファイル処理時）')
    parser.add_argument('--text-file', '-tf', help='ファイル名とテキストのマッピングを含むJSONファイル（ディレクトリ処理時）')
    parser.add_argument('--model', default='gemini-2.5-pro-exp-03-25', help='使用するGeminiモデル（デフォルト: gemini-2.5-pro-exp-03-25）')
    parser.add_argument('--no-text', action='store_true', help='テキスト抽出を行わない')
    parser.add_argument('--no-embedding', action='store_true', help='エンベディングを取得しない')
    parser.add_argument('--api-key', help='Gemini APIキー（指定しない場合は環境変数から取得）')
    parser.add_argument('--parallel', '-p', type=int, default=4, help='並列処理のワーカー数（デフォルト: 4）')
    
    args = parser.parse_args()
    
    try:
        # 入力パスの確認
        if not os.path.exists(args.input):
            logger.error(f"入力パスが存在しません: {args.input}")
            return 1
        
        # 関連テキストの読み込み（ディレクトリ処理時）
        associated_texts = None
        if args.text_file and os.path.isfile(args.text_file):
            try:
                with open(args.text_file, 'r', encoding='utf-8') as f:
                    associated_texts = json.load(f)
                logger.info(f"関連テキストを読み込みました: {len(associated_texts)}件")
            except Exception as e:
                logger.error(f"関連テキストファイルの読み込みに失敗しました: {str(e)}")
                return 1
        
        # Gemini画像アナライザーの初期化
        analyzer = GeminiImageAnalyzer(
            api_key=args.api_key,
            model_name=args.model,
            extract_text=not args.no_text,
            get_embedding=not args.no_embedding
        )
        
        # 単一ファイルまたはディレクトリを処理
        if os.path.isfile(args.input):
            # 単一ファイルの処理
            logger.info(f"単一ファイルを処理: {args.input}")
            result = analyzer.analyze_image(
                image_path=args.input,
                associated_text=args.text,
                output_dir=args.output
            )
            
            if result["success"]:
                logger.info(f"ファイルの処理が完了しました: {args.input}")
                if result["text_content"]:
                    logger.info(f"テキスト抽出: {len(result['text_content'])}文字")
                if result["embedding"] is not None:
                    logger.info(f"エンベディング: {result['embedding'].shape}")
                return 0
            else:
                logger.error(f"ファイルの処理に失敗しました: {args.input} - {result['error']}")
                return 1
                
        elif os.path.isdir(args.input):
            # ディレクトリの処理
            logger.info(f"ディレクトリを処理: {args.input}")
            results = analyzer.process_directory(
                input_dir=args.input,
                output_dir=args.output,
                associated_texts=associated_texts,
                max_workers=args.parallel
            )
            
            # 結果のサマリーを出力
            success_count = sum(1 for r in results if r["success"])
            if success_count == 0:
                logger.error("全てのファイルの処理に失敗しました")
                return 1
            elif success_count < len(results):
                logger.warning(f"一部のファイルの処理に失敗しました: 成功={success_count}/{len(results)}")
                return 0
            else:
                logger.info(f"全てのファイルの処理が完了しました: {len(results)}件")
                return 0
        
    except Exception as e:
        logger.error(f"実行中にエラーが発生しました: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main()) 
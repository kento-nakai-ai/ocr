#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCRエンジン統合スクリプト (Tesseract または LLMベース)

このスクリプトは、画像からテキストを抽出するための統合インターフェースを提供します。
ローカルのTesseract OCRか、マルチモーダルLLM API（Gemini, Claude, GPT-4等）を
パラメータに応じて切り替えて使用することができます。

仕様:
- 入力: 画像ファイル（PNG/JPEG）
- 出力: 抽出されたテキスト
- OCRエンジン: Tesseract（ローカル）またはLLM API（Gemini/Claude/GPT-4）

制限事項:
- ローカルモードでは、Tesseractがインストールされている必要があります
- LLMモードでは、各APIのキーが.envファイルに設定されている必要があります
- 画像の品質によってOCR精度が大きく変わります
"""

import os
import argparse
import logging
import subprocess
from pathlib import Path
import base64
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

class OCREngine:
    """
    OCRエンジン基底クラス
    
    @param {string} input_path - 入力画像ファイルまたはディレクトリのパス
    @param {string} output_path - 出力テキストファイルまたはディレクトリのパス
    @param {string} lang - OCR処理言語（Tesseractの場合）
    """
    def __init__(self, input_path, output_path, lang='jpn'):
        self.input_path = input_path
        self.output_path = output_path
        self.lang = lang
        self.logger = logging.getLogger(__name__)
        
        # 出力パスのディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    def process_single_image(self, image_path):
        """
        単一画像に対するOCR処理（サブクラスでオーバーライド）
        
        @param {string} image_path - 処理対象の画像ファイルパス
        @return {string} 抽出されたテキスト
        """
        raise NotImplementedError("サブクラスで実装する必要があります")
    
    def process(self):
        """
        OCR処理を実行
        
        @return {list} 処理結果のリスト
        """
        if os.path.isfile(self.input_path):
            # 単一ファイルの場合
            text = self.process_single_image(self.input_path)
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            return [self.output_path]
        
        elif os.path.isdir(self.input_path):
            # ディレクトリの場合
            input_dir = Path(self.input_path)
            output_dir = Path(self.output_path)
            output_dir.mkdir(exist_ok=True, parents=True)
            
            results = []
            
            # 画像ファイルのみを対象とする
            image_files = [f for f in input_dir.glob('*') 
                          if f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']]
            
            for img_file in sorted(image_files):
                # 出力ファイル名を決定（拡張子をtxtに変更）
                output_file = output_dir / (img_file.stem + '.txt')
                
                # OCR処理を実行
                self.logger.info(f"処理中: {img_file}")
                text = self.process_single_image(str(img_file))
                
                # 結果を保存
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                results.append(str(output_file))
                self.logger.info(f"保存完了: {output_file}")
            
            return results
        
        else:
            self.logger.error(f"入力パスが見つかりません: {self.input_path}")
            return []


class TesseractOCR(OCREngine):
    """
    Tesseract OCRを使用するクラス
    
    @param {string} input_path - 入力画像ファイルまたはディレクトリのパス
    @param {string} output_path - 出力テキストファイルまたはディレクトリのパス
    @param {string} lang - OCR処理言語（例: 'jpn', 'eng', 'jpn+eng'）
    @param {number} psm - Tesseractのページセグメンテーションモード
    """
    def __init__(self, input_path, output_path, lang='jpn', psm=11):
        super().__init__(input_path, output_path, lang)
        self.psm = psm
    
    def process_single_image(self, image_path):
        """
        Tesseract OCRで単一画像を処理
        
        @param {string} image_path - 処理対象の画像ファイルパス
        @return {string} 抽出されたテキスト
        """
        try:
            # Tesseractコマンドを構築
            cmd = [
                'tesseract',
                image_path,
                'stdout',
                '-l', self.lang,
                '--psm', str(self.psm)
            ]
            
            # コマンドを実行
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # 出力を返す
            return result.stdout
        
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Tesseract処理中にエラーが発生しました: {e}")
            self.logger.error(f"エラー詳細: {e.stderr}")
            raise Exception(f"Tesseract OCRエラー: {e.stderr}")
            
        except Exception as e:
            self.logger.error(f"OCR処理中に予期せぬエラーが発生しました: {str(e)}")
            raise


class LLMBasedOCR(OCREngine):
    """
    LLMベースのOCRを使用するクラス（GPT-4, Claude, Gemini）
    
    @param {string} input_path - 入力画像ファイルまたはディレクトリのパス
    @param {string} output_path - 出力テキストファイルまたはディレクトリのパス
    @param {string} llm_provider - 使用するLLMプロバイダ('claude', 'gpt4', 'gemini')
    @param {string} prompt - LLMに送るプロンプト
    """
    def __init__(self, input_path, output_path, llm_provider='claude', prompt=None):
        super().__init__(input_path, output_path)
        self.llm_provider = llm_provider.lower()
        
        # デフォルトプロンプト
        default_prompt = "この画像内のテキストを抽出してください。数式、表、段落など全てを正確に抽出し、元のレイアウトをできるだけ維持してください。"
        self.prompt = prompt if prompt else default_prompt
        
        # APIキーの取得
        if self.llm_provider == 'claude':
            self.api_key = os.getenv('CLAUDE_API_KEY')
        elif self.llm_provider == 'gpt4':
            self.api_key = os.getenv('OPENAI_API_KEY')
        elif self.llm_provider == 'gemini':
            self.api_key = os.getenv('GEMINI_API_KEY')
        else:
            raise ValueError(f"サポートされていないLLMプロバイダ: {llm_provider}")
        
        if not self.api_key:
            raise ValueError(f"{self.llm_provider.upper()}のAPIキーが設定されていません。.envファイルを確認してください。")
    
    def encode_image(self, image_path):
        """
        画像をBase64エンコード
        
        @param {string} image_path - 画像ファイルのパス
        @return {string} Base64エンコードされた画像データ
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def process_with_claude(self, image_path):
        """
        Claude APIを使用して画像からテキストを抽出
        
        @param {string} image_path - 処理対象の画像ファイルパス
        @return {string} 抽出されたテキスト
        """
        import anthropic
        
        client = anthropic.Anthropic(api_key=self.api_key)
        
        with open(image_path, "rb") as img:
            message = client.messages.create(
                model="claude-3-opus-20240229",  # 適切なモデルバージョンを指定
                max_tokens=4000,
                temperature=0,
                system="あなたはOCRエキスパートです。画像内のテキストを抽出し、可能な限り元のレイアウトを保持してください。",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.prompt},
                            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": self.encode_image(image_path)}}
                        ]
                    }
                ]
            )
        
        return message.content[0].text
    
    def process_with_gpt4(self, image_path):
        """
        GPT-4 Vision APIを使用して画像からテキストを抽出
        
        @param {string} image_path - 処理対象の画像ファイルパス
        @return {string} 抽出されたテキスト
        """
        import openai
        
        client = openai.OpenAI(api_key=self.api_key)
        
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{self.encode_image(image_path)}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4096
        )
        
        return response.choices[0].message.content
    
    def process_with_gemini(self, image_path):
        """
        Google Gemini APIを使用して画像からテキストを抽出
        
        @param {string} image_path - 処理対象の画像ファイルパス
        @return {string} 抽出されたテキスト
        """
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            
            # マルチモーダルモデルを使用
            model = genai.GenerativeModel('gemini-pro-vision')
            
            # 画像を読み込み
            image_parts = [
                {
                    "mime_type": "image/png",
                    "data": self.encode_image(image_path)
                }
            ]
            
            # 生成リクエストを実行
            response = model.generate_content([self.prompt, image_parts[0]])
            
            return response.text
            
        except ImportError:
            self.logger.error("google-cloud-aiplatformパッケージがインストールされていません。")
            self.logger.error("pip install google-cloud-aiplatform を実行してインストールしてください。")
            raise
    
    def process_single_image(self, image_path):
        """
        LLMベースOCRで単一画像を処理
        
        @param {string} image_path - 処理対象の画像ファイルパス
        @return {string} 抽出されたテキスト
        """
        try:
            self.logger.info(f"{self.llm_provider.upper()} APIを使用して画像を処理: {image_path}")
            
            # LLMプロバイダに応じた処理を実行
            if self.llm_provider == 'claude':
                text = self.process_with_claude(image_path)
            elif self.llm_provider == 'gpt4':
                text = self.process_with_gpt4(image_path)
            elif self.llm_provider == 'gemini':
                text = self.process_with_gemini(image_path)
            else:
                raise ValueError(f"サポートされていないLLMプロバイダ: {self.llm_provider}")
            
            return text
            
        except Exception as e:
            self.logger.error(f"LLM OCR処理中にエラーが発生しました: {str(e)}")
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
    parser = argparse.ArgumentParser(description='画像からテキストを抽出するOCRエンジン')
    parser.add_argument('input', help='入力画像ファイルまたはディレクトリのパス')
    parser.add_argument('output', help='出力テキストファイルまたはディレクトリのパス')
    parser.add_argument('--use-llm', action='store_true', help='LLMベースのOCRを使用する')
    parser.add_argument('--llm-provider', choices=['claude', 'gpt4', 'gemini'], default='claude',
                        help='使用するLLMプロバイダ（デフォルト: claude）')
    parser.add_argument('--lang', default='jpn', help='Tesseract OCRの言語（デフォルト: jpn）')
    parser.add_argument('--psm', type=int, default=11, help='Tesseractのページセグメンテーションモード（デフォルト: 11）')
    parser.add_argument('--prompt', help='LLMに送るカスタムプロンプト')
    
    args = parser.parse_args()
    
    try:
        # 引数に基づいてOCRエンジンを選択
        if args.use_llm:
            engine = LLMBasedOCR(
                input_path=args.input,
                output_path=args.output,
                llm_provider=args.llm_provider,
                prompt=args.prompt
            )
            logger.info(f"LLMベースOCRを使用: {args.llm_provider}")
        else:
            engine = TesseractOCR(
                input_path=args.input,
                output_path=args.output,
                lang=args.lang,
                psm=args.psm
            )
            logger.info(f"Tesseract OCRを使用: 言語={args.lang}, PSM={args.psm}")
        
        # OCR処理を実行
        result_files = engine.process()
        
        logger.info(f"OCR処理が完了しました。{len(result_files)}ファイルが生成されました。")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())  
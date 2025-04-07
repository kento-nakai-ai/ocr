#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCRテキストをMarkdown形式に変換するスクリプト

このスクリプトは、OCRで抽出したテキストをMarkdown形式に整形します。
特に数式をKaTeX形式に変換したり、図表を適切なMarkdownの画像タグに
変換する機能を提供します。
また、画像から直接KaTeX形式の数式を抽出する機能も備えています。

仕様:
- 入力: OCRテキストファイルまたは画像ファイル
- 出力: Markdown形式のファイル
- 機能: 数式のKaTeX変換、図表の画像タグ変換、レイアウト整形、画像からの直接KaTeX抽出

制限事項:
- 複雑な数式や特殊な記号は正確に変換できない場合があります
- OCRの精度に依存するため、元の画像品質が低いと変換精度も低下します
"""

import os
import re
import argparse
import logging
from pathlib import Path
import json
import requests
import base64
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

class OCRToMarkdownConverter:
    """
    OCRテキストをMarkdown形式に変換するクラス
    
    @param {string} input_path - 入力テキストファイルまたはディレクトリのパス
    @param {string} output_path - 出力Markdownファイルまたはディレクトリのパス
    @param {boolean} with_image_tags - 画像参照タグを挿入するかどうか
    @param {string} image_base_path - 画像ファイルの基本パス（相対パス）
    @param {boolean} use_gemini - 数式変換にGemini APIを使用するかどうか
    @param {boolean} direct_image_to_katex - 画像から直接KaTeXに変換するかどうか
    """
    def __init__(self, input_path, output_path, with_image_tags=True, image_base_path='../images', 
                 use_gemini=False, direct_image_to_katex=False):
        self.input_path = input_path
        self.output_path = output_path
        self.with_image_tags = with_image_tags
        self.image_base_path = image_base_path
        self.use_gemini = use_gemini
        self.direct_image_to_katex = direct_image_to_katex
        self.logger = logging.getLogger(__name__)
        
        # Gemini API設定
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.gemini_model = "gemini-2.5-pro-exp-03-25"
        
        # 数式変換パターン
        self.math_patterns = [
            # 平方根: √a → \sqrt{a}
            (r'√(\d+)', r'$\\sqrt{\1}$'),
            # 分数: a/b → \frac{a}{b}
            (r'(\d+)/(\d+)', r'$\\frac{\1}{\2}$'),
            # 上付き文字: a^b → a^{b}
            (r'(\w+)\^(\d+)', r'$\1^{\2}$'),
            # 下付き文字: a_b → a_{b}
            (r'(\w+)_(\d+)', r'$\1_{\2}$'),
            # 三角関数: sin(x) → \sin(x)
            (r'sin\(([^)]+)\)', r'$\\sin(\1)$'),
            (r'cos\(([^)]+)\)', r'$\\cos(\1)$'),
            (r'tan\(([^)]+)\)', r'$\\tan(\1)$'),
            # 数式ブロック（行間）
            (r'\[数式:([^]]+)\]', r'$$\1$$'),
            # 積分記号
            (r'∫\s*([^d]+)d([a-z])', r'$\\int \1 d\2$'),
            # ギリシャ文字
            (r'α', r'$\\alpha$'),
            (r'β', r'$\\beta$'),
            (r'γ', r'$\\gamma$'),
            (r'θ', r'$\\theta$'),
            (r'π', r'$\\pi$'),
            # 無限大
            (r'∞', r'$\\infty$'),
        ]
        
        # 図表パターン（[図1]、[表2]などの検出）
        self.figure_pattern = re.compile(r'\[図(\d+)\]|\[表(\d+)\]|\[Fig\.(\d+)\]|\[Table(\d+)\]')
        
        # 出力ディレクトリが存在しない場合は作成
        output_dir = os.path.dirname(output_path) if os.path.isfile(input_path) else output_path
        os.makedirs(output_dir, exist_ok=True)
    
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
    
    def direct_image_to_katex_conversion(self, image_path):
        """
        画像から直接KaTeX形式の数式を抽出
        
        @param {string} image_path - 画像ファイルのパス
        @return {string} 変換されたMarkdownテキスト
        """
        try:
            if not self.gemini_api_key:
                self.logger.error("Gemini APIキーが設定されていません。画像から直接KaTeXへの変換にはAPIキーが必要です。")
                return None
            
            # 画像をBase64エンコード
            image_data = self.encode_image(image_path)
            mime_type = self.get_mime_type(image_path)
            
            # Gemini APIのエンドポイント
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
            
            # リクエストヘッダー
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.gemini_api_key
            }
            
            # プロンプト作成
            prompt = """
            この画像は試験問題やノートなどから抽出された画像です。画像から以下の内容を抽出し、マークダウン形式で出力してください：

            1. テキスト内容全体を抽出する
            2. 数式は必ずKaTeX形式（$...$または$$...$$）で表現する
            3. LaTeXの数式表現を正確に使用する：
               - 分数は \frac{分子}{分母}
               - 指数は a^{n}
               - 添え字は a_{n}
               - ギリシャ文字は \alpha, \beta など
               - 積分記号は \int
               - 極限は \lim_{x \to a}
               - 和記号は \sum_{i=1}^{n}
               - 平方根は \sqrt{x}
            4. 回路図、表、グラフなどの図形的要素は [図: 回路図の説明] のように記述する
            5. 選択肢がある場合は番号付きリスト（1. 2. 3. 4.）で表現する
            6. 見出しは適切なマークダウン記法（# ## ###）で表現する
            7. 箇条書きはマークダウンの箇条書き記法（- または *）で表現する
            
            出力形式はMarkdown形式のみとし、解説や前後の文章は含めないでください。
            """
            
            # リクエストデータ
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
                    "temperature": 0.2,
                    "topP": 0.8,
                    "topK": 40,
                    "maxOutputTokens": 8192
                }
            }
            
            # APIリクエスト送信
            self.logger.info(f"画像から直接KaTeXへの変換リクエストを送信: {image_path}")
            response = requests.post(url, headers=headers, json=data)
            
            # レスポンスのチェック
            if response.status_code != 200:
                self.logger.error(f"Gemini API エラー: {response.status_code} {response.text}")
                return None
            
            # レスポンスからテキストを抽出
            response_json = response.json()
            if 'candidates' not in response_json or not response_json['candidates']:
                self.logger.error("Gemini API レスポンスに有効なcandidatesがありません")
                return None
            
            # テキスト部分を抽出
            text_parts = []
            for part in response_json["candidates"][0]["content"]["parts"]:
                if "text" in part:
                    text_parts.append(part["text"])
            
            markdown_text = "\n".join(text_parts)
            
            # 余分な部分の除去（プロンプトの繰り返しなど）
            if 'この画像は試験問題' in markdown_text:
                markdown_text = markdown_text.split('この画像は試験問題')[0]
            
            self.logger.info(f"画像から直接KaTeXへの変換が完了しました: {image_path}")
            return markdown_text
            
        except Exception as e:
            self.logger.error(f"画像から直接KaTeXへの変換中にエラーが発生: {str(e)}")
            return None
    
    def apply_math_patterns(self, text):
        """
        テキスト内の数式記号をKaTeX形式に変換
        
        @param {string} text - 入力テキスト
        @return {string} 変換後のテキスト
        """
        # Gemini APIを使用する場合
        if self.use_gemini and self.gemini_api_key:
            return self._apply_math_patterns_with_gemini(text)
        
        # 通常の正規表現ベースの変換
        result = text
        for pattern, replacement in self.math_patterns:
            result = re.sub(pattern, replacement, result)
        return result
    
    def _apply_math_patterns_with_gemini(self, text):
        """
        Gemini APIを使用してテキスト内の数式記号をKaTeX形式に変換
        
        @param {string} text - 入力テキスト
        @return {string} 変換後のテキスト
        """
        try:
            # Gemini APIのエンドポイント
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
            
            # リクエストヘッダー
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.gemini_api_key
            }
            
            # Gemini APIへのプロンプト
            prompt = """
            下記のテキスト内の数式や数学記号をKaTeX構文を使って変換してください。
            変換ルール:
            1. インライン数式は $...$ で囲む
            2. ブロック数式は $$...$$ で囲む
            3. 分数はLaTeX形式で \frac{分子}{分母} と表現
            4. 平方根は \sqrt{} を使用
            5. ギリシャ文字はLaTeX表記 (\alpha, \beta, \gamma, \theta など)
            6. 上付き添字はa^{b}、下付き添字はa_{b}の形式
            7. 三角関数は \sin, \cos, \tan などを使用
            8. 積分記号は \int を使用
            9. 無限大は \infty を使用
            
            元のテキストのレイアウトは可能な限り保持し、数式・記号部分のみを変換してください。
            元テキスト:
            
            """
            
            # リクエストデータ
            data = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": prompt + text
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.8,
                    "topK": 40
                }
            }
            
            # APIリクエスト送信
            self.logger.info("Gemini APIに数式変換リクエストを送信")
            response = requests.post(url, headers=headers, json=data)
            
            # レスポンスのチェック
            if response.status_code != 200:
                self.logger.error(f"Gemini API エラー: {response.status_code} {response.text}")
                return text  # エラー時は元のテキストを返す
            
            # レスポンスからテキストを抽出
            response_json = response.json()
            if 'candidates' not in response_json or not response_json['candidates']:
                self.logger.error(f"Gemini API レスポンスに有効なcandidatesがありません")
                return text
            
            # 変換後のテキストを取得
            converted_text = response_json['candidates'][0]['content']['parts'][0]['text']
            
            # 余分な部分の除去（プロンプトの繰り返しなど）
            if '元テキスト:' in converted_text:
                converted_text = converted_text.split('元テキスト:')[0]
            
            return converted_text
            
        except Exception as e:
            self.logger.error(f"Gemini APIによる数式変換中にエラーが発生: {str(e)}")
            return text  # エラー時は元のテキストを返す
    
    def insert_image_tags(self, text, base_filename):
        """
        図表の参照を画像タグに変換
        
        @param {string} text - 入力テキスト
        @param {string} base_filename - 基本ファイル名（画像ファイル名の生成に使用）
        @return {string} 変換後のテキスト
        """
        if not self.with_image_tags:
            return text
        
        def replace_figure(match):
            fig_num = match.group(1) or match.group(2) or match.group(3) or match.group(4)
            if not fig_num:
                return match.group(0)
            
            img_path = f"{self.image_base_path}/{base_filename}_figure_{fig_num}.png"
            return f"\n\n![図{fig_num}]({img_path})\n\n"
        
        return self.figure_pattern.sub(replace_figure, text)
    
    def format_layout(self, text):
        """
        テキストのレイアウトを整形
        
        @param {string} text - 入力テキスト
        @return {string} 整形後のテキスト
        """
        # 複数の空行を1つにまとめる
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 箇条書きの整形
        text = re.sub(r'^(\s*)([•·・])(\s*)', r'\1- ', text, flags=re.MULTILINE)
        
        # 見出しの整形（数字で始まる行を見出しに）
        text = re.sub(r'^(\d+)[\.．、]\s+(.+)$', r'## \1. \2', text, flags=re.MULTILINE)
        
        # 選択肢（1. 2. 3. など）の整形
        text = re.sub(r'^(\s*)(\d+)[\.．、](\s*)(?!\d)', r'\1\2. ', text, flags=re.MULTILINE)
        
        return text
    
    def convert_single_file(self, input_file, output_file):
        """
        単一ファイルの変換を実行
        
        @param {string} input_file - 入力ファイルパス
        @param {string} output_file - 出力ファイルパス
        @return {boolean} 変換が成功したかどうか
        """
        try:
            self.logger.info(f"ファイルを変換: {input_file} → {output_file}")
            
            # ファイルの種類を判断（画像かテキストか）
            file_extension = os.path.splitext(input_file)[1].lower()
            is_image = file_extension in ['.png', '.jpg', '.jpeg', '.webp', '.gif']
            
            # ベースファイル名を取得（拡張子なし）
            base_filename = os.path.splitext(os.path.basename(input_file))[0]
            
            # 画像から直接KaTeXに変換する場合
            if is_image and self.direct_image_to_katex:
                text = self.direct_image_to_katex_conversion(input_file)
                if text is None:
                    self.logger.error(f"画像からの直接変換に失敗しました: {input_file}")
                    return False
            else:
                # テキストファイルを読み込み
                with open(input_file, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # 数式変換
                text = self.apply_math_patterns(text)
            
            # 図表変換
            text = self.insert_image_tags(text, base_filename)
            
            # レイアウト整形
            text = self.format_layout(text)
            
            # 出力ファイルに保存
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(text)
            
            self.logger.info(f"変換完了: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイル変換中にエラーが発生しました: {str(e)}")
            return False
    
    def convert(self):
        """
        変換処理を実行
        
        @return {list} 生成されたMarkdownファイルのパスリスト
        """
        if os.path.isfile(self.input_path):
            # 単一ファイルの場合
            success = self.convert_single_file(self.input_path, self.output_path)
            return [self.output_path] if success else []
        
        elif os.path.isdir(self.input_path):
            # ディレクトリの場合
            input_dir = Path(self.input_path)
            output_dir = Path(self.output_path)
            output_dir.mkdir(exist_ok=True, parents=True)
            
            results = []
            
            # 対象ファイルを検索（テキストファイルと画像ファイル）
            target_files = []
            
            # テキストファイル
            target_files.extend(input_dir.glob('*.txt'))
            
            # 画像ファイル（直接KaTeXに変換する場合のみ）
            if self.direct_image_to_katex:
                for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif']:
                    target_files.extend(input_dir.glob(f'*{ext}'))
            
            for input_file in sorted(target_files):
                # 出力ファイル名を決定（拡張子をmdに変更）
                output_file = output_dir / f"{input_file.stem}.md"
                
                # 変換を実行
                success = self.convert_single_file(str(input_file), str(output_file))
                if success:
                    results.append(str(output_file))
            
            return results
        
        else:
            self.logger.error(f"入力パスが見つかりません: {self.input_path}")
            return []


def main():
    """メイン関数"""
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='OCRテキストをMarkdown形式に変換')
    parser.add_argument('input', help='入力テキストファイルまたはディレクトリのパス')
    parser.add_argument('output', help='出力Markdownファイルまたはディレクトリのパス')
    parser.add_argument('--no-image-tags', action='store_true', help='画像参照タグを挿入しない')
    parser.add_argument('--image-base-path', default='../images', help='画像ファイルの基本パス（相対パス）')
    parser.add_argument('--use-gemini', action='store_true', help='数式変換にGemini APIを使用する')
    parser.add_argument('--direct-image-to-katex', action='store_true', help='画像から直接KaTeXに変換する')
    
    args = parser.parse_args()
    
    try:
        # Gemini APIを使用する場合はAPIキーの存在をチェック
        if (args.use_gemini or args.direct_image_to_katex) and not os.getenv('GEMINI_API_KEY'):
            logger.warning("Gemini APIを使用する設定ですが、APIキーが設定されていません。")
            logger.warning(".envファイルに GEMINI_API_KEY を設定してください。")
            
            if args.direct_image_to_katex:
                logger.error("画像から直接KaTeXへの変換には、Gemini APIキーが必須です。処理を中止します。")
                return 1
            
            logger.warning("標準の正規表現ベースの変換を使用します。")
            args.use_gemini = False
        
        # 変換を実行
        converter = OCRToMarkdownConverter(
            input_path=args.input,
            output_path=args.output,
            with_image_tags=not args.no_image_tags,
            image_base_path=args.image_base_path,
            use_gemini=args.use_gemini,
            direct_image_to_katex=args.direct_image_to_katex
        )
        
        # Gemini APIを使用する場合のログ出力
        if args.use_gemini:
            logger.info("数式変換にGemini APIを使用します")
        
        # 画像から直接KaTeXに変換する場合のログ出力
        if args.direct_image_to_katex:
            logger.info("画像から直接KaTeXへの変換を使用します")
        
        result_files = converter.convert()
        
        logger.info(f"変換が完了しました。{len(result_files)}ファイルが生成されました。")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 
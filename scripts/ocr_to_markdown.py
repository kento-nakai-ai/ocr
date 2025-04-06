#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCRテキストをMarkdown形式に変換するスクリプト

このスクリプトは、OCRで抽出したテキストをMarkdown形式に整形します。
特に数式をKaTeX形式に変換したり、図表を適切なMarkdownの画像タグに
変換する機能を提供します。

仕様:
- 入力: OCRテキストファイル
- 出力: Markdown形式のファイル
- 機能: 数式のKaTeX変換、図表の画像タグ変換、レイアウト整形

制限事項:
- 複雑な数式や特殊な記号は正確に変換できない場合があります
- OCRの精度に依存するため、元の画像品質が低いと変換精度も低下します
"""

import os
import re
import argparse
import logging
from pathlib import Path

class OCRToMarkdownConverter:
    """
    OCRテキストをMarkdown形式に変換するクラス
    
    @param {string} input_path - 入力テキストファイルまたはディレクトリのパス
    @param {string} output_path - 出力Markdownファイルまたはディレクトリのパス
    @param {boolean} with_image_tags - 画像参照タグを挿入するかどうか
    @param {string} image_base_path - 画像ファイルの基本パス（相対パス）
    """
    def __init__(self, input_path, output_path, with_image_tags=True, image_base_path='../images'):
        self.input_path = input_path
        self.output_path = output_path
        self.with_image_tags = with_image_tags
        self.image_base_path = image_base_path
        self.logger = logging.getLogger(__name__)
        
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
    
    def apply_math_patterns(self, text):
        """
        テキスト内の数式記号をKaTeX形式に変換
        
        @param {string} text - 入力テキスト
        @return {string} 変換後のテキスト
        """
        result = text
        for pattern, replacement in self.math_patterns:
            result = re.sub(pattern, replacement, result)
        return result
    
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
            
            # 入力ファイルを読み込み
            with open(input_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # ベースファイル名を取得（拡張子なし）
            base_filename = os.path.splitext(os.path.basename(input_file))[0]
            
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
            
            # テキストファイルのみを対象とする
            text_files = [f for f in input_dir.glob('*.txt')]
            
            for text_file in sorted(text_files):
                # 出力ファイル名を決定（拡張子をmdに変更）
                output_file = output_dir / f"{text_file.stem}.md"
                
                # 変換を実行
                success = self.convert_single_file(str(text_file), str(output_file))
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
    
    args = parser.parse_args()
    
    try:
        # 変換を実行
        converter = OCRToMarkdownConverter(
            input_path=args.input,
            output_path=args.output,
            with_image_tags=not args.no_image_tags,
            image_base_path=args.image_base_path
        )
        result_files = converter.convert()
        
        logger.info(f"変換が完了しました。{len(result_files)}ファイルが生成されました。")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 
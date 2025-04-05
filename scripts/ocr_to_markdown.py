#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCRテキストをMarkdown形式に変換するスクリプト

このスクリプトは、Tesseract OCRなどで生成されたプレーンテキストを
Markdown形式に変換します。特に数式表現をKaTeX形式に変換し、
画像タグや見出しなどを適切なMarkdown構文に置き換えます。

使用例:
    python ocr_to_markdown.py input.txt output.md
"""

import re
import argparse
import os
import logging


# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OCRToMarkdownConverter:
    """
    OCRテキストをMarkdown形式に変換するクラス
    
    主な機能:
    - 数式表現のKaTeX変換
    - 画像タグのMarkdown変換
    - 見出しや箇条書きの整形
    - その他の整形ルール
    """
    
    def __init__(self):
        # 数式変換パターン
        self.math_patterns = [
            # [SQRT(3)] → $\sqrt{3}$
            (r'\[SQRT\((\d+)\)\]', r'$\\sqrt{\1}$'),
            # [1/2] → $\frac{1}{2}$
            (r'\[(\d+)/(\d+)\]', r'$\\frac{\1}{\2}$'),
            # x^2 → $x^2$
            (r'([a-zA-Z])(\^)(\d+)', r'$\1\2\3$'),
            # [PI] → $\pi$
            (r'\[PI\]', r'$\\pi$'),
            # [SIGMA] → $\Sigma$
            (r'\[SIGMA\]', r'$\\Sigma$'),
            # [DELTA] → $\Delta$
            (r'\[DELTA\]', r'$\\Delta$'),
            # [ALPHA] → $\alpha$
            (r'\[ALPHA\]', r'$\\alpha$'),
            # [BETA] → $\beta$
            (r'\[BETA\]', r'$\\beta$'),
            # [GAMMA] → $\gamma$
            (r'\[GAMMA\]', r'$\\gamma$'),
            # [OMEGA] → $\omega$
            (r'\[OMEGA\]', r'$\\omega$'),
            # [INFINITY] → $\infty$
            (r'\[INFINITY\]', r'$\\infty$'),
            # x[n] → $x[n]$
            (r'([a-zA-Z])\[([a-zA-Z0-9])\]', r'$\1[\2]$'),
            # [INTEGRAL] → $\int$
            (r'\[INTEGRAL\]', r'$\\int$'),
            # [PARTIAL] → $\partial$
            (r'\[PARTIAL\]', r'$\\partial$'),
            # [THETA] → $\theta$
            (r'\[THETA\]', r'$\\theta$')
        ]
        
        # 画像タグ変換パターン
        self.image_patterns = [
            # <img src="foo.png"> → ![画像](foo.png)
            (r'<img\s+src=["\']([^"\']+)["\']>', r'![画像](\1)'),
            # [figure_n] → ![図n](図n.png)
            (r'\[figure_(\d+)\]', r'![図\1](図\1.png)')
        ]
        
        # 見出し変換パターン
        self.heading_patterns = [
            # 問 1. → ## 問 1.
            (r'^(問\s*\d+\.?)', r'## \1'),
            # 第1章 → # 第1章
            (r'^(第\s*\d+\s*章)', r'# \1')
        ]
        
        # その他の整形パターン
        self.format_patterns = [
            # 連続する空行を1つにまとめる
            (r'\n{3,}', r'\n\n'),
            # 行末の空白を削除
            (r'[ \t]+$', r''),
            # 箇条書きを整形
            (r'^(\s*)(\d+)[\.\)]\s+', r'\1\2. '),
            # アスタリスクによる箇条書き
            (r'^(\s*)\*\s+', r'\1* ')
        ]
    
    def convert_text(self, text):
        """
        テキストをMarkdown形式に変換します
        
        Args:
            text (str): 変換するOCRテキスト
            
        Returns:
            str: 変換後のMarkdownテキスト
        """
        # 入力テキストの行数をログに出力
        logger.info(f"変換開始: {len(text.splitlines())}行のテキスト")
        
        # 1. 数式変換
        for pattern, replacement in self.math_patterns:
            text = re.sub(pattern, replacement, text)
        logger.info("数式変換完了")
        
        # 2. 画像タグ変換
        for pattern, replacement in self.image_patterns:
            text = re.sub(pattern, replacement, text)
        logger.info("画像タグ変換完了")
        
        # 3. 見出し変換
        for pattern, replacement in self.heading_patterns:
            text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
        logger.info("見出し変換完了")
        
        # 4. その他の整形
        for pattern, replacement in self.format_patterns:
            text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
        logger.info("一般フォーマット変換完了")
        
        # 変換後のテキストの行数をログに出力
        logger.info(f"変換完了: {len(text.splitlines())}行のMarkdown")
        
        return text
    
    def convert_file(self, input_file, output_file):
        """
        ファイルを読み込み、変換して保存します
        
        Args:
            input_file (str): 入力ファイルのパス
            output_file (str): 出力ファイルのパス
            
        Returns:
            bool: 変換が成功したかどうか
        """
        try:
            # ファイルを読み込む
            with open(input_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # テキストを変換
            markdown_text = self.convert_text(text)
            
            # 変換結果を保存
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_text)
            
            logger.info(f"ファイル変換成功: {input_file} → {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"ファイル変換エラー: {str(e)}")
            return False


def main():
    """
    コマンドライン引数を解析し、OCRテキスト→Markdown変換を実行
    """
    parser = argparse.ArgumentParser(description='OCRテキストをMarkdown形式に変換します')
    parser.add_argument('input_file', help='入力OCRテキストファイルのパス')
    parser.add_argument('output_file', help='出力Markdownファイルのパス')
    
    args = parser.parse_args()
    
    # 入力ファイルの存在を確認
    if not os.path.exists(args.input_file):
        logger.error(f"入力ファイルが見つかりません: {args.input_file}")
        return
    
    # 出力ディレクトリの存在を確認し、なければ作成
    output_dir = os.path.dirname(args.output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 変換を実行
    converter = OCRToMarkdownConverter()
    converter.convert_file(args.input_file, args.output_file)


if __name__ == "__main__":
    main() 
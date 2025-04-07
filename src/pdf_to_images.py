#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDFファイルをページごとに画像に変換するスクリプト

このスクリプトは、指定されたPDFファイルをPopplerを使用して
ページごとに画像ファイル（PNG/JPEG）に変換します。

仕様:
- 入力: PDFファイルパス
- 出力: 画像ファイル（ページごと）
- オプション: DPI設定、出力形式（PNG/JPEG）、出力ディレクトリ

制限事項:
- Popplerがシステムにインストールされている必要があります
- 大きなPDFファイルは処理に時間がかかることがあります
"""

import os
import argparse
from pdf2image import convert_from_path
import logging

class PdfToImageConverter:
    """
    PDFファイルを画像に変換するクラス
    
    @param {string} pdf_path - 入力PDFファイルのパス
    @param {string} output_dir - 出力画像を保存するディレクトリ
    @param {number} dpi - 画像のDPI設定
    @param {string} format - 出力画像のフォーマット（'png'または'jpeg'）
    """
    def __init__(self, pdf_path, output_dir, dpi=300, format='png'):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.dpi = dpi
        self.format = format
        
        # 出力ディレクトリが存在しない場合は作成
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # ベースファイル名（拡張子なし）を取得
        self.base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # ロガーの設定
        self.logger = logging.getLogger(__name__)
        
    def convert(self):
        """
        PDFを画像に変換する処理を実行
        
        @return {list} 生成された画像ファイルのパスリスト
        """
        try:
            self.logger.info(f"PDFファイル「{self.pdf_path}」の変換を開始します...")
            
            # PDFを画像に変換
            images = convert_from_path(
                self.pdf_path, 
                dpi=self.dpi, 
                fmt=self.format
            )
            
            # 生成されたファイルパスのリスト
            output_files = []
            
            # 各ページを画像として保存
            for i, image in enumerate(images):
                # 出力ファイルパスを作成
                output_file = os.path.join(
                    self.output_dir, 
                    f"{self.base_filename}_page_{i+1:03d}.{self.format}"
                )
                
                # 画像を保存
                image.save(output_file)
                output_files.append(output_file)
                
                self.logger.info(f"ページ {i+1}/{len(images)} を {output_file} として保存しました")
            
            self.logger.info(f"PDFの変換が完了しました。合計 {len(images)} ページを変換しました。")
            return output_files
            
        except Exception as e:
            self.logger.error(f"PDF変換中にエラーが発生しました: {str(e)}")
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
    parser = argparse.ArgumentParser(description='PDFファイルを画像に変換')
    parser.add_argument('pdf_file', help='入力PDFファイルのパス')
    parser.add_argument('--output_dir', '-o', default='../data/images', 
                        help='出力画像を保存するディレクトリ（デフォルト: ../data/images）')
    parser.add_argument('--dpi', '-d', type=int, default=300, 
                        help='画像のDPI設定（デフォルト: 300）')
    parser.add_argument('--format', '-f', choices=['png', 'jpeg'], default='png', 
                        help='出力画像のフォーマット（デフォルト: png）')
    
    args = parser.parse_args()
    
    try:
        # PDFを画像に変換
        converter = PdfToImageConverter(
            pdf_path=args.pdf_file,
            output_dir=args.output_dir,
            dpi=args.dpi,
            format=args.format
        )
        output_files = converter.convert()
        
        logger.info(f"変換完了: {len(output_files)} ファイルが {args.output_dir} に保存されました")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 
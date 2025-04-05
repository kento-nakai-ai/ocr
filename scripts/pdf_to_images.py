#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDFファイルを画像ファイル（PNG/JPEG）に変換するスクリプト

このスクリプトは、指定されたPDFファイルをページごとに画像ファイルに変換します。
Poppler（pdf2image）を使用してPDFを高解像度の画像に変換し、OCR処理に最適な
画像ファイルを生成します。

要件:
    - Poppler: PDFのレンダリングエンジン
    - pdf2image: PopplerのPythonラッパー

使用例:
    python pdf_to_images.py input.pdf --output_dir ./images --dpi 300 --format png
"""

import os
import argparse
from pdf2image import convert_from_path


def pdfToImages(pdf_path, output_dir=None, dpi=300, fmt='png', prefix=None):
    """
    PDFファイルをページごとに画像ファイルに変換します

    Args:
        pdf_path (str): 変換対象のPDFファイルのパス
        output_dir (str, optional): 出力先ディレクトリ。指定がない場合はPDFと同じディレクトリ
        dpi (int, optional): 出力画像の解像度（DPI）。デフォルトは300
        fmt (str, optional): 出力画像のフォーマット（'png'または'jpeg'）。デフォルトは'png'
        prefix (str, optional): 出力ファイル名のプレフィックス。指定がない場合はPDFのファイル名

    Returns:
        list: 生成された画像ファイルのパスのリスト
    """
    # 出力ディレクトリの設定
    if output_dir is None:
        output_dir = os.path.dirname(pdf_path)
    
    # 出力ディレクトリがなければ作成
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # プレフィックスの設定
    if prefix is None:
        prefix = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # PDFをページごとに画像に変換
    try:
        print(f"PDFを変換中: {pdf_path}")
        print(f"解像度: {dpi} DPI, 形式: {fmt}")
        
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            fmt=fmt,
            thread_count=os.cpu_count()
        )
        
        # 画像を保存
        output_paths = []
        for i, image in enumerate(images):
            page_num = i + 1
            output_filename = f"{prefix}_page{page_num:02d}.{fmt}"
            output_path = os.path.join(output_dir, output_filename)
            
            image.save(output_path)
            output_paths.append(output_path)
            print(f"ページ {page_num}/{len(images)} を保存: {output_path}")
        
        print(f"変換完了: {len(images)}ページを{output_dir}に保存しました")
        return output_paths
    
    except Exception as e:
        print(f"エラー: PDFの変換に失敗しました: {str(e)}")
        return []


def main():
    """
    コマンドライン引数を解析し、PDFを画像に変換する処理を実行します
    """
    parser = argparse.ArgumentParser(description='PDFをページごとに画像ファイルに変換します')
    parser.add_argument('pdf_path', help='変換するPDFファイルのパス')
    parser.add_argument('--output_dir', '-o', help='出力先ディレクトリ')
    parser.add_argument('--dpi', '-d', type=int, default=300, help='出力画像の解像度（DPI）')
    parser.add_argument('--format', '-f', choices=['png', 'jpeg'], default='png', help='出力画像のフォーマット')
    parser.add_argument('--prefix', '-p', help='出力ファイル名のプレフィックス')
    
    args = parser.parse_args()
    
    pdfToImages(
        args.pdf_path,
        args.output_dir,
        args.dpi,
        args.format,
        args.prefix
    )


if __name__ == "__main__":
    main() 
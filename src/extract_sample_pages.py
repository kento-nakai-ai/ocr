"""
PDFファイルからサンプルとして10ページ分を抽出するモジュール

このモジュールは、指定したPDFファイルから10ページ分を抽出し、新しいPDFファイルとして保存します。
抽出するページは、均等に分布するように選択されます。

制限事項:
- PyPDF2ライブラリに依存します
- 非常に大きなPDFファイルの処理には時間がかかる場合があります
"""

import os
import sys
import argparse
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter

def extract_sample_pages(input_pdf_path: str, output_pdf_path: str, num_pages: int = 10) -> bool:
    """
    PDFファイルから指定した数のページをサンプルとして抽出する

    Args:
        input_pdf_path (str): 入力PDFファイルのパス
        output_pdf_path (str): 出力PDFファイルのパス
        num_pages (int, optional): 抽出するページ数。デフォルトは10

    Returns:
        bool: 処理が成功した場合はTrue、失敗した場合はFalse
    """
    try:
        # PDFファイルを開く
        reader = PdfReader(input_pdf_path)
        writer = PdfWriter()
        
        # PDFの総ページ数を取得
        total_pages = len(reader.pages)
        
        if total_pages <= num_pages:
            print(f"指定されたPDFは{total_pages}ページしかありません。すべてのページを抽出します。")
            for i in range(total_pages):
                writer.add_page(reader.pages[i])
        else:
            # 抽出するページのインデックスを計算（均等に分布）
            step = total_pages / num_pages
            page_indices = [int(i * step) for i in range(num_pages)]
            
            # 最後のページを確実に含める
            if total_pages - 1 not in page_indices:
                page_indices[-1] = total_pages - 1
            
            # ページを抽出
            for i in page_indices:
                writer.add_page(reader.pages[i])
            
            print(f"抽出したページ: {page_indices}")
        
        # 新しいPDFファイルとして保存
        writer.write(output_pdf_path)
        print(f"サンプルPDFを保存しました: {output_pdf_path}")
        return True
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return False

def main():
    """
    コマンドライン引数を解析して処理を実行する
    """
    parser = argparse.ArgumentParser(description="PDFからサンプルページを抽出します")
    parser.add_argument("input_pdf", help="入力PDFファイルのパス")
    parser.add_argument("-o", "--output", help="出力PDFファイルのパス")
    parser.add_argument("-n", "--num-pages", type=int, default=10, help="抽出するページ数（デフォルト: 10）")
    
    args = parser.parse_args()
    
    # 入力ファイルの存在確認
    if not os.path.isfile(args.input_pdf):
        print(f"エラー: 入力ファイル '{args.input_pdf}' が見つかりません")
        return 1
    
    # 出力ファイルパスが指定されていない場合はデフォルトを設定
    if not args.output:
        input_name = os.path.basename(args.input_pdf)
        input_base = os.path.splitext(input_name)[0]
        args.output = f"{input_base}_sample.pdf"
    
    # ページを抽出
    success = extract_sample_pages(args.input_pdf, args.output, args.num_pages)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 
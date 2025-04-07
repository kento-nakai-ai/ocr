"""
PDFファイルをMarkdown形式に変換するモジュール（Gemini 2.5 Pro利用）

このモジュールは、PDFファイルをGemini 2.5 ProのAI機能を使用してMarkdown形式に変換します。
指定されたPDFファイルを処理し、結果を出力ファイルに保存します。

制限事項:
- Geminiの入出力トークン制限に依存します
- Google Cloud APIキーが必要です（.envファイルに設定）
"""

import os
import sys
import base64
from pathlib import Path
from dotenv import load_dotenv

import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError

# 環境変数の読み込み
load_dotenv()

MODEL_NAME = "gemini-2.5-pro-exp-03-25"
MODEL_NAME_FOR_OUTPUT = "gemini-2.5-pro-exp-03-25"
API_KEY = os.getenv("GEMINI_API_KEY", "your_api_key_here")
SYSTEM_PROMPT = "このPDFの内容を余すことなくmarkdown形式に変換してください。また、内容はまとめないでオリジナルの内容をそのまま複写することを意識してください。出力はmarkdown形式のみ、不要な出力はしないでください。"

def setup_gemini():
    """
    Gemini APIの初期設定を行う

    Returns:
        None
    """
    genai.configure(api_key=API_KEY)

def pdf2md(pdf_filepath: str) -> str:
    """
    PDFファイルをMarkdown形式に変換する

    Args:
        pdf_filepath (str): 変換対象のPDFファイルパス

    Returns:
        str: 変換されたMarkdown形式のテキスト
    """
    try:
        # 変換対象のPDFをバイナリデータとして取得
        with open(pdf_filepath, "rb") as pdf_file:
            pdf_data = pdf_file.read()
        
        # GeminiのPDF処理モデルを設定
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config={
                "max_output_tokens": 8192,
                "temperature": 0.0,
                "top_p": 0.95,
            }
        )
        
        # PDFとプロンプトを送信
        response = model.generate_content(
            [
                {
                    "mime_type": "application/pdf",
                    "data": pdf_data
                },
                SYSTEM_PROMPT
            ]
        )
        
        # トークン使用状況の表示（APIがサポートしていれば）
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            print(f"入力トークン: {response.usage_metadata.prompt_token_count}")
            print(f"出力トークン: {response.usage_metadata.candidates_token_count}")
            print(f"合計トークン: {response.usage_metadata.prompt_token_count + response.usage_metadata.candidates_token_count}")
        
        # レスポンスからテキストを抽出
        return response.text
    
    except GoogleAPIError as e:
        print(f"Gemini API エラー: {e}")
        return f"# 変換エラー\n\nGemini APIでエラーが発生しました: {e}"
    except Exception as e:
        print(f"予期せぬエラー: {e}")
        return f"# 変換エラー\n\n処理中にエラーが発生しました: {e}"

def list_files_in_folder(folder_path: str) -> list[str]:
    """
    指定したフォルダ内のファイル一覧を取得する

    Args:
        folder_path (str): ファイル一覧を取得するフォルダのパス

    Returns:
        list[str]: ファイル名のリスト
    """
    try:
        # 指定したフォルダ内のファイル一覧を取得
        files = os.listdir(folder_path)
        # ファイルのみをフィルタリング
        file_list = [f for f in files if os.path.isfile(os.path.join(folder_path, f))]
        return file_list
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return []

if __name__ == "__main__":
    # コマンドライン引数の確認
    if len(sys.argv) < 2:
        print("使用方法: python pdf2md_gemini.py <input_pdf_path> [output_md_path]")
        sys.exit(1)
    
    input_pdf_path = sys.argv[1]
    
    # 出力ファイルパス（省略可能）
    if len(sys.argv) >= 3:
        output_md_path = sys.argv[2]
    else:
        # デフォルトの出力パスを設定
        output_dir = "./src/output"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        output_basename = os.path.basename(input_pdf_path).replace(".pdf", ".md")
        output_md_path = f"{output_dir}/{MODEL_NAME_FOR_OUTPUT}_{output_basename}"
    
    # APIキーの確認
    if API_KEY == "your_api_key_here" or not API_KEY:
        print("Gemini APIキーが設定されていません。.envファイルにGEMINI_API_KEYを設定してください。")
        exit(1)
    
    # Gemini APIを初期化
    setup_gemini()
    
    print(f"処理ファイル: {os.path.basename(input_pdf_path)}")
    
    # PDFをMarkdownに変換
    md_content = pdf2md(input_pdf_path)
    
    # 出力ディレクトリを作成（必要な場合）
    output_dir = os.path.dirname(output_md_path)
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 出力されたMarkdownを保存
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    print(f"変換完了: {output_md_path}") 
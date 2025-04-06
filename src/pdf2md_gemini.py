"""
PDFファイルをMarkdown形式に変換するモジュール（Gemini利用）

このモジュールは、PDFファイルをGeminiのAI機能を使用してMarkdown形式に変換します。
入力フォルダ内のすべてのPDFファイルを処理し、結果を出力フォルダに保存します。

制限事項:
- Geminiの入出力トークン制限に依存します
- Google Cloud APIキーが必要です（.envファイルに設定）
"""

import os
import base64
from pathlib import Path
from dotenv import load_dotenv

import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError

# 環境変数の読み込み
load_dotenv()

MODEL_NAME = "gemini-1.5-pro-latest"
MODEL_NAME_FOR_OUTPUT = "gemini-1.5-pro"
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
    # 入出力ディレクトリの確認と作成
    Path("./src/input").mkdir(parents=True, exist_ok=True)
    Path("./src/output").mkdir(parents=True, exist_ok=True)
    
    # APIキーの確認
    if API_KEY == "your_api_key_here" or not API_KEY:
        print("Gemini APIキーが設定されていません。.envファイルにGEMINI_API_KEYを設定してください。")
        exit(1)
    
    # Gemini APIを初期化
    setup_gemini()
    
    # 入力フォルダ内のPDFファイルを処理
    pdf_files = [f for f in list_files_in_folder("./src/input") if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("処理対象のPDFファイルが見つかりません。src/inputディレクトリにPDFファイルを配置してください。")
        exit(0)
    
    for pdf_file in pdf_files:            
        print(f"処理ファイル: {pdf_file}")
        
        # PDFをMarkdownに変換
        md_content = pdf2md(f"./src/input/{pdf_file}")
        
        # 出力されたMarkdownを保存
        output_file = pdf_file.replace(".pdf", ".md")
        output_path = f"./src/output/{MODEL_NAME_FOR_OUTPUT}_{output_file}"
        
        # ファイルに書き込み
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        print(f"変換完了: {output_path}") 
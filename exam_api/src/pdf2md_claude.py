"""
PDFファイルをMarkdown形式に変換するモジュール（Claude 3.7 Sonnet利用）

このモジュールは、PDFファイルをClaude 3.7 SonnetのAI機能を使用してMarkdown形式に変換します。
指定されたPDFファイルを処理し、結果を出力ファイルに保存します。

制限事項:
- Claudeの入出力トークン制限に依存します
- APIキーが必要です（.envファイルに設定）
"""

import os
import sys
import base64
from pathlib import Path
from dotenv import load_dotenv

import anthropic

# 環境変数の読み込み
load_dotenv()

MODEL_NAME = "claude-3-7-sonnet-20240307"
MODEL_NAME_FOR_OUTPUT = "claude-3-7-sonnet"
API_TOKEN = os.getenv("CLAUDE_API_KEY", "sk-xxx")
SYSTEM_PROMPT = "このPDFの内容を余すことなくmarkdown形式に変換してください。また、内容はまとめないでオリジナルの内容をそのまま複写することを意識してください。出力はmarkdown形式のみ、不要な出力はしないでください。"

def pdf2md(pdf_filepath: str):
    """
    PDFファイルをMarkdown形式に変換する

    Args:
        pdf_filepath (str): 変換対象のPDFファイルパス

    Returns:
        str: 変換されたMarkdown形式のテキスト
    """
    # 変換対象のPDFをバイナリデータとして取得
    with open(pdf_filepath, "rb") as pdf_file:
        # Setp 1: basee64 encode pdf
        pdf_data = base64.b64encode(pdf_file.read()).decode("utf-8")

    # LLMの設定
    client = anthropic.Anthropic(api_key=API_TOKEN)
    # アップロードしたPDFをmarkdown形式に変換するようLLMに指示
    response = client.beta.messages.create(
        model=MODEL_NAME,
        betas=["pdfs-2024-09-25"],
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_data
                        }
                    },
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT
                    }
                ]
            }
        ],
    )

    # 消費したトークンの表示
    print(f"input token: {response.usage.input_tokens}")
    print(f"output token: {response.usage.output_tokens}")
    print(f"total token: {response.usage.input_tokens + response.usage.output_tokens}")
    return ''.join([chunk.text for chunk in response.content])

# inputフォルダにあるPDFファイル名一覧を取得
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
        print("使用方法: python pdf2md_claude.py <input_pdf_path> [output_md_path]")
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
    
    print(f"処理ファイル: {os.path.basename(input_pdf_path)}")
    
    # pdfをmarkdownに変換
    md_content = pdf2md(input_pdf_path)
    
    # 出力ディレクトリを作成（必要な場合）
    output_dir = os.path.dirname(output_md_path)
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 出力されたmarkdownを.md形式の新規ファイルに書き込む
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    print(f"変換完了: {output_md_path}") 
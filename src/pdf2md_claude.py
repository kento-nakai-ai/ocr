"""
PDFファイルをMarkdown形式に変換するモジュール（Claude利用）

このモジュールは、PDFファイルをClaudeのAI機能を使用してMarkdown形式に変換します。
入力フォルダ内のすべてのPDFファイルを処理し、結果を出力フォルダに保存します。

制限事項:
- Claudeの入出力トークン制限に依存します
- APIキーが必要です（.envファイルに設定）
"""

import os
import base64
from pathlib import Path
from dotenv import load_dotenv

import anthropic

# 環境変数の読み込み
load_dotenv()

MODEL_NAME = "claude-3-5-sonnet-20241022"
MODEL_NAME_FOR_OUTPUT = "claude-3-5-sonnet"
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
        model="claude-3-5-sonnet-20241022",
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
    # 入出力ディレクトリの確認と作成
    Path("./src/input").mkdir(parents=True, exist_ok=True)
    Path("./src/output").mkdir(parents=True, exist_ok=True)
    
    # 入力フォルダのPDFファイルを処理
    pdf_files = [f for f in list_files_in_folder("./src/input") if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("処理対象のPDFファイルが見つかりません。src/inputディレクトリにPDFファイルを配置してください。")
        exit(0)
    
    for pdf_file in pdf_files:
        print(f"処理ファイル: {pdf_file}")
        # pdfをmarkdownに変換
        md_content = pdf2md(f"./src/input/{pdf_file}")

        # 出力されたmarkdownを.md形式の新規ファイルに書き込む
        output_file = pdf_file.replace(".pdf", ".md")
        with open(f"./src/output/{MODEL_NAME_FOR_OUTPUT}_{output_file}", "w", encoding="utf-8") as f:
           f.write(md_content)
        
        print(f"変換完了: {output_file}") 
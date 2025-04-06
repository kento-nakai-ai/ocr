#!/bin/bash

# ====================================================================================
# PDFサンプル抽出 + OCR処理実行スクリプト
# ====================================================================================
#
# このスクリプトは、指定されたPDFファイルからサンプルとして10ページを抽出し、
# 抽出したサンプルに対してOCR処理を実行します。
#
# 使用例:
#   ./extract_sample.sh path/to/document.pdf --use-llm --claude
#
# 作者: OCRプロジェクトチーム
# ====================================================================================

# スクリプトが存在するディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# プロジェクトのルートディレクトリを設定
ROOT_DIR="$SCRIPT_DIR"
# スクリプトディレクトリを設定
SCRIPTS_DIR="$ROOT_DIR/src"
# データディレクトリを設定
DATA_DIR="$ROOT_DIR/data"
# ソースディレクトリを設定
SRC_DIR="$ROOT_DIR/src"

# 各種データディレクトリ
PDF_DIR="$DATA_DIR/pdf"
IMAGES_DIR="$DATA_DIR/images"
OCR_DIR="$DATA_DIR/ocr"
MARKDOWN_DIR="$DATA_DIR/markdown"

# デフォルト設定
DEFAULT_DPI=300
DEFAULT_FORMAT="png"
DEFAULT_PAGES=10
DEFAULT_PARALLEL=4

# コマンドライン引数のパース
PDF_FILE=""
USE_LLM=false
USE_CLAUDE=false
USE_GEMINI=false
DPI=$DEFAULT_DPI
FORMAT=$DEFAULT_FORMAT
PAGES=$DEFAULT_PAGES
PARALLEL=$DEFAULT_PARALLEL

# ヘルプメッセージ
function show_help {
    echo "使用方法: $0 <pdf_file> [オプション]"
    echo ""
    echo "オプション:"
    echo "  --output DIR        出力ディレクトリを指定（デフォルト: $DATA_DIR）"
    echo "  --dpi NUM           画像変換時のDPI値を指定（デフォルト: $DEFAULT_DPI）"
    echo "  --format FORMAT     出力画像のフォーマット（png/jpeg、デフォルト: $DEFAULT_FORMAT）"
    echo "  --pages NUM         抽出するページ数を指定（デフォルト: $DEFAULT_PAGES）"
    echo "  --use-llm           OCRにLLMベースの処理を使用する"
    echo "  --claude            画像解析にClaude APIを使用する"
    echo "  --gemini            画像解析にGemini APIを使用する（デフォルト）"
    echo "  --parallel NUM      並列処理数を指定（デフォルト: $DEFAULT_PARALLEL）"
    echo "  --help              このヘルプを表示する"
    echo ""
    echo "例: $0 data/pdf/sample.pdf --use-llm --claude --pages 10"
    exit 1
}

# 引数がない場合はヘルプを表示
if [ $# -eq 0 ]; then
    show_help
fi

# 最初の引数がPDFファイルパスの場合
if [[ "$1" != --* && "$1" != "" ]]; then
    PDF_FILE="$1"
    shift
fi

# 残りの引数を解析
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output)
            DATA_DIR="$2"
            PDF_DIR="$DATA_DIR/pdf"
            IMAGES_DIR="$DATA_DIR/images"
            OCR_DIR="$DATA_DIR/ocr"
            MARKDOWN_DIR="$DATA_DIR/markdown"
            shift 2
            ;;
        --dpi)
            DPI="$2"
            shift 2
            ;;
        --format)
            FORMAT="$2"
            shift 2
            ;;
        --pages)
            PAGES="$2"
            shift 2
            ;;
        --use-llm)
            USE_LLM=true
            shift
            ;;
        --claude)
            USE_CLAUDE=true
            shift
            ;;
        --gemini)
            USE_GEMINI=true
            shift
            ;;
        --parallel)
            PARALLEL="$2"
            shift 2
            ;;
        --help)
            show_help
            ;;
        *)
            echo "エラー: 不明なオプション '$1'"
            show_help
            ;;
    esac
done

# PDFファイルが指定されているか確認
if [ -z "$PDF_FILE" ]; then
    echo "エラー: PDFファイルを指定してください"
    show_help
fi

# PDFファイルが存在するか確認
if [ ! -f "$PDF_FILE" ]; then
    echo "エラー: 指定されたPDFファイル '$PDF_FILE' が見つかりません"
    exit 1
fi

# 必要なディレクトリを作成
mkdir -p "$PDF_DIR" "$IMAGES_DIR" "$OCR_DIR" "$MARKDOWN_DIR"

# PDFファイル名（拡張子なし）を取得
PDF_BASENAME=$(basename "$PDF_FILE" .pdf)

# 出力ファイル名を設定
SAMPLE_PDF="$PDF_DIR/${PDF_BASENAME}_sample.pdf"

echo "========================================================"
echo "PDFサンプル抽出 + OCR処理パイプライン"
echo "========================================================"
echo "処理対象: $PDF_FILE"
echo "サンプルPDF: $SAMPLE_PDF"
echo "抽出ページ数: $PAGES"
echo "出力ディレクトリ: $DATA_DIR"
echo "処理設定:"
echo "  - DPI: $DPI"
echo "  - 画像フォーマット: $FORMAT"
echo "  - LLMベースOCR: $USE_LLM"
echo "  - Claude画像解析: $USE_CLAUDE"
echo "  - Gemini画像解析: $USE_GEMINI"
echo "========================================================"

# ステップ1: サンプルPDFの抽出
echo "ステップ1: サンプルPDFを抽出しています..."
python3 "$SRC_DIR/extract_sample_pages.py" "$PDF_FILE" --output "$SAMPLE_PDF" --num-pages "$PAGES"

if [ ! -f "$SAMPLE_PDF" ]; then
    echo "エラー: サンプルPDFの抽出に失敗しました"
    exit 1
fi

# ステップ2: サンプルPDFを画像に変換
echo "ステップ2: サンプルPDFを画像に変換しています..."
SAMPLE_BASENAME=$(basename "$SAMPLE_PDF" .pdf)
SAMPLE_IMAGES_DIR="$IMAGES_DIR/$SAMPLE_BASENAME"
mkdir -p "$SAMPLE_IMAGES_DIR"

# pdf2imageを使ってPDFを画像に変換
python3 -c "
import os
from pdf2image import convert_from_path

# PDFを画像に変換
images = convert_from_path('$SAMPLE_PDF', dpi=$DPI)

# 画像を保存
for i, image in enumerate(images):
    image.save(os.path.join('$SAMPLE_IMAGES_DIR', f'page_{i+1:03d}.$FORMAT'), '$FORMAT')

print(f'{len(images)}ページの画像を {len(images)} 個の $FORMAT ファイルに変換しました')
"

# ステップ3: OCR処理
echo "ステップ3: OCR処理を実行しています..."
SAMPLE_OCR_DIR="$OCR_DIR/$SAMPLE_BASENAME"
mkdir -p "$SAMPLE_OCR_DIR"

# LLMベースのOCRを使用する場合
if [ "$USE_LLM" = true ]; then
    if [ "$USE_CLAUDE" = true ]; then
        echo "Claude APIを使用してOCR処理を実行します..."
        # サンプルPDFをMarkdownに変換
        python3 "$SRC_DIR/pdf2md_claude.py" "$SAMPLE_PDF" "$SAMPLE_OCR_DIR/${SAMPLE_BASENAME}_ocr.md"
    else
        echo "Gemini APIを使用してOCR処理を実行します..."
        # サンプルPDFをMarkdownに変換
        python3 "$SRC_DIR/pdf2md_gemini.py" "$SAMPLE_PDF" "$SAMPLE_OCR_DIR/${SAMPLE_BASENAME}_ocr.md"
    fi
else
    echo "従来のOCR処理を実行します..."
    # ここに従来のOCR処理のコードを記述
    echo "注意: 現在の実装ではLLMベースのOCRのみサポートしています。--use-llmオプションを指定してください。"
    exit 1
fi

echo "========================================================"
echo "サンプル抽出 + OCR処理 完了"
echo "========================================================"
echo "サンプルPDF: $SAMPLE_PDF"
echo "サンプル画像: $SAMPLE_IMAGES_DIR"
echo "OCR結果: $SAMPLE_OCR_DIR"
echo "========================================================" 
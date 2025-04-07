#!/bin/bash

# ====================================================================================
# PDFサンプル抽出 + OCR処理実行スクリプト
# ====================================================================================
#
# このスクリプトは、指定されたPDFファイルからサンプルとして指定ページ数を抽出し、
# 抽出したサンプルに対してOCR処理を実行します。
#
# 使用例:
#   ./extract_sample.sh path/to/document.pdf --use-llm --claude
#   ./extract_sample.sh path/to/document.pdf --use-llm --gemini --pages 15
#   ./extract_sample.sh path/to/document.pdf --use-llm --dpi 600 --format jpeg
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
CLAUDE_DIR="$DATA_DIR/claude"
GEMINI_DIR="$DATA_DIR/gemini"

# デフォルト設定
DEFAULT_DPI=300
DEFAULT_FORMAT="png"
DEFAULT_PAGES=10
DEFAULT_PARALLEL=4

# コマンドライン引数のパース
PDF_FILE=""
USE_LLM=false
USE_CLAUDE=false
USE_GEMINI=true
DPI=$DEFAULT_DPI
FORMAT=$DEFAULT_FORMAT
PAGES=$DEFAULT_PAGES
PARALLEL=$DEFAULT_PARALLEL
DIRECT_KATEX=false

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
    echo "  --direct-katex      画像から直接KaTeX形式に変換する（OCRをスキップ）"
    echo "  --parallel NUM      並列処理数を指定（デフォルト: $DEFAULT_PARALLEL）"
    echo "  --help              このヘルプを表示する"
    echo ""
    echo "例:"
    echo "  $0 data/pdf/sample.pdf --use-llm --claude --pages 10"
    echo "  $0 data/pdf/sample.pdf --use-llm --gemini --pages 15 --dpi 600"
    echo "  $0 data/pdf/sample.pdf --direct-katex --format jpeg"
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
            CLAUDE_DIR="$DATA_DIR/claude"
            GEMINI_DIR="$DATA_DIR/gemini"
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
            USE_GEMINI=false
            shift
            ;;
        --gemini)
            USE_GEMINI=true
            USE_CLAUDE=false
            shift
            ;;
        --direct-katex)
            DIRECT_KATEX=true
            USE_LLM=false # 直接KaTeX変換ではLLMベースOCRは不要
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
mkdir -p "$PDF_DIR" "$IMAGES_DIR" "$OCR_DIR" "$MARKDOWN_DIR" "$CLAUDE_DIR" "$GEMINI_DIR"

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
echo "  - 直接KaTeX変換: $DIRECT_KATEX"
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

# PyScriptでpdf2imageを使ってPDFを画像に変換
python3 "$SRC_DIR/pdf_to_images.py" "$SAMPLE_PDF" --output_dir "$SAMPLE_IMAGES_DIR" --dpi "$DPI" --format "$FORMAT"

if [ $? -ne 0 ]; then
    echo "エラー: 画像変換に失敗しました"
    exit 1
fi

# ステップ3: OCR処理 または 直接KaTeX変換
SAMPLE_OCR_DIR="$OCR_DIR/$SAMPLE_BASENAME"
SAMPLE_MARKDOWN_DIR="$MARKDOWN_DIR/$SAMPLE_BASENAME"
mkdir -p "$SAMPLE_OCR_DIR" "$SAMPLE_MARKDOWN_DIR"

if [ "$DIRECT_KATEX" = true ]; then
    echo "ステップ3: 画像から直接KaTeX形式に変換しています..."
    for img_file in "$SAMPLE_IMAGES_DIR"/*.$FORMAT; do
        base_name=$(basename "$img_file" .$FORMAT)
        python3 "$SRC_DIR/ocr_to_markdown.py" "$img_file" "$SAMPLE_MARKDOWN_DIR/${base_name}.md" --direct-image-to-katex
    done
else
    if [ "$USE_LLM" = true ]; then
        if [ "$USE_CLAUDE" = true ]; then
            echo "ステップ3: Claude APIを使用してOCR処理を実行します..."
            python3 "$SRC_DIR/pdf2md_claude.py" "$SAMPLE_PDF" "$SAMPLE_OCR_DIR/${SAMPLE_BASENAME}_ocr.md"
            
            # Markdown変換
            echo "ステップ4: Markdown形式に変換しています..."
            python3 "$SRC_DIR/ocr_to_markdown.py" "$SAMPLE_OCR_DIR" "$SAMPLE_MARKDOWN_DIR" --image-base-path "../images/$SAMPLE_BASENAME"
            
            # 画像解析
            echo "ステップ5: Claude APIで画像解析を実行します..."
            CLAUDE_OUTPUT_DIR="$CLAUDE_DIR/$SAMPLE_BASENAME"
            mkdir -p "$CLAUDE_OUTPUT_DIR"
            python3 "$SRC_DIR/claude_image_analyzer.py" --input "$SAMPLE_IMAGES_DIR" --output "$CLAUDE_OUTPUT_DIR"
        else
            echo "ステップ3: Gemini APIを使用してOCR処理を実行します..."
            python3 "$SRC_DIR/pdf2md_gemini.py" "$SAMPLE_PDF" "$SAMPLE_OCR_DIR/${SAMPLE_BASENAME}_ocr.md"
            
            # Markdown変換
            echo "ステップ4: Markdown形式に変換しています..."
            python3 "$SRC_DIR/ocr_to_markdown.py" "$SAMPLE_OCR_DIR" "$SAMPLE_MARKDOWN_DIR" --image-base-path "../images/$SAMPLE_BASENAME"
            
            # 画像解析
            echo "ステップ5: Gemini APIで画像解析を実行します..."
            GEMINI_OUTPUT_DIR="$GEMINI_DIR/$SAMPLE_BASENAME"
            mkdir -p "$GEMINI_OUTPUT_DIR"
            python3 "$SRC_DIR/gemini_image_analyzer.py" --input "$SAMPLE_IMAGES_DIR" --output "$GEMINI_OUTPUT_DIR"
        fi
    else
        echo "ステップ3: ローカルOCR処理を実行します..."
        python3 "$SRC_DIR/ocr_engine.py" "$SAMPLE_IMAGES_DIR" "$SAMPLE_OCR_DIR"
        
        # Markdown変換
        echo "ステップ4: Markdown形式に変換しています..."
        python3 "$SRC_DIR/ocr_to_markdown.py" "$SAMPLE_OCR_DIR" "$SAMPLE_MARKDOWN_DIR" --image-base-path "../images/$SAMPLE_BASENAME"
    fi
fi

echo "========================================================"
echo "サンプル抽出 + OCR処理 完了"
echo "========================================================"
echo "サンプルPDF: $SAMPLE_PDF"
echo "サンプル画像: $SAMPLE_IMAGES_DIR"
echo "OCR結果: $SAMPLE_OCR_DIR"
echo "Markdown結果: $SAMPLE_MARKDOWN_DIR"

if [ "$USE_CLAUDE" = true ]; then
    echo "Claude解析結果: $CLAUDE_DIR/$SAMPLE_BASENAME"
elif [ "$USE_GEMINI" = true ] && [ "$USE_LLM" = true ]; then
    echo "Gemini解析結果: $GEMINI_DIR/$SAMPLE_BASENAME"
fi

echo "========================================================" 
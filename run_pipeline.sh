#!/bin/bash

# ====================================================================================
# OCR + LLM + Markdown変換 + ベクターサーチ + マルチモーダル解析パイプライン実行スクリプト
# ====================================================================================
#
# このスクリプトは、PDFからの画像変換、OCR処理、Markdown変換、
# データベースへのインポート、マルチモーダル画像解析、エンベディング登録までの
# 一連の処理を自動化します。
#
# 使用例:
#   ./run_pipeline.sh path/to/document.pdf --use-llm --year 2024 --claude
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

# 各種データディレクトリ
PDF_DIR="$DATA_DIR/pdf"
IMAGES_DIR="$DATA_DIR/images"
OCR_DIR="$DATA_DIR/ocr"
MARKDOWN_DIR="$DATA_DIR/markdown"
EMBEDDING_DIR="$DATA_DIR/embedding"

# デフォルト設定
DEFAULT_DPI=300
DEFAULT_FORMAT="png"
DEFAULT_YEAR=2025
DEFAULT_QUESTION_PREFIX="Q"
DEFAULT_PARALLEL=4

# コマンドライン引数のパース
PDF_FILE=""
USE_LLM=false
USE_CLAUDE=false
USE_GEMINI=false
SKIP_OCR=false
SKIP_MARKDOWN=false
SKIP_DB=false
SKIP_EMBEDDING=false
DPI=$DEFAULT_DPI
FORMAT=$DEFAULT_FORMAT
YEAR=$DEFAULT_YEAR
QUESTION_PREFIX=$DEFAULT_QUESTION_PREFIX
PARALLEL=$DEFAULT_PARALLEL

# ヘルプメッセージ
function show_help {
    echo "使用方法: $0 <pdf_file> [オプション]"
    echo ""
    echo "オプション:"
    echo "  --output DIR        出力ディレクトリを指定（デフォルト: $DATA_DIR）"
    echo "  --dpi NUM           画像変換時のDPI値を指定（デフォルト: $DEFAULT_DPI）"
    echo "  --format FORMAT     出力画像のフォーマット（png/jpeg、デフォルト: $DEFAULT_FORMAT）"
    echo "  --year YEAR         問題の年度を指定（デフォルト: $DEFAULT_YEAR）"
    echo "  --prefix PREFIX     問題IDのプレフィックスを指定（デフォルト: $DEFAULT_QUESTION_PREFIX）"
    echo "  --use-llm           OCRにLLMベースの処理を使用する"
    echo "  --claude            画像解析にClaude APIを使用する"
    echo "  --gemini            画像解析にGemini APIを使用する（デフォルト）"
    echo "  --skip-ocr          OCR処理をスキップする（既にOCRデータがある場合）"
    echo "  --skip-markdown     Markdown変換をスキップする"
    echo "  --skip-db           DBインポートをスキップする"
    echo "  --skip-embedding    エンベディング処理をスキップする"
    echo "  --parallel NUM      並列処理数を指定（デフォルト: $DEFAULT_PARALLEL）"
    echo "  --help              このヘルプを表示する"
    echo ""
    echo "例: $0 data/pdf/sample.pdf --use-llm --year 2024 --claude"
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
            EMBEDDING_DIR="$DATA_DIR/embedding"
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
        --year)
            YEAR="$2"
            shift 2
            ;;
        --prefix)
            QUESTION_PREFIX="$2"
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
        --skip-ocr)
            SKIP_OCR=true
            shift
            ;;
        --skip-markdown)
            SKIP_MARKDOWN=true
            shift
            ;;
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        --skip-embedding)
            SKIP_EMBEDDING=true
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
mkdir -p "$PDF_DIR" "$IMAGES_DIR" "$OCR_DIR" "$MARKDOWN_DIR" "$EMBEDDING_DIR"

# PDFファイル名（拡張子なし）を取得
PDF_BASENAME=$(basename "$PDF_FILE" .pdf)

# PDFファイルをコピー（まだデータディレクトリにない場合）
if [ ! -f "$PDF_DIR/$PDF_BASENAME.pdf" ]; then
    echo "PDFファイルをデータディレクトリにコピーします..."
    cp "$PDF_FILE" "$PDF_DIR/$PDF_BASENAME.pdf"
fi

echo "========================================================"
echo "OCR + LLM + Markdown + ベクターサーチパイプライン"
echo "========================================================"
echo "処理対象: $PDF_FILE"
echo "出力ディレクトリ: $DATA_DIR"
echo "処理設定:"
echo "  - DPI: $DPI"
echo "  - 画像フォーマット: $FORMAT"
echo "  - 年度: $YEAR"
echo "  - 問題ID接頭辞: $QUESTION_PREFIX"
echo "  - LLMベースOCR: $USE_LLM"
echo "  - Claude画像解析: $USE_CLAUDE"
echo "  - Gemini画像解析: $USE_GEMINI"
echo "========================================================"

# PDFを画像に変換
echo "ステップ1: PDFを画像に変換しています..."
python "$SCRIPTS_DIR/pdf_to_images.py" "$PDF_DIR/$PDF_BASENAME.pdf" --output_dir "$IMAGES_DIR" --dpi "$DPI" --format "$FORMAT"

if [ $? -ne 0 ]; then
    echo "エラー: PDFの画像変換に失敗しました"
    exit 1
fi
echo "PDF → 画像変換が完了しました"

# OCR処理（スキップフラグがオフの場合）
if [ "$SKIP_OCR" = false ]; then
    echo "ステップ2: OCR処理を実行しています..."
    
    OCR_ARGS=("$IMAGES_DIR" "$OCR_DIR")
    
    if [ "$USE_LLM" = true ]; then
        OCR_ARGS+=("--use-llm")
        
        if [ "$USE_CLAUDE" = true ]; then
            OCR_ARGS+=("--llm-provider" "claude")
            echo "LLMベースOCR（Claude）を使用します"
        elif [ "$USE_GEMINI" = true ]; then
            OCR_ARGS+=("--llm-provider" "gemini")
            echo "LLMベースOCR（Gemini）を使用します"
        else
            OCR_ARGS+=("--llm-provider" "claude")
            echo "LLMベースOCR（デフォルト: Claude）を使用します"
        fi
    else
        echo "TesseractベースOCRを使用します"
    fi
    
    python "$SCRIPTS_DIR/ocr_engine.py" "${OCR_ARGS[@]}"
    
    if [ $? -ne 0 ]; then
        echo "エラー: OCR処理に失敗しました"
        exit 1
    fi
    echo "OCR処理が完了しました"
else
    echo "ステップ2: OCR処理はスキップされました"
fi

# Markdown変換（スキップフラグがオフの場合）
if [ "$SKIP_MARKDOWN" = false ]; then
    echo "ステップ3: OCRテキストをMarkdownに変換しています..."
    python "$SCRIPTS_DIR/ocr_to_markdown.py" "$OCR_DIR" "$MARKDOWN_DIR" --image-base-path "../images"
    
    if [ $? -ne 0 ]; then
        echo "エラー: Markdown変換に失敗しました"
        exit 1
    fi
    echo "Markdown変換が完了しました"
else
    echo "ステップ3: Markdown変換はスキップされました"
fi

# DBインポート（スキップフラグがオフの場合）
if [ "$SKIP_DB" = false ]; then
    echo "ステップ4: MarkdownをDBにインポートしています..."
    python "$SCRIPTS_DIR/markdown_importer.py" "$MARKDOWN_DIR" --year "$YEAR" --prefix "$QUESTION_PREFIX"
    
    if [ $? -ne 0 ]; then
        echo "エラー: DBインポートに失敗しました"
        exit 1
    fi
    echo "DBインポートが完了しました"
else
    echo "ステップ4: DBインポートはスキップされました"
fi

# 画像解析・エンベディング取得（スキップフラグがオフの場合）
if [ "$SKIP_EMBEDDING" = false ]; then
    echo "ステップ5: 画像解析とエンベディング取得を実行しています..."
    
    if [ "$USE_CLAUDE" = true ]; then
        echo "Claude APIを使用した画像解析を実行中..."
        # Claudes APIバージョンの画像解析を実行（必要に応じて実装を追加）
        echo "注：現在のスクリプトでは、ClaudeベースのAPIを直接サポートしていません。"
        echo "代わりにGemini APIを使用します（互換性のためにモデル名を変更）"
        
        # ClaudeのAPIキーをチェック
        if [ -z "$CLAUDE_API_KEY" ]; then
            echo "警告: CLAUDE_API_KEYが設定されていないようです。.envファイルを確認してください。"
        fi
        
        MODEL_NAME="claude-3-sonnet"
    elif [ "$USE_GEMINI" = true ] || [ "$USE_CLAUDE" = false -a "$USE_GEMINI" = false ]; then
        echo "Gemini APIを使用した画像解析を実行中..."
        
        # GeminiのAPIキーをチェック
        if [ -z "$GEMINI_API_KEY" ]; then
            echo "警告: GEMINI_API_KEYが設定されていないようです。.envファイルを確認してください。"
        fi
        
        MODEL_NAME="gemini-2.5-pro-exp-03-25"
    fi
    
    python "$SCRIPTS_DIR/gemini_image_analyzer.py" --input "$IMAGES_DIR" --output "$EMBEDDING_DIR" --model "$MODEL_NAME" --parallel "$PARALLEL"
    
    if [ $? -ne 0 ]; then
        echo "エラー: 画像解析・エンベディング取得に失敗しました"
        exit 1
    fi
    echo "画像解析・エンベディング取得が完了しました"
    
    echo "ステップ6: エンベディングをDBにインポートしています..."
    python "$SCRIPTS_DIR/embed_importer.py" --input "$EMBEDDING_DIR" --table "embeddings"
    
    if [ $? -ne 0 ]; then
        echo "エラー: エンベディングのDBインポートに失敗しました"
        exit 1
    fi
    echo "エンベディングのDBインポートが完了しました"
else
    echo "ステップ5-6: 画像解析・エンベディング処理はスキップされました"
fi

echo "========================================================"
echo "パイプライン処理が全て完了しました！"
echo "========================================================"
echo "処理結果:"
echo "  - PDF → 画像: $IMAGES_DIR"
echo "  - OCRテキスト: $OCR_DIR"
echo "  - Markdown: $MARKDOWN_DIR"
echo "  - エンベディング: $EMBEDDING_DIR"
echo "  - データベース: questionsテーブルおよびembeddingsテーブル"
echo ""
echo "以下のSQLでベクターサーチを実行できます:"
echo "SELECT q.question_id, q.year, q.content,"
echo "       e.embedding <-> to_query_vector(:input_vector) AS distance"
echo "  FROM questions q"
echo "  JOIN embeddings e ON q.question_id = e.question_id"
echo " ORDER BY distance ASC"
echo " LIMIT 10;"
echo "========================================================" 
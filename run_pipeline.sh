#!/bin/bash

# ====================================================================================
# OCR + LLM + Markdown変換 + ベクターサーチ（Aurora） + マルチモーダル解析パイプライン実行スクリプト
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

# デフォルト値の設定
PDF_FILE="" # PDFファイルのパス
OUTPUT_DIR="data" # 出力ディレクトリ
DPI=$DEFAULT_DPI # 画像変換時のDPI
FORMAT=$DEFAULT_FORMAT # 画像フォーマット
YEAR=$DEFAULT_YEAR # 対象年度
QUESTION_PREFIX=$DEFAULT_QUESTION_PREFIX # 問題IDのプレフィックス
USE_LLM=false # LLMベースのOCRを使用するかどうか
SKIP_OCR=false # OCR処理をスキップするかどうか
SKIP_MARKDOWN=false # Markdown変換をスキップするかどうか
SKIP_IMPORT=false # DBインポートをスキップするかどうか
SKIP_ANALYSIS=false # 画像解析をスキップするかどうか
SKIP_EMBEDDING=false # エンベディング生成をスキップするかどうか
SKIP_EMBED_IMPORT=false # エンベディングインポートをスキップするかどうか
PARALLEL=$DEFAULT_PARALLEL # 並列処理数
USE_CLAUDE=false # Claude APIを使用するかどうか
USE_GEMINI=true # Gemini APIを使用するかどうか（デフォルト）
DIRECT_KATEX=false # 画像から直接KaTeX形式に変換するかどうか
MULTIMODAL_EMBEDDING=false # マルチモーダルエンベディングを生成するかどうか
NO_API=false # API呼び出しを使用せずダミーエンベディングを生成するかどうか

# ヘルプ表示関数
function show_help {
  echo "使用方法: $0 PDF_FILE [オプション]"
  echo ""
  echo "オプション:"
  echo "  --output DIR         出力ディレクトリを指定（デフォルト: data）"
  echo "  --skip-ocr           OCR処理をスキップ（すでにデータがある場合）"
  echo "  --skip-markdown      Markdown変換をスキップ"
  echo "  --skip-import        DBインポートをスキップ"
  echo "  --skip-analysis      画像解析をスキップ"
  echo "  --skip-embedding     エンベディング生成をスキップ"
  echo "  --skip-embed-import  エンベディングのDBインポートをスキップ"
  echo "  --use-llm            LLMベースのOCRを使用（デフォルト: Tesseract）"
  echo "  --claude             画像解析にClaude APIを使用"
  echo "  --gemini             画像解析にGemini APIを使用（デフォルト）"
  echo "  --direct-katex       画像から直接KaTeX形式に変換（OCRをスキップ）"
  echo "  --multimodal-embedding 画像とテキストを組み合わせたマルチモーダルエンベディングを生成"
  echo "  --no-api             API呼び出しを使用せずダミーエンベディングを生成"
  echo "  --year YEAR          対象年度を指定（デフォルト: 2025）"
  echo "  --prefix PREFIX      問題IDのプレフィックスを指定（デフォルト: Q）"
  echo "  --dpi DPI            画像変換時のDPI値を指定（デフォルト: 300）"
  echo "  --format FORMAT      画像フォーマットを指定（png/jpeg、デフォルト: png）"
  echo "  --parallel N         並列処理数を指定（デフォルト: 4）"
  echo "  -h, --help           このヘルプを表示"
  echo ""
  echo "例:"
  echo "  $0 data/pdf/sample.pdf --use-llm --year 2024 --gemini"
  echo "  $0 data/pdf/sample.pdf --direct-katex --year 2024"
  echo "  $0 data/pdf/sample.pdf --use-llm --gemini --multimodal-embedding"
  echo ""
  exit 0
}

# パラメータが1つも指定されていない場合、またはヘルプオプションが指定された場合はヘルプを表示
if [ $# -eq 0 ] || [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  show_help
fi

# 最初の引数をPDFファイルとして取得
PDF_FILE="$1"
shift

# PDFファイルの存在確認
if [ ! -f "$PDF_FILE" ]; then
  echo "エラー: 指定されたPDFファイル '$PDF_FILE' が見つかりません。"
  exit 1
fi

# オプション引数の解析
while [ $# -gt 0 ]; do
  case "$1" in
    --output)
      OUTPUT_DIR="$2"
      PDF_DIR="$OUTPUT_DIR/pdf"
      IMAGES_DIR="$OUTPUT_DIR/images"
      OCR_DIR="$OUTPUT_DIR/ocr"
      MARKDOWN_DIR="$OUTPUT_DIR/markdown"
      EMBEDDING_DIR="$OUTPUT_DIR/embedding"
      shift 2
      ;;
    --skip-ocr)
      SKIP_OCR=true
      shift
      ;;
    --skip-markdown)
      SKIP_MARKDOWN=true
      shift
      ;;
    --skip-import)
      SKIP_IMPORT=true
      shift
      ;;
    --skip-analysis)
      SKIP_ANALYSIS=true
      shift
      ;;
    --skip-embedding)
      SKIP_EMBEDDING=true
      shift
      ;;
    --skip-embed-import)
      SKIP_EMBED_IMPORT=true
      shift
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
      SKIP_OCR=true # 直接KaTeX変換を使用する場合はOCRをスキップ
      shift
      ;;
    --multimodal-embedding)
      MULTIMODAL_EMBEDDING=true
      shift
      ;;
    --no-api)
      NO_API=true
      shift
      ;;
    --year)
      YEAR="$2"
      shift 2
      ;;
    --prefix)
      QUESTION_PREFIX="$2"
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
    --parallel)
      PARALLEL="$2"
      shift 2
      ;;
    *)
      echo "エラー: 不明なオプション '$1'"
      show_help
      ;;
  esac
done

# 必要なディレクトリの作成
mkdir -p "$PDF_DIR" "$IMAGES_DIR" "$OCR_DIR" "$MARKDOWN_DIR" "$EMBEDDING_DIR"
mkdir -p "$OUTPUT_DIR/claude" "$OUTPUT_DIR/gemini"

# PDFファイル名の取得（パスを除く）
PDF_FILENAME=$(basename "$PDF_FILE")
PDF_NAME="${PDF_FILENAME%.*}"

# ステップ1: PDFを画像に変換
echo "ステップ1: PDFをページごとに画像に変換中..."
python "$SCRIPTS_DIR/pdf_to_images.py" "$PDF_FILE" --output_dir "$IMAGES_DIR/$PDF_NAME" --dpi "$DPI" --format "$FORMAT"
echo "  -> 変換完了: $IMAGES_DIR/$PDF_NAME"

# ステップ2: OCR処理または直接KaTeX変換
if [ "$SKIP_OCR" = false ]; then
  echo "ステップ2: OCR処理中..."
  OCR_CMD="python $SCRIPTS_DIR/ocr_engine.py $IMAGES_DIR/$PDF_NAME $OCR_DIR/$PDF_NAME"
  
  if [ "$USE_LLM" = true ]; then
    OCR_CMD="$OCR_CMD --use-llm"
    if [ "$USE_CLAUDE" = true ]; then
      OCR_CMD="$OCR_CMD --llm-provider claude"
    elif [ "$USE_GEMINI" = true ]; then
      OCR_CMD="$OCR_CMD --llm-provider gemini"
    fi
  fi
  
  eval "$OCR_CMD"
  echo "  -> OCR完了: $OCR_DIR/$PDF_NAME"
fi

# ステップ3: Markdown変換
if [ "$SKIP_MARKDOWN" = false ]; then
  echo "ステップ3: OCRテキストをMarkdownに変換中..."
  
  if [ "$DIRECT_KATEX" = true ]; then
    # 画像から直接KaTeX形式に変換する場合
    for img_file in "$IMAGES_DIR/$PDF_NAME"/*.$FORMAT; do
      base_name=$(basename "$img_file" .$FORMAT)
      python "$SCRIPTS_DIR/ocr_to_markdown.py" "$img_file" "$MARKDOWN_DIR/$PDF_NAME/${base_name}.md" --direct-image-to-katex
    done
  else
    # 通常のOCRテキストからMarkdownへの変換
    python "$SCRIPTS_DIR/ocr_to_markdown.py" "$OCR_DIR/$PDF_NAME" "$MARKDOWN_DIR/$PDF_NAME" --image-base-path "../images/$PDF_NAME"
  fi
  
  echo "  -> Markdown変換完了: $MARKDOWN_DIR/$PDF_NAME"
fi

# ステップ4: MarkdownをDBにインポート
if [ "$SKIP_IMPORT" = false ]; then
  echo "ステップ4: MarkdownをDBにインポート中..."
  python "$SCRIPTS_DIR/markdown_importer.py" --input "$MARKDOWN_DIR/$PDF_NAME" --year "$YEAR" --prefix "$QUESTION_PREFIX"
  echo "  -> DBインポート完了"
fi

# ステップ5: 画像解析（マルチモーダルAPI）
if [ "$SKIP_ANALYSIS" = false ]; then
  echo "ステップ5: 画像解析（マルチモーダルAPI）中..."
  
  if [ "$USE_CLAUDE" = true ]; then
    ANALYSIS_CMD="python $SCRIPTS_DIR/claude_image_analyzer.py --input $IMAGES_DIR/$PDF_NAME --output $OUTPUT_DIR/claude/$PDF_NAME"
    eval "$ANALYSIS_CMD"
    echo "  -> Claude APIによる画像解析完了: $OUTPUT_DIR/claude/$PDF_NAME"
  elif [ "$USE_GEMINI" = true ]; then
    ANALYSIS_CMD="python $SCRIPTS_DIR/gemini_image_analyzer.py --input $IMAGES_DIR/$PDF_NAME --output $OUTPUT_DIR/gemini/$PDF_NAME"
    
    if [ "$MULTIMODAL_EMBEDDING" = true ]; then
      ANALYSIS_CMD="$ANALYSIS_CMD --multimodal-embedding"
    fi
    
    eval "$ANALYSIS_CMD"
    echo "  -> Gemini APIによる画像解析完了: $OUTPUT_DIR/gemini/$PDF_NAME"
  fi
fi

# ステップ6: エンベディング生成
if [ "$SKIP_EMBEDDING" = false ] && [ "$MULTIMODAL_EMBEDDING" = false ]; then
  echo "ステップ6: エンベディング生成中..."
  
  if [ "$USE_CLAUDE" = true ]; then
    EMBEDDING_CMD="python $SCRIPTS_DIR/generate_embedding.py --input $OUTPUT_DIR/claude/$PDF_NAME --dimension 1536 --parallel $PARALLEL"
  else
    EMBEDDING_CMD="python $SCRIPTS_DIR/generate_embedding.py --input $OUTPUT_DIR/gemini/$PDF_NAME --dimension 1536 --parallel $PARALLEL"
  fi
  
  if [ "$NO_API" = true ]; then
    EMBEDDING_CMD="$EMBEDDING_CMD --no-api"
  fi
  
  eval "$EMBEDDING_CMD"
  echo "  -> エンベディング生成完了"
fi

# ステップ7: エンベディングをDBにインポート
if [ "$SKIP_EMBED_IMPORT" = false ]; then
  echo "ステップ7: エンベディングをDBにインポート中..."
  
  if [ "$USE_CLAUDE" = true ]; then
    python "$SCRIPTS_DIR/embed_importer.py" --input "$OUTPUT_DIR/claude/$PDF_NAME" --table embeddings
  else
    python "$SCRIPTS_DIR/embed_importer.py" --input "$OUTPUT_DIR/gemini/$PDF_NAME" --table embeddings
  fi
  
  echo "  -> エンベディングのDBインポート完了"
fi

echo "パイプライン処理が完了しました！"
echo "出力ディレクトリ: $OUTPUT_DIR"
echo "処理結果:"
echo "  - PDF → 画像: $IMAGES_DIR/$PDF_NAME"
echo "  - OCRテキスト: $OCR_DIR/$PDF_NAME"
echo "  - Markdown: $MARKDOWN_DIR/$PDF_NAME"
echo "  - エンベディング: $EMBEDDING_DIR/$PDF_NAME"
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
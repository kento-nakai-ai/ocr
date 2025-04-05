#!/bin/bash

# OCRパイプラインの実行スクリプト
# PDF→画像→OCR→Markdown→DBインポート→画像解析までの一連の処理を実行します

# 処理終了時に表示するメッセージ
function finish {
  echo "処理が終了しました"
  exit 0
}

# エラー時に表示するメッセージと終了
function error_exit {
  echo "エラー: $1" >&2
  exit 1
}

# ヘルプの表示
function show_help {
  echo "使用方法: $0 <PDF_PATH> [OPTIONS]"
  echo ""
  echo "PDF→画像→OCR→Markdown→DBインポート→画像解析までの一連の処理を実行します"
  echo ""
  echo "オプション:"
  echo "  -o, --output DIR      出力ディレクトリを指定します（デフォルト: data/）"
  echo "  -d, --dpi NUM         画像変換時のDPI値を指定します（デフォルト: 300）"
  echo "  -f, --format FORMAT   出力画像のフォーマットを指定します（png/jpeg、デフォルト: png）"
  echo "  -y, --year YEAR       問題の年度を指定します（デフォルト: 2025）"
  echo "  -q, --question ID     問題IDのプレフィックスを指定します（デフォルト: Q）"
  echo "  -s, --skip-ocr        OCR処理をスキップします（既にOCRテキストがある場合）"
  echo "  -c, --claude          Claude APIによる画像解析を有効にします"
  echo "  -h, --help            このヘルプを表示します"
  echo ""
  exit 0
}

# 引数のパース
PDF_PATH=""
OUTPUT_DIR="data"
DPI=300
FORMAT="png"
YEAR="2025"
QUESTION_PREFIX="Q"
SKIP_OCR=false
RUN_CLAUDE=false

# 引数が無ければヘルプを表示
if [ $# -eq 0 ]; then
  show_help
fi

# 引数の解析
while [ $# -gt 0 ]; do
  case "$1" in
    -o|--output)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    -d|--dpi)
      DPI="$2"
      shift 2
      ;;
    -f|--format)
      FORMAT="$2"
      shift 2
      ;;
    -y|--year)
      YEAR="$2"
      shift 2
      ;;
    -q|--question)
      QUESTION_PREFIX="$2"
      shift 2
      ;;
    -s|--skip-ocr)
      SKIP_OCR=true
      shift
      ;;
    -c|--claude)
      RUN_CLAUDE=true
      shift
      ;;
    -h|--help)
      show_help
      ;;
    *)
      if [ -z "$PDF_PATH" ]; then
        PDF_PATH="$1"
      else
        error_exit "不明な引数: $1"
      fi
      shift
      ;;
  esac
done

# PDFパスの確認
if [ -z "$PDF_PATH" ]; then
  error_exit "PDFファイルを指定してください"
fi

if [ ! -f "$PDF_PATH" ]; then
  error_exit "指定されたPDFファイルが存在しません: $PDF_PATH"
fi

# 出力ディレクトリのセットアップ
PDF_NAME=$(basename "$PDF_PATH" .pdf)
IMAGES_DIR="${OUTPUT_DIR}/images/${PDF_NAME}"
OCR_DIR="${OUTPUT_DIR}/ocr/${PDF_NAME}"
MARKDOWN_DIR="${OUTPUT_DIR}/markdown/${PDF_NAME}"
CLAUDE_DIR="${OUTPUT_DIR}/claude/${PDF_NAME}"

mkdir -p "$IMAGES_DIR" "$OCR_DIR" "$MARKDOWN_DIR" "$CLAUDE_DIR"

echo "===================================================="
echo "OCRパイプライン開始"
echo "===================================================="
echo "入力PDF: $PDF_PATH"
echo "出力ディレクトリ: $OUTPUT_DIR"
echo "画像DPI: $DPI"
echo "画像形式: $FORMAT"
echo "問題年度: $YEAR"
echo "問題IDプレフィックス: $QUESTION_PREFIX"
echo "OCRスキップ: $SKIP_OCR"
echo "Claude画像解析: $RUN_CLAUDE"
echo "===================================================="
echo ""

# ステップ1: PDF→画像変換
echo "[ステップ1] PDF→画像変換を開始"
python scripts/pdf_to_images.py "$PDF_PATH" --output_dir "$IMAGES_DIR" --dpi "$DPI" --format "$FORMAT" || error_exit "PDF→画像変換に失敗しました"
echo "[ステップ1] PDF→画像変換が完了しました"
echo ""

# OCRのスキップ確認
if [ "$SKIP_OCR" = true ]; then
  echo "[ステップ2] OCR処理はスキップします"
else
  # ステップ2: 画像→OCR処理
  echo "[ステップ2] 画像→OCR処理を開始"
  
  # 必要なディレクトリの確認
  if [ ! -d "$IMAGES_DIR" ]; then
    error_exit "画像ディレクトリが見つかりません: $IMAGES_DIR"
  fi
  
  # 各画像に対してOCR処理を実行
  for IMAGE_FILE in "$IMAGES_DIR"/*.$FORMAT; do
    if [ ! -f "$IMAGE_FILE" ]; then
      continue
    fi
    
    IMAGE_NAME=$(basename "$IMAGE_FILE" .$FORMAT)
    OCR_OUTPUT="$OCR_DIR/${IMAGE_NAME}.txt"
    
    echo "OCR処理: $IMAGE_FILE"
    tesseract "$IMAGE_FILE" "$OCR_DIR/${IMAGE_NAME}" -l jpn --dpi "$DPI" || error_exit "OCR処理に失敗しました: $IMAGE_FILE"
    echo "OCR完了: $OCR_OUTPUT"
  done
  
  echo "[ステップ2] 画像→OCR処理が完了しました"
  echo ""
fi

# ステップ3: OCRテキスト→Markdown変換
echo "[ステップ3] OCRテキスト→Markdown変換を開始"

# 必要なディレクトリの確認
if [ ! -d "$OCR_DIR" ]; then
  error_exit "OCRテキストディレクトリが見つかりません: $OCR_DIR"
fi

# 各OCRテキストファイルに対してMarkdown変換を実行
for OCR_FILE in "$OCR_DIR"/*.txt; do
  if [ ! -f "$OCR_FILE" ]; then
    continue
  fi
  
  OCR_NAME=$(basename "$OCR_FILE" .txt)
  MARKDOWN_OUTPUT="$MARKDOWN_DIR/${OCR_NAME}.md"
  
  echo "Markdown変換: $OCR_FILE"
  python scripts/ocr_to_markdown.py "$OCR_FILE" "$MARKDOWN_OUTPUT" || error_exit "Markdown変換に失敗しました: $OCR_FILE"
  echo "Markdown変換完了: $MARKDOWN_OUTPUT"
done

echo "[ステップ3] OCRテキスト→Markdown変換が完了しました"
echo ""

# ステップ4: Markdown→DBインポート
echo "[ステップ4] Markdown→DBインポートを開始"

# 必要なディレクトリの確認
if [ ! -d "$MARKDOWN_DIR" ]; then
  error_exit "Markdownディレクトリが見つかりません: $MARKDOWN_DIR"
fi

# 各Markdownファイルに対してDBインポートを実行
for MARKDOWN_FILE in "$MARKDOWN_DIR"/*.md; do
  if [ ! -f "$MARKDOWN_FILE" ]; then
    continue
  fi
  
  MARKDOWN_NAME=$(basename "$MARKDOWN_FILE" .md)
  # Q001_page01 形式から Q001 のようなIDを抽出
  QUESTION_ID=$(echo "$MARKDOWN_NAME" | cut -d '_' -f 1)
  # プレフィックスが指定されている場合は置換
  if [ -n "$QUESTION_PREFIX" ]; then
    if [[ "$QUESTION_ID" != "$QUESTION_PREFIX"* ]]; then
      QUESTION_ID="${QUESTION_PREFIX}${QUESTION_ID}"
    fi
  fi
  
  echo "DBインポート: $MARKDOWN_FILE (ID: $QUESTION_ID)"
  python scripts/markdown_importer.py "$MARKDOWN_FILE" "$YEAR" "$QUESTION_ID" || error_exit "DBインポートに失敗しました: $MARKDOWN_FILE"
  echo "DBインポート完了: $QUESTION_ID"
done

echo "[ステップ4] Markdown→DBインポートが完了しました"
echo ""

# ステップ5: Claude画像解析（オプション）
if [ "$RUN_CLAUDE" = true ]; then
  echo "[ステップ5] Claude画像解析を開始"
  
  # Claude API キーの確認
  if [ -z "$CLAUDE_API_KEY" ]; then
    error_exit "環境変数 CLAUDE_API_KEY が設定されていません"
  fi
  
  # 必要なディレクトリの確認
  if [ ! -d "$IMAGES_DIR" ]; then
    error_exit "画像ディレクトリが見つかりません: $IMAGES_DIR"
  fi
  
  # 画像解析の実行
  echo "バッチ画像解析: $IMAGES_DIR"
  python scripts/claude_image_analyzer.py --batch "$IMAGES_DIR" --output_dir "$CLAUDE_DIR" --save_to_db || error_exit "Claude画像解析に失敗しました"
  echo "[ステップ5] Claude画像解析が完了しました"
  echo ""
else
  echo "[ステップ5] Claude画像解析はスキップします"
  echo ""
fi

echo "===================================================="
echo "処理完了サマリー:"
echo "画像ファイル数: $(find "$IMAGES_DIR" -name "*.$FORMAT" | wc -l)"
echo "OCRテキストファイル数: $(find "$OCR_DIR" -name "*.txt" | wc -l)"
echo "Markdownファイル数: $(find "$MARKDOWN_DIR" -name "*.md" | wc -l)"
if [ "$RUN_CLAUDE" = true ]; then
  echo "Claude解析結果数: $(find "$CLAUDE_DIR" -name "*.json" | wc -l)"
fi
echo "===================================================="

finish 
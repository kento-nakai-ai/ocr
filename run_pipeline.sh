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
#   ./run_pipeline.sh path/to/document.pdf --direct-katex --year 2024
#   ./run_pipeline.sh path/to/document.pdf --use-llm --gemini --multimodal-embedding
#
# 作者: OCRプロジェクトチーム
# バージョン: 1.1.0 (2024-04-08)
# ====================================================================================

# 終了時のクリーンアップ処理
function cleanup {
  echo "クリーンアップ処理を実行中..."
  # 一時ファイルの削除などがあれば実行
}

# エラー発生時の処理
function handle_error {
  echo "エラーが発生しました: $1"
  cleanup
  exit 1
}

# ロギング機能
function log {
  local level="$1"
  local message="$2"
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  
  case "$level" in
    "INFO")
      echo "[INFO] $timestamp - $message"
      ;;
    "ERROR")
      echo "[ERROR] $timestamp - $message" >&2
      ;;
    "WARNING")
      echo "[WARNING] $timestamp - $message"
      ;;
    *)
      echo "[$level] $timestamp - $message"
      ;;
  esac
}

# 必要なコマンドが存在するか確認
function check_required_commands {
  local commands=("python" "mkdir" "basename")
  
  for cmd in "${commands[@]}"; do
    if ! command -v "$cmd" &> /dev/null; then
      handle_error "$cmd コマンドが見つかりません。インストールしてください。"
    fi
  done
}

# スクリプトの初期チェック
check_required_commands

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
CLAUDE_DIR="$DATA_DIR/claude"
GEMINI_DIR="$DATA_DIR/gemini"
SIMILARITY_DIR="$DATA_DIR/similarity_reports"

# デフォルト設定
DEFAULT_DPI=300
DEFAULT_FORMAT="png"
DEFAULT_YEAR=2025
DEFAULT_QUESTION_PREFIX="Q"
DEFAULT_PARALLEL=4
DEFAULT_MODEL_VERSION="3.7" # Claude API用のモデルバージョン
DEFAULT_EMBEDDING_DIMENSION=1536 # エンベディングの次元数

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
SIMILARITY_COMPARE=false # エンベディング類似度比較を実行するかどうか
NO_FK_CHECK=false # 外部キー制約チェックを無効にするかどうか
TAG_EXTRACTION=false # 問題タグの自動抽出を実行するかどうか
MODEL_VERSION=$DEFAULT_MODEL_VERSION # APIモデルのバージョン
EMBEDDING_DIMENSION=$DEFAULT_EMBEDDING_DIMENSION # エンベディングの次元数
DEBUG_MODE=false # デバッグモード（詳細なログ出力）

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
  echo "  --similarity-compare エンベディング間の類似度比較を実行"
  echo "  --no-fk-check        エンベディングインポート時に外部キー制約チェックを無効化"
  echo "  --tag-extraction     問題のタグを自動抽出して保存"
  echo "  --model-version VER  APIモデルのバージョンを指定（デフォルト: $DEFAULT_MODEL_VERSION）"
  echo "  --embedding-dim DIM  エンベディングの次元数を指定（デフォルト: $DEFAULT_EMBEDDING_DIMENSION）"
  echo "  --year YEAR          対象年度を指定（デフォルト: $DEFAULT_YEAR）"
  echo "  --prefix PREFIX      問題IDのプレフィックスを指定（デフォルト: $DEFAULT_QUESTION_PREFIX）"
  echo "  --dpi DPI            画像変換時のDPI値を指定（デフォルト: $DEFAULT_DPI）"
  echo "  --format FORMAT      画像フォーマットを指定（png/jpeg、デフォルト: $DEFAULT_FORMAT）"
  echo "  --parallel N         並列処理数を指定（デフォルト: $DEFAULT_PARALLEL）"
  echo "  --debug              デバッグモードを有効化（詳細なログ出力）"
  echo "  -h, --help           このヘルプを表示"
  echo ""
  echo "例:"
  echo "  $0 data/pdf/sample.pdf --use-llm --year 2024 --gemini"
  echo "  $0 data/pdf/sample.pdf --direct-katex --year 2024"
  echo "  $0 data/pdf/sample.pdf --use-llm --gemini --multimodal-embedding"
  echo "  $0 data/pdf/sample.pdf --use-llm --similarity-compare --tag-extraction"
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
  handle_error "指定されたPDFファイル '$PDF_FILE' が見つかりません。"
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
      CLAUDE_DIR="$OUTPUT_DIR/claude"
      GEMINI_DIR="$OUTPUT_DIR/gemini"
      SIMILARITY_DIR="$OUTPUT_DIR/similarity_reports"
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
    --similarity-compare)
      SIMILARITY_COMPARE=true
      shift
      ;;
    --no-fk-check)
      NO_FK_CHECK=true
      shift
      ;;
    --tag-extraction)
      TAG_EXTRACTION=true
      shift
      ;;
    --model-version)
      MODEL_VERSION="$2"
      shift 2
      ;;
    --embedding-dim)
      EMBEDDING_DIMENSION="$2"
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
    --debug)
      DEBUG_MODE=true
      shift
      ;;
    *)
      handle_error "不明なオプション '$1'"
      ;;
  esac
done

# デバッグモードの設定
if [ "$DEBUG_MODE" = true ]; then
  set -x  # コマンドトレースを有効化
fi

# 必要なディレクトリの作成
log "INFO" "必要なディレクトリを作成中..."
mkdir -p "$PDF_DIR" "$IMAGES_DIR" "$OCR_DIR" "$MARKDOWN_DIR" "$EMBEDDING_DIR"
mkdir -p "$CLAUDE_DIR" "$GEMINI_DIR" "$SIMILARITY_DIR"

# PDFファイル名の取得（パスを除く）
PDF_FILENAME=$(basename "$PDF_FILE")
PDF_NAME="${PDF_FILENAME%.*}"

# ステップ1: PDFを画像に変換
log "INFO" "ステップ1: PDFをページごとに画像に変換中..."
python "$SCRIPTS_DIR/pdf_to_images.py" "$PDF_FILE" --output_dir "$IMAGES_DIR/$PDF_NAME" --dpi "$DPI" --format "$FORMAT" || handle_error "PDF→画像変換に失敗しました"
log "INFO" "  -> 変換完了: $IMAGES_DIR/$PDF_NAME"

# ステップ2: OCR処理または直接KaTeX変換
if [ "$SKIP_OCR" = false ]; then
  log "INFO" "ステップ2: OCR処理中..."
  OCR_CMD="python $SCRIPTS_DIR/ocr_engine.py $IMAGES_DIR/$PDF_NAME $OCR_DIR/$PDF_NAME"
  
  if [ "$USE_LLM" = true ]; then
    OCR_CMD="$OCR_CMD --use-llm"
    if [ "$USE_CLAUDE" = true ]; then
      OCR_CMD="$OCR_CMD --llm-provider claude --model-version $MODEL_VERSION"
    elif [ "$USE_GEMINI" = true ]; then
      OCR_CMD="$OCR_CMD --llm-provider gemini"
    fi
  fi
  
  eval "$OCR_CMD" || handle_error "OCR処理に失敗しました"
  log "INFO" "  -> OCR完了: $OCR_DIR/$PDF_NAME"
fi

# ステップ3: Markdown変換
if [ "$SKIP_MARKDOWN" = false ]; then
  log "INFO" "ステップ3: OCRテキストをMarkdownに変換中..."
  
  if [ "$DIRECT_KATEX" = true ]; then
    # 画像から直接KaTeX形式に変換する場合
    mkdir -p "$MARKDOWN_DIR/$PDF_NAME"
    for img_file in "$IMAGES_DIR/$PDF_NAME"/*.$FORMAT; do
      if [ -f "$img_file" ]; then
        base_name=$(basename "$img_file" .$FORMAT)
        log "INFO" "  -> 画像変換中: $base_name"
        python "$SCRIPTS_DIR/ocr_to_markdown.py" "$img_file" "$MARKDOWN_DIR/$PDF_NAME/${base_name}.md" --direct-image-to-katex || handle_error "画像→KaTeX変換に失敗しました: $img_file"
      fi
    done
  else
    # 通常のOCRテキストからMarkdownへの変換
    python "$SCRIPTS_DIR/ocr_to_markdown.py" "$OCR_DIR/$PDF_NAME" "$MARKDOWN_DIR/$PDF_NAME" --image-base-path "../images/$PDF_NAME" || handle_error "Markdown変換に失敗しました"
  fi
  
  log "INFO" "  -> Markdown変換完了: $MARKDOWN_DIR/$PDF_NAME"
fi

# ステップ4: MarkdownをDBにインポート
if [ "$SKIP_IMPORT" = false ]; then
  log "INFO" "ステップ4: MarkdownをDBにインポート中..."
  python "$SCRIPTS_DIR/markdown_importer.py" "$MARKDOWN_DIR/$PDF_NAME" --year "$YEAR" --prefix "$QUESTION_PREFIX" || handle_error "DBインポートに失敗しました"
  log "INFO" "  -> DBインポート完了"
fi

# ステップ5: 画像解析（マルチモーダルAPI）
if [ "$SKIP_ANALYSIS" = false ]; then
  log "INFO" "ステップ5: 画像解析（マルチモーダルAPI）中..."
  
  if [ "$USE_CLAUDE" = true ]; then
    ANALYSIS_CMD="python $SCRIPTS_DIR/claude_image_analyzer.py --input $IMAGES_DIR/$PDF_NAME --output $CLAUDE_DIR/$PDF_NAME --model-version $MODEL_VERSION"
    eval "$ANALYSIS_CMD" || handle_error "Claude APIによる画像解析に失敗しました"
    log "INFO" "  -> Claude APIによる画像解析完了: $CLAUDE_DIR/$PDF_NAME"
  elif [ "$USE_GEMINI" = true ]; then
    ANALYSIS_CMD="python $SCRIPTS_DIR/gemini_image_analyzer.py --input $IMAGES_DIR/$PDF_NAME --output $GEMINI_DIR/$PDF_NAME"
    
    if [ "$MULTIMODAL_EMBEDDING" = true ]; then
      ANALYSIS_CMD="$ANALYSIS_CMD --multimodal-embedding"
    fi
    
    if [ "$TAG_EXTRACTION" = true ]; then
      ANALYSIS_CMD="$ANALYSIS_CMD --extract-tags"
    fi
    
    eval "$ANALYSIS_CMD" || handle_error "Gemini APIによる画像解析に失敗しました"
    log "INFO" "  -> Gemini APIによる画像解析完了: $GEMINI_DIR/$PDF_NAME"
  fi
fi

# ステップ6: エンベディング生成
if [ "$SKIP_EMBEDDING" = false ] && [ "$MULTIMODAL_EMBEDDING" = false ]; then
  log "INFO" "ステップ6: エンベディング生成中..."
  
  if [ "$USE_CLAUDE" = true ]; then
    EMBEDDING_CMD="python $SCRIPTS_DIR/generate_embedding.py --input $CLAUDE_DIR/$PDF_NAME --dimension $EMBEDDING_DIMENSION --parallel $PARALLEL"
  else
    EMBEDDING_CMD="python $SCRIPTS_DIR/generate_embedding.py --input $GEMINI_DIR/$PDF_NAME --dimension $EMBEDDING_DIMENSION --parallel $PARALLEL"
  fi
  
  if [ "$NO_API" = true ]; then
    EMBEDDING_CMD="$EMBEDDING_CMD --no-api"
  fi
  
  eval "$EMBEDDING_CMD" || handle_error "エンベディング生成に失敗しました"
  log "INFO" "  -> エンベディング生成完了"
fi

# ステップ7: エンベディングをDBにインポート
if [ "$SKIP_EMBED_IMPORT" = false ]; then
  log "INFO" "ステップ7: エンベディングをDBにインポート中..."
  
  if [ "$USE_CLAUDE" = true ]; then
    EMBED_IMPORT_CMD="python $SCRIPTS_DIR/embed_importer.py --input $CLAUDE_DIR/$PDF_NAME --table embeddings"
  else
    EMBED_IMPORT_CMD="python $SCRIPTS_DIR/embed_importer.py --input $GEMINI_DIR/$PDF_NAME --table embeddings"
  fi
  
  if [ "$NO_FK_CHECK" = true ]; then
    EMBED_IMPORT_CMD="$EMBED_IMPORT_CMD --no-fk-check"
  fi
  
  eval "$EMBED_IMPORT_CMD" || handle_error "エンベディングのDBインポートに失敗しました"
  
  log "INFO" "  -> エンベディングのDBインポート完了"
fi

# ステップ8: 問題タグの自動抽出と登録
if [ "$TAG_EXTRACTION" = true ] && [ "$SKIP_ANALYSIS" = false ]; then
  log "INFO" "ステップ8: 問題タグの自動抽出と登録中..."
  
  if [ "$USE_GEMINI" = true ]; then
    # タグ登録コマンド
    python "$SCRIPTS_DIR/tag_manager.py" --input "$GEMINI_DIR/$PDF_NAME" --operation import-tags || handle_error "タグ登録に失敗しました"
    log "INFO" "  -> 問題タグの登録完了"
  else
    log "WARNING" "  -> タグ抽出はGemini APIでのみサポートされています"
  fi
fi

# ステップ9: エンベディング類似度比較（オプション）
if [ "$SIMILARITY_COMPARE" = true ]; then
  log "INFO" "ステップ9: エンベディング類似度比較中..."
  
  if [ "$USE_CLAUDE" = true ]; then
    python "$SCRIPTS_DIR/compare_similarity.py" --input "$CLAUDE_DIR/$PDF_NAME" --output "$SIMILARITY_DIR/$PDF_NAME" || handle_error "類似度比較に失敗しました"
  else
    python "$SCRIPTS_DIR/compare_similarity.py" --input "$GEMINI_DIR/$PDF_NAME" --output "$SIMILARITY_DIR/$PDF_NAME" || handle_error "類似度比較に失敗しました"
  fi
  
  log "INFO" "  -> 類似度比較レポート生成完了: $SIMILARITY_DIR/$PDF_NAME"
fi

# デバッグモードを無効化
if [ "$DEBUG_MODE" = true ]; then
  set +x  # コマンドトレースを無効化
fi

log "INFO" "パイプライン処理が完了しました！"
log "INFO" "出力ディレクトリ: $OUTPUT_DIR"
log "INFO" "処理結果:"
log "INFO" "  - PDF → 画像: $IMAGES_DIR/$PDF_NAME"
log "INFO" "  - OCRテキスト: $OCR_DIR/$PDF_NAME"
log "INFO" "  - Markdown: $MARKDOWN_DIR/$PDF_NAME"

if [ "$USE_CLAUDE" = true ]; then
  log "INFO" "  - 解析結果: $CLAUDE_DIR/$PDF_NAME"
else
  log "INFO" "  - 解析結果: $GEMINI_DIR/$PDF_NAME"
fi

log "INFO" "  - エンベディング: $EMBEDDING_DIR"

if [ "$SIMILARITY_COMPARE" = true ]; then
  log "INFO" "  - 類似度レポート: $SIMILARITY_DIR/$PDF_NAME"
fi

if [ "$TAG_EXTRACTION" = true ]; then
  log "INFO" "  - 問題タグ: question_tagsテーブル"
fi

log "INFO" "  - データベース: questionsテーブルおよびembeddingsテーブル"
echo ""
echo "以下のSQLでベクターサーチを実行できます:"
echo "SELECT q.question_id, q.year, q.content,"
echo "       1 - (e.embedding <=> :query_vector) AS similarity"
echo "  FROM questions q"
echo "  JOIN embeddings e ON q.question_id = e.question_id"
echo " ORDER BY similarity DESC"
echo " LIMIT 10;"
echo "========================================================"

# クリーンアップ処理を実行
cleanup

# 終了時のクリーンアップ処理を実行
cleanup 
# OCR + Markdown変換 + DBインポート + 画像解析パイプライン

このプロジェクトは、PDF形式の問題データからOCRによるテキスト抽出を行い、Markdown形式に整形し、PostgreSQLデータベースへインポートするワークフローを提供します。また、オプションでClaude APIを使用した画像解析機能も含まれています。

## 機能概要

1. PDFファイルのページごとの画像変換
2. Tesseract OCRによるテキスト抽出
3. OCRテキストのMarkdown形式への変換（数式KaTeX対応）
4. MarkdownデータのPostgreSQLへのインポート
5. （オプション）Claude APIを使用した画像解析

## 前提条件

以下のソフトウェア・ライブラリが必要です：

### システム要件
- Python 3.8以上
- Tesseract OCR（日本語モデル）
- Poppler
- PostgreSQL

### Pythonパッケージ
```
pip install pdf2image psycopg2-binary python-dotenv anthropic
```

### 環境変数
`.env`ファイルをプロジェクトルートに作成し、以下の内容を設定してください：

```
# データベース接続設定
DB_HOST=localhost
DB_PORT=5432
DB_NAME=questions_db
DB_USER=postgres
DB_PASSWORD=your_password

# Claude API（オプション）
CLAUDE_API_KEY=your_claude_api_key
```

## ディレクトリ構造

```
.
├── README.md            # このファイル
├── run_pipeline.sh      # ワークフロー実行スクリプト
├── .env                 # 環境変数設定ファイル（要作成）
├── scripts/             # 各種Pythonスクリプト
│   ├── pdf_to_images.py        # PDF→画像変換
│   ├── ocr_to_markdown.py      # OCRテキスト→Markdown変換
│   ├── markdown_importer.py    # Markdown→DBインポート
│   └── claude_image_analyzer.py # Claude画像解析
└── data/                # データファイル（自動生成）
    ├── pdf/             # 元のPDFファイル
    ├── images/          # 変換された画像
    ├── ocr/             # OCRテキスト
    ├── markdown/        # 変換されたMarkdown
    └── claude/          # Claude解析結果
```

## 使い方

### 1. 基本的な実行方法

```bash
./run_pipeline.sh path/to/your/document.pdf
```

これにより、PDFが画像に変換され、OCR処理、Markdown変換、DBインポートが順に実行されます。

### 2. オプションの指定

```bash
# DPIと出力ディレクトリを指定
./run_pipeline.sh path/to/your/document.pdf --dpi 600 --output custom_output

# OCR処理をスキップし、問題の年度を2024に設定
./run_pipeline.sh path/to/your/document.pdf --skip-ocr --year 2024

# Claude APIによる画像解析を有効化
./run_pipeline.sh path/to/your/document.pdf --claude
```

使用可能なオプションの一覧：

```
  -o, --output DIR      出力ディレクトリを指定します（デフォルト: data/）
  -d, --dpi NUM         画像変換時のDPI値を指定します（デフォルト: 300）
  -f, --format FORMAT   出力画像のフォーマットを指定します（png/jpeg、デフォルト: png）
  -y, --year YEAR       問題の年度を指定します（デフォルト: 2025）
  -q, --question ID     問題IDのプレフィックスを指定します（デフォルト: Q）
  -s, --skip-ocr        OCR処理をスキップします（既にOCRテキストがある場合）
  -c, --claude          Claude APIによる画像解析を有効にします
  -h, --help            このヘルプを表示します
```

### 3. 個別スクリプトの実行

各スクリプトは個別に実行することもできます：

#### PDF→画像変換
```bash
python scripts/pdf_to_images.py input.pdf --output_dir ./images --dpi 300 --format png
```

#### OCRテキスト→Markdown変換
```bash
python scripts/ocr_to_markdown.py input.txt output.md
```

#### Markdown→DBインポート
```bash
# 単一ファイル
python scripts/markdown_importer.py file.md 2025 "Q001"

# バッチモード
python scripts/markdown_importer.py --batch folder/ 2025
```

#### Claude画像解析
```bash
# 単一画像
python scripts/claude_image_analyzer.py image.png --output result.json

# バッチモード
python scripts/claude_image_analyzer.py --batch folder/ --output_dir results/
```

## カスタマイズ

### OCR→Markdown変換ルールの追加

`scripts/ocr_to_markdown.py`の`OCRToMarkdownConverter`クラスにて、数式変換パターンや画像タグ変換パターンを編集・追加できます。

```python
# 数式変換パターン例
self.math_patterns = [
    # [SQRT(3)] → $\sqrt{3}$
    (r'\[SQRT\((\d+)\)\]', r'$\\sqrt{\1}$'),
    # 新しいパターンを追加する場合はここに追記
    (r'\[NEW_PATTERN\]', r'$\\newcommand$')
]
```

### Claude APIプロンプトのカスタマイズ

`scripts/claude_image_analyzer.py`の`analyze_image`メソッドにて、画像解析用のプロンプトをカスタマイズできます。

## トラブルシューティング

- **OCR精度の問題**: 画像のDPIを上げる（300→600など）ことで改善されることがあります
- **DB接続エラー**: `.env`ファイルのDB設定を確認してください
- **Claude API接続エラー**: 環境変数`CLAUDE_API_KEY`を正しく設定してください

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。 
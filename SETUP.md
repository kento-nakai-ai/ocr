# 開発環境セットアップガイド

このドキュメントでは、OCR + Markdown変換 + DBインポート + 画像解析パイプラインの開発環境セットアップ手順を説明します。

## 1. 必要なシステムツールのインストール

### macOS (Homebrew使用)

```bash
# Poppler（PDF処理用）
brew install poppler

# Tesseract OCR（日本語モデル含む）
brew install tesseract
brew install tesseract-lang  # 日本語を含む追加言語

# PostgreSQL
brew install postgresql
```

### Ubuntu/Debian

```bash
# 必要なパッケージ
sudo apt update
sudo apt install -y poppler-utils tesseract-ocr tesseract-ocr-jpn postgresql postgresql-contrib

# PostgreSQLの起動
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Windows

1. **Poppler**: [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/)からダウンロードして解凍し、環境変数PATHに追加
2. **Tesseract OCR**: [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)からインストーラーをダウンロードし、日本語を含めてインストール
3. **PostgreSQL**: [PostgreSQL公式サイト](https://www.postgresql.org/download/windows/)からインストーラーをダウンロードしてインストール

## 2. Python環境のセットアップ

```bash
# プロジェクトディレクトリに移動
cd /path/to/ocr-project

# 仮想環境を作成（オプション、推奨）
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate

# 必要なパッケージをインストール
pip install -r requirements.txt
```

## 3. PostgreSQLのセットアップ

```bash
# PostgreSQLにログイン
psql -U postgres

# データベースを作成
CREATE DATABASE questions_db;

# ユーザー作成（オプション）
CREATE USER ocr_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE questions_db TO ocr_user;

# 終了
\q
```

## 4. 環境変数の設定

1. `.env.example`ファイルを`.env`としてコピー
   ```bash
   cp .env.example .env
   ```

2. `.env`ファイルを編集し、実際の値を設定
   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=questions_db
   DB_USER=postgres  # または先ほど作成したユーザー
   DB_PASSWORD=your_password
   
   # Claude API使用時のみ設定
   CLAUDE_API_KEY=your_claude_api_key
   ```

## 5. 動作確認

### 基本機能の確認

```bash
# スクリプトに実行権限を付与
chmod +x scripts/*.py run_pipeline.sh

# テスト用PDFで実行（Claude API除く）
./run_pipeline.sh path/to/sample.pdf
```

### Claude API連携の確認（オプション）

1. [Anthropic Developer Console](https://console.anthropic.com/)でAPIキーを取得
2. `.env`ファイルに`CLAUDE_API_KEY`を設定
3. Claude API連携を有効にしてパイプラインを実行
   ```bash
   ./run_pipeline.sh path/to/sample.pdf --claude
   ```

## トラブルシューティング

### Tesseract OCRが「tesseract: command not found」エラー

環境変数PATHにTesseractの実行ファイルが含まれているか確認し、必要に応じて追加してください。

### pdf2imageが「poppler not found」エラー

Popplerがインストールされているか確認し、環境変数PATHにPopplerの実行ファイルが含まれているか確認してください。

### データベース接続エラー

1. PostgreSQLが実行中かどうか確認
2. `.env`ファイルの接続情報が正しいか確認
3. PostgreSQLの認証設定（pg_hba.conf）を確認

### その他の問題

各スクリプトは個別に実行できるため、問題の箇所を特定するために個別にテストすることができます。例えば：

```bash
# PDF→画像変換のみ実行
python scripts/pdf_to_images.py sample.pdf --output_dir ./images

# OCR処理のみ実行（直接Tesseractを呼び出し）
tesseract images/sample_page01.png ocr/sample_page01 -l jpn
```

## 更新履歴

- 初版: 2024-04-05 
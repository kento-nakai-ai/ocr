# 開発環境セットアップガイド

このドキュメントでは、OCR + LLM(LLM-based OCR) + Markdown変換 + ベクターサーチ（Aurora） + マルチモーダル解析パイプラインの開発環境を詳細にセットアップする手順を説明します。

## 1. 前提条件と必要なシステムツールのインストール

### macOS (Homebrew使用)

```bash
# Homebrewがインストールされていない場合はインストール
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Poppler（PDF処理用）
brew install poppler

# Tesseract OCR（日本語モデル含む）
brew install tesseract
brew install tesseract-lang  # 日本語を含む追加言語

# PostgreSQL
brew install postgresql

# PostgreSQLの起動
brew services start postgresql
```

インストール後の確認:
```bash
# Popplerがインストールされているか確認
pdfinfo -v

# Tesseractがインストールされているか確認
tesseract --version

# PostgreSQLがインストールされているか確認
psql --version
```

### Ubuntu/Debian

```bash
# システムの更新
sudo apt update
sudo apt upgrade -y

# 必要なパッケージ
sudo apt install -y poppler-utils tesseract-ocr tesseract-ocr-jpn
sudo apt install -y postgresql postgresql-contrib

# pgvector拡張のインストール（オプション）
sudo apt install -y postgresql-server-dev-all build-essential git
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# PostgreSQLの起動と自動起動設定
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

インストール後の確認:
```bash
# Popplerがインストールされているか確認
pdfinfo -v

# Tesseractがインストールされているか確認
tesseract --version

# PostgreSQLがインストールされているか確認
psql --version
```

### Windows

#### Popplerのインストール
1. [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/)から最新リリースをダウンロード
2. ダウンロードしたzipファイルを任意の場所（例：`C:\Program Files\poppler`）に解凍
3. 環境変数の設定:
   - Windows検索で「環境変数」と入力→「システム環境変数の編集」を選択
   - 「環境変数」ボタン→ユーザー変数の「Path」を選択→「編集」
   - 「新規」をクリックし、Popplerの`bin`フォルダのパス（例：`C:\Program Files\poppler\bin`）を追加
   - 「OK」をクリックして適用

#### Tesseract OCRのインストール
1. [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)から最新の32ビットまたは64ビット版インストーラーをダウンロード
2. インストーラを実行し、インストール中に「Additional language data」から「Japanese」を選択
3. デフォルトのインストール先（例：`C:\Program Files\Tesseract-OCR`）を記録しておく
4. 環境変数の設定:
   - 上記と同様の手順で「Path」環境変数に Tesseract のインストールディレクトリ（例：`C:\Program Files\Tesseract-OCR`）を追加

#### PostgreSQLのインストール
1. [PostgreSQL公式サイト](https://www.postgresql.org/download/windows/)から最新版インストーラをダウンロード
2. インストーラを実行し、以下の設定でインストール:
   - インストールディレクトリ: デフォルト（`C:\Program Files\PostgreSQL\<version>`）
   - データディレクトリ: デフォルト
   - パスワード: 任意のパスワードを設定（忘れないように記録すること）
   - ポート: デフォルト（5432）
   - ロケール: デフォルト
3. インストール完了後、「Stack Builder」は不要なのでチェックを外してよい

インストール後の確認:
```bash
# コマンドプロンプトを開き、以下を実行

# Popplerがインストールされているか確認
pdfinfo -v

# Tesseractがインストールされているか確認
tesseract --version

# PostgreSQLがインストールされているか確認
psql --version
```

## 2. Python環境のセットアップ

### Python本体のインストール（まだの場合）

#### macOS
```bash
brew install python
```

#### Ubuntu/Debian
```bash
sudo apt install -y python3 python3-pip python3-venv
```

#### Windows
1. [Python公式サイト](https://www.python.org/downloads/)から最新版インストーラをダウンロード
2. インストーラを実行し、「Add Python to PATH」にチェックを入れる
3. 「Install Now」でインストール

### プロジェクトセットアップ

```bash
# プロジェクトディレクトリに移動
cd /path/to/ocr-project  # パスは適宜変更してください

# リポジトリのクローン（該当する場合）
# git clone https://github.com/your-username/ocr-project.git
# cd ocr-project

# 仮想環境を作成
python -m venv venv
```

#### 仮想環境のアクティブ化
##### macOS / Linux:
```bash
source venv/bin/activate
```

##### Windows:
```bash
venv\Scripts\activate
```

#### 必要なパッケージのインストール
```bash
# pipを最新バージョンにアップグレード
pip install --upgrade pip

# 必要なパッケージをインストール
pip install -r requirements.txt
```

## 3. PostgreSQLのセットアップ詳細

### データベースとユーザーの作成

#### macOS / Linux
```bash
# PostgreSQLにログイン（macOSの場合）
psql -U postgres
# または Ubuntu/Debian の場合
sudo -u postgres psql
```

#### Windows
```bash
# PostgreSQLにログイン
psql -U postgres
```

### 共通の PostgreSQL コマンド（全OS共通）
```sql
-- データベースを作成
CREATE DATABASE questions_db;

-- ユーザー作成（オプション）
CREATE USER ocr_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE questions_db TO ocr_user;

-- pgvector拡張のインストール（ベクターサーチ用）
\c questions_db
CREATE EXTENSION IF NOT EXISTS vector;

-- データベースに接続
\c questions_db

-- 必要なテーブルを作成

-- 問題テーブル
CREATE TABLE questions (
  id SERIAL PRIMARY KEY,
  year INT NOT NULL,
  page_number INT NOT NULL,
  problem_id VARCHAR(20),
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- エンベディングテーブル（ベクターサーチ用）
CREATE TABLE embeddings (
  id SERIAL PRIMARY KEY,
  question_id INT REFERENCES questions(id),
  embedding vector(1536),  -- OpenAI Embedding サイズ。使用するモデルに応じて変更可
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- メタデータテーブル
CREATE TABLE metadata (
  id SERIAL PRIMARY KEY,
  question_id INT REFERENCES questions(id),
  metadata JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス作成（検索高速化）
CREATE INDEX ON questions(year);
CREATE INDEX ON questions(problem_id);
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);

-- 終了
\q
```

### データベース接続テスト
```bash
# 作成したデータベースに接続
psql -U postgres -d questions_db

# または作成したユーザーで接続
psql -U ocr_user -d questions_db
```

## 4. 環境変数の設定

### .envファイルの設定

1. `.env.sample`ファイルを`.env`としてコピー
   ```bash
   cp .env.sample .env
   ```

2. `.env`ファイルを任意のエディタで開き、実際の値を設定
   ```
   # データベース接続設定
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=questions_db
   DB_USER=postgres  # または作成したユーザー
   DB_PASSWORD=your_secure_password
   
   # Claude API使用時設定
   CLAUDE_API_KEY=your_claude_api_key
   
   # Gemini API使用時設定
   GEMINI_API_KEY=your_gemini_api_key
   
   # OpenAI API使用時設定
   OPENAI_API_KEY=your_openai_api_key
   ```

### APIキーの取得方法

#### Claude APIキー取得
1. [Anthropic Console](https://console.anthropic.com/)にアクセスしてアカウント作成
2. 「API Keys」タブからAPIキーを作成
3. 作成したAPIキーを`.env`ファイルの`CLAUDE_API_KEY`にコピー

#### Gemini APIキー取得
1. [Google AI Studio](https://makersuite.google.com/app/apikey)にアクセスしてアカウント作成
2. 「API keys」セクションで「Create API key」をクリック
3. 作成したAPIキーを`.env`ファイルの`GEMINI_API_KEY`にコピー

#### OpenAI APIキー取得
1. [OpenAI API](https://platform.openai.com/)にアクセスしてアカウント作成
2. 「API keys」セクションで「Create new secret key」をクリック
3. 作成したAPIキーを`.env`ファイルの`OPENAI_API_KEY`にコピー

## 5. プロジェクトディレクトリの初期化

必要なディレクトリ構造を作成します。

```bash
# ルートディレクトリから実行

# dataディレクトリ内の必要なサブディレクトリを作成
mkdir -p data/pdf data/images data/ocr data/markdown data/embedding data/claude

# srcディレクトリ内の必要なサブディレクトリを作成
mkdir -p src/input src/output
```

## 6. スクリプトに実行権限を付与（macOS/Linux）

```bash
# スクリプトに実行権限を付与
chmod +x run_pipeline.sh extract_sample.sh
chmod +x src/*.py
```

## 7. 動作確認

### 基本機能の確認

```bash
# テスト用PDFをdata/pdfディレクトリに配置
# (例: 以下のコマンドで任意のPDFをコピー)
cp /path/to/sample.pdf data/pdf/

# パイプラインを実行
./run_pipeline.sh data/pdf/sample.pdf

# 結果の確認
ls -l data/images/  # 画像ファイルが生成されていることを確認
ls -l data/ocr/     # OCRテキストファイルが生成されていることを確認
ls -l data/markdown/ # Markdownファイルが生成されていることを確認
```

### LLMベースOCRの確認

```bash
# Claude APIを使用した場合
./run_pipeline.sh data/pdf/sample.pdf --use-llm --claude

# または Gemini APIを使用した場合
./run_pipeline.sh data/pdf/sample.pdf --use-llm --gemini
```

### サンプルページ抽出の確認

```bash
# サンプルページ抽出（Claudeを使用）
./extract_sample.sh data/pdf/sample.pdf --use-llm --claude --pages 5

# または Geminiを使用
./extract_sample.sh data/pdf/sample.pdf --use-llm --gemini --pages 5
```

## 8. データベース内容の確認

```bash
# PostgreSQLに接続
psql -U postgres -d questions_db

# または作成したユーザーで接続
psql -U ocr_user -d questions_db

# データベース内のテーブル一覧を表示
\dt

# questionsテーブルの内容を確認
SELECT id, year, problem_id, substring(content, 1, 50) FROM questions LIMIT 5;

# embeddings テーブルの内容を確認
SELECT id, question_id FROM embeddings LIMIT 5;

# ベクターサーチのテスト（pgvector使用時）
SELECT q.id, q.problem_id, q.year 
FROM questions q
JOIN embeddings e ON q.id = e.question_id
ORDER BY e.embedding <-> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

## 9. 詳細なトラブルシューティング

### 共通の問題

#### `ModuleNotFoundError`
原因: 必要なPythonパッケージがインストールされていない
解決策:
```bash
# 仮想環境がアクティブであることを確認
pip install -r requirements.txt
```

#### 環境変数読み込みエラー
原因: `.env`ファイルが正しく設定されていない
解決策:
```bash
# .envファイルが存在することを確認
ls -la .env

# .envファイルが正しく設定されているか確認
cat .env

# 必要に応じて.env.sampleから再作成
cp .env.sample .env
# そして必要な値を編集
```

### OS別の問題

#### macOS

##### Popplerが見つからない
```bash
# インストール状態確認
brew info poppler

# 再インストール
brew reinstall poppler

# パスが通っているか確認
which pdftoppm
```

##### テキスト出力が文字化けする
原因: 日本語フォントの問題
解決策:
```bash
# MacOSの場合、日本語フォントを確認
fc-list | grep -i japan
```

#### Linux

##### Tesseractが「jpn.traineddata」を見つけられない
原因: 日本語言語データがインストールされていない
解決策:
```bash
sudo apt install -y tesseract-ocr-jpn
```

##### PostgreSQLに接続できない
```bash
# サービスが実行中か確認
sudo systemctl status postgresql

# 実行されていない場合は起動
sudo systemctl start postgresql

# 設定ファイルを確認
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

#### Windows

##### 「XXXは内部コマンドまたは外部コマンド、操作可能なプログラムまたはバッチファイルとして認識されていません。」
原因: パスが正しく設定されていない
解決策:
1. システム環境変数のPathに各ツールのインストールパスが追加されているか確認
2. コマンドプロンプトを再起動して再度実行

##### PostgreSQLサービスが起動しない
解決策:
1. スタートメニュー→「サービス」を検索して開く
2. 「postgresql」サービスを探し、右クリック→「開始」
3. それでも起動しない場合は、ログを確認:
```bash
# データディレクトリのログを確認（典型的なパス）
type "C:\Program Files\PostgreSQL\<version>\data\pg_log\postgresql-<日付>.log"
```

### データベース関連の問題

#### テーブル作成エラー
```bash
# テーブルが存在するか確認
\dt

# 既存のテーブルを削除してやり直す場合
DROP TABLE IF EXISTS embeddings;
DROP TABLE IF EXISTS metadata;
DROP TABLE IF EXISTS questions;
```

#### pgvector拡張のエラー
```bash
# 拡張がインストールされているか確認
\dx

# 拡張をインストール
CREATE EXTENSION IF NOT EXISTS vector;

# バージョン確認
SELECT extversion FROM pg_extension WHERE extname = 'vector';
```

### API関連の問題

#### Claude/Gemini/OpenAI APIエラー
原因: APIキーが無効または制限に達している
解決策:
1. APIキーが正しいか確認
2. APIサービスのダッシュボードで使用量/制限を確認
3. APIサービスのステータスページで障害がないか確認

デバッグ:
```bash
# APIリクエストのデバッグログを有効にする（一部のスクリプト）
export DEBUG=true
python src/claude_image_analyzer.py ...
```

## 10. 参考情報

### ハードウェア要件の目安
- 最低: 4GB RAM、デュアルコアCPU
- 推奨: 8GB以上のRAM、クアッドコア以上のCPU
- GPU: オプション（エンベディング生成やAI処理を高速化）

### 対応PDFの制限事項
- サイズ制限: ファイルサイズ50MB以下推奨
- ページ数: 200ページ以下推奨（大きいPDFは分割処理推奨）
- スキャン品質: 最低300 DPI推奨
- テキスト抽出可能性: スキャンPDFの品質によっては精度が下がる可能性あり

### セキュリティ注意事項
- APIキーの管理: `.env`ファイルは`.gitignore`に含め、リポジトリにコミットしない
- データベースパスワード: 強力なパスワードを使用し、定期的に変更
- 接続セキュリティ: 本番環境ではSSL/TLS接続を有効化推奨

### パフォーマンス最適化
- 並列処理: `generate_embedding.py`などの処理では`--parallel`オプションで並列度を指定可能
- バッチサイズ: 大量のデータ処理時は適切なバッチサイズの指定が重要
- インデックス: データベースにはクエリパターンに合わせたインデックスを作成済み

## 更新履歴

- 2024-04-06: 詳細なトラブルシューティングセクションを追加
- 2024-04-05: 初版作成 
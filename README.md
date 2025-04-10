
# OCR + LLM + 資格試験対策統合システム

## 目次

1. [プロジェクト概要](#プロジェクト概要)
2. [システム構成](#システム構成)
3. [OCRパイプライン詳細](#ocrパイプライン詳細)
4. [資格試験対策API詳細](#資格試験対策api詳細)
5. [データベース構造](#データベース構造)
6. [タグシステム](#タグシステム)
7. [インストールと環境構築](#インストールと環境構築)
8. [使用例](#使用例)
9. [分析ツール](#分析ツール)
10. [ディレクトリ構造](#ディレクトリ構造)
11. [トラブルシューティング](#トラブルシューティング)
12. [参考リンク](#参考リンク)

## プロジェクト概要

このプロジェクトは、PDF形式の問題データを処理し、資格試験対策システムを構築するための統合ソリューションです。OCR処理から始まり、マルチモーダル解析、ベクターサーチ、そしてRESTful APIによるユーザーインターフェースまでを一貫して提供します。

主な特徴：
- 高精度OCR（ローカルTesseractまたはLLMベース）
- 数式・図表を含むMarkdown/KaTeX形式への変換
- マルチモーダルAI（Gemini/Claude）による画像解析
- ベクターサーチによる類似問題検索
- FastAPIベースのREST APIインターフェース
- 柔軟なタグシステムによる問題管理

## システム構成

```mermaid
flowchart TD
    subgraph "データ処理パイプライン"
        A[PDF入力] --> B[PDF→画像変換]
        B --> C[OCR処理]
        C --> D[Markdown変換]
        D --> E[データベース登録]
        B --> F[画像解析]
        F --> G[エンベディング生成]
        G --> E
    end
    
    subgraph "API層"
        E --> H[頻出問題API]
        E --> I[ユーザー回答API]
        E --> J[成績統計API]
        H --> K[クライアントアプリ]
        I --> K
        J --> K
    end
    
    subgraph "検索機能"
        E --> L[ベクターサーチ]
        L --> M[類似問題表示]
        M --> K
    end
```

## OCRパイプライン詳細

OCRパイプラインはPDF問題データを処理し、構造化された形式で保存します。

### 処理フロー

1. **PDF処理**: PDFページを高品質画像に変換
   ```bash
   python src/pdf_to_images.py --input input.pdf --output data/images/
   ```

2. **OCR処理**: 3つの方式から選択
   - Tesseract（ローカル）
   - LLMベース（Gemini/Claude）
   - 画像から直接KaTeX変換
   ```bash
   python src/ocr_engine.py --input data/images/page_001.png --output data/ocr/ --use-llm --gemini
   ```

3. **Markdown変換**: OCRテキストを数式付きMarkdownに変換
   ```bash
   python src/ocr_to_markdown.py --input data/ocr/page_001.txt --output data/markdown/page_001.md
   ```

4. **データベース登録**: MarkdownをPostgreSQLに格納
   ```bash
   python src/markdown_importer.py --input data/markdown/page_001.md --year 2024 --db-connection "postgresql://user:pass@localhost/db"
   ```

5. **画像解析**: マルチモーダルAIによる構造解析
   ```bash
   python src/gemini_image_analyzer.py --input data/images/page_001.png --output data/gemini/
   ```

6. **エンベディング生成**: テキストまたはマルチモーダルエンベディング
   ```bash
   python src/generate_embedding.py --input data/gemini/page_001_analysis.json --output data/embedding/
   ```

7. **エンベディングをDBに格納**: ベクターサーチ用
   ```bash
   python src/embed_importer.py --input data/embedding/page_001_embedding.npy --question-id R04001
   ```

### 主な機能

- **LLMベースOCR**: 高精度な日本語OCR
- **KaTeX数式変換**: 数式を美しく表示
- **構造化抽出**: 問題文、選択肢、解説など自動認識
- **回路図・表認識**: 図形的要素も検出・構造化
- **マルチモーダルエンベディング**: 画像とテキストの複合的な埋め込み

## 資格試験対策API詳細

FastAPIベースのREST APIでユーザーインターフェースを提供します。

### 主な機能

- **頻出問題API**: ユーザーの試験種別に合わせた頻出問題を取得
- **ユーザー回答API**: 回答記録と合格率スコア計算
- **成績統計API**: 学習進捗や成績履歴の取得
- **頻出問題登録API**: 一括登録機能（管理者向け）

### API仕様

サーバー起動後、以下のURLでAPIドキュメントにアクセスできます：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### アプリケーション構造

```
app/
├── main.py                   # アプリケーションエントリポイント
├── models/                   # データモデル
│   ├── database.py           # データベース接続設定
│   ├── question.py           # 問題モデル
│   ├── frequent_question.py  # 頻出問題モデル
│   ├── user_answer.py        # ユーザー回答モデル
│   └── user_stat.py          # ユーザー統計モデル
├── routes/                   # APIルート
│   ├── frequent_questions.py # 頻出問題API
│   └── user_answers.py       # ユーザー回答API
├── services/                 # ビジネスロジック
│   ├── frequent_question_service.py # 頻出問題サービス
│   └── user_answer_service.py       # ユーザー回答サービス
└── utils/                    # ユーティリティ
    └── auth.py               # 認証ユーティリティ
```

## データベース構造

PostgreSQL（またはAurora）を使用し、pgvector拡張でベクターサーチを実現します。

### 主要テーブル

**questionsテーブル**:
```sql
CREATE TABLE questions (
  id SERIAL PRIMARY KEY,
  question_id VARCHAR(50) UNIQUE NOT NULL,
  year INTEGER NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**embeddingsテーブル**:
```sql
CREATE TABLE embeddings (
  id SERIAL PRIMARY KEY,
  question_id VARCHAR(50) REFERENCES questions(question_id),
  embedding_type VARCHAR(50) NOT NULL,
  embedding VECTOR(768), -- 次元数は使用するモデルによる
  metadata JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**frequent_questionsテーブル**:
```sql
CREATE TABLE frequent_questions (
  id SERIAL PRIMARY KEY,
  question_id VARCHAR(50) REFERENCES questions(question_id),
  exam_type VARCHAR(50) NOT NULL,
  frequency_score FLOAT NOT NULL,
  last_appearance_year INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**user_answersテーブル**:
```sql
CREATE TABLE user_answers (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  question_id VARCHAR(50) REFERENCES questions(question_id),
  answer TEXT NOT NULL,
  is_correct BOOLEAN NOT NULL,
  answer_time INTEGER, -- 回答時間（秒）
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### ベクトル検索例

```sql
SELECT q2.question_id, q2.content, 
       1 - (e1.embedding <=> e2.embedding) AS similarity
FROM questions q1
JOIN embeddings e1 ON q1.question_id = e1.question_id
JOIN embeddings e2 ON e1.id != e2.id
JOIN questions q2 ON e2.question_id = q2.question_id
WHERE q1.question_id = 'R04001'
ORDER BY similarity DESC
LIMIT 5;
```

## タグシステム

問題に対して複数の属性（タグ）を柔軟に付与・管理するシステムです。

### タグ定義テーブル

```sql
CREATE TABLE tag_definitions (
  id SERIAL PRIMARY KEY,
  tag_key VARCHAR(50) UNIQUE NOT NULL,
  tag_type VARCHAR(20) NOT NULL, -- Flag, Categorical, Array, Enum, Text
  description TEXT,
  possible_values JSONB,
  remarks TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 問題タグテーブル

```sql
CREATE TABLE question_tags (
  id SERIAL PRIMARY KEY,
  question_id VARCHAR(50) REFERENCES questions(question_id),
  tag_key VARCHAR(50) REFERENCES tag_definitions(tag_key),
  tag_value TEXT NOT NULL,
  ai_inference VARCHAR(20), -- manual, by_AI, by_expert
  remarks TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 事前定義タグ例

- **is_mandatory**: 必須問題かどうか
- **difficulty**: 問題の難易度（LOW/MID/HIGH）
- **problem_type**: 問題タイプ（計算/暗記/など）
- **category**: 問題カテゴリ（法規/安全管理/設備/など）
- **year_list**: 出題された年度のリスト
- **exam_type**: 試験種別（1級電気/1級管/など）

## インストールと環境構築

### 前提条件

- Python 3.8以上
- Poppler（PDF→画像変換用）
- PostgreSQL または Amazon Aurora
- （必要に応じて）Tesseract OCR + 日本語モデル

### 仮想環境のセットアップ

```bash
# プロジェクトディレクトリに移動
cd /path/to/ocr-project

# 仮想環境を作成
python -m venv venv

# 仮想環境をアクティブ化（macOS/Linux）
source venv/bin/activate
# または Windows
# venv\Scripts\activate

# 必要なパッケージをインストール
pip install -r requirements.txt
```

### 環境変数の設定

`.env`ファイルをプロジェクトルートに作成：

```
# データベース接続設定
DB_HOST=localhost
DB_PORT=5432
DB_NAME=questions_db
DB_USER=postgres
DB_PASSWORD=your_password

# API設定（必要なものを設定）
CLAUDE_API_KEY=your_claude_api_key
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key

# AWS Cognito設定（API認証用）
AWS_REGION=ap-northeast-1
COGNITO_USER_POOL_ID=your-user-pool-id
COGNITO_APP_CLIENT_ID=your-app-client-id
```

### データベースセットアップ

```bash
# データベース作成
createdb questions_db

# pgvector拡張のインストール
psql -d questions_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# スキーマ作成
psql -d questions_db -f db/schema.sql
psql -d questions_db -f db/tags_schema.sql
```

### APIサーバーの起動

```bash
# 開発用サーバー
uvicorn app.main:app --reload

# 本番用サーバー
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 使用例

### 基本的なパイプライン実行

```bash
# 基本実行（Tesseract OCR使用）
./run_pipeline.sh data/pdf/document.pdf --year 2024

# LLMベースOCR使用（Gemini）
./run_pipeline.sh data/pdf/document.pdf --use-llm --gemini --year 2024

# 画像から直接KaTeX変換
./run_pipeline.sh data/pdf/document.pdf --direct-katex --year 2024

# マルチモーダルエンベディング使用
./run_pipeline.sh data/pdf/document.pdf --use-llm --gemini --multimodal-embedding
```

### サンプルページ抽出と分析

```bash
./extract_sample.sh data/pdf/large_document.pdf --use-llm --claude --pages 10
```

### タグマネージャーの使用例

```python
from tag_manager import TagManager

# TagManagerの初期化
with TagManager(db_config) as tag_manager:
    # 問題にタグを追加
    tag_manager.add_tag_to_question(
        question_id="R04001",
        tag_key="difficulty",
        tag_value="HIGH",
        ai_inference="by_expert"
    )
    
    # 難易度が「HIGH」の問題を検索
    high_difficulty_questions = tag_manager.get_questions_by_difficulty("HIGH")
    
    # 複数タグでの検索
    law_calc_questions = tag_manager.get_questions_by_multiple_tags({
        "category": "law", 
        "problem_type": "calc"
    })
```

## 分析ツール

### エンベディング距離分析

```bash
# エンベディングの分析
python src/embedding_analyzer.py --input data/embedding --output data/embedding/analysis --mode analyze

# 特定のエンベディングファイルに対して類似/非類似ファイルを探す
python src/embedding_analyzer.py --input data/embedding/令和5年度_page_046_embedding.npy --output data/embedding/samples --mode sample
```

### 類似/非類似問題の比較

```bash
# 比較レポートを作成
python src/compare_samples.py --input data/embedding/samples/sample_files.json --output data/embedding/comparison
```

### エンベディング類似度の比較

```bash
# 類似度比較を実行
python src/compare_similarity.py --input data/embedding --output data/similarity_report
```

## ディレクトリ構造

```
.
├── README.md                     # プロジェクト概要
├── SETUP.md                      # 詳細セットアップガイド
├── run_pipeline.sh               # パイプライン実行スクリプト
├── extract_sample.sh             # サンプルページ抽出スクリプト
├── requirements.txt              # Pythonパッケージ依存関係
├── .env                          # 環境変数（非公開）
├── .env.sample                   # 環境変数サンプル
├── ocr_pipeline_flow.md          # パイプラインフロー図解
├── ocr_future_plans.md           # 今後の開発計画
├── ocr_progress_report.md        # 進捗レポート
├── ocr_demo_results.md           # デモ結果報告
├── multimodal_embedding_issue.md # エンベディング問題報告
├── infra-todo.md                 # インフラ関連Todo
├── IMPROVEMENTS.md               # 改善提案書
├── src/                          # ソースコード
│   ├── pdf_to_images.py          # [1] PDF→画像変換
│   ├── ocr_engine.py             # [2] OCR処理
│   ├── ocr_to_markdown.py        # [3] Markdown変換
│   ├── markdown_importer.py      # [4] DB登録
│   ├── claude_image_analyzer.py  # [5a] Claude画像解析
│   ├── gemini_image_analyzer.py  # [5b] Gemini画像解析
│   ├── generate_embedding.py     # [6] エンベディング生成
│   ├── embed_importer.py         # [7] DB格納
│   ├── pdf2md_claude.py          # Claude PDF→MD変換
│   ├── pdf2md_gemini.py          # Gemini PDF→MD変換
│   ├── extract_sample_pages.py   # サンプルページ抽出
│   ├── embedding_analyzer.py     # エンベディング分析
│   ├── compare_samples.py        # 類似問題比較
│   ├── compare_similarity.py     # 類似度比較
│   ├── db_utils.py               # DB操作ユーティリティ
│   ├── tag_manager.py            # タグ管理
│   ├── json_to_db.py             # JSON→DB変換
│   ├── extract_frequently_asked.ts # 頻出問題抽出
│   ├── frequently_asked_service.ts # 頻出問題サービス
│   ├── utils/                    # ユーティリティ関数
│   ├── input/                    # 入力ファイル
│   └── output/                   # 出力ファイル
├── app/                          # FastAPIアプリケーション
│   ├── main.py                   # アプリエントリポイント
│   ├── models/                   # データモデル
│   ├── routes/                   # APIルート
│   ├── services/                 # サービスロジック
│   └── utils/                    # ユーティリティ
├── data/                         # データファイル
│   ├── pdf/                      # PDFファイル
│   ├── images/                   # 画像ファイル
│   ├── ocr/                      # OCRテキスト
│   ├── markdown/                 # Markdownファイル
│   ├── embedding/                # エンベディング
│   ├── claude/                   # Claude API結果
│   └── gemini/                   # Gemini API結果
├── db/                           # データベース関連
│   ├── README.md                 # データベース説明
│   ├── TAGS_README.md            # タグシステム説明
│   ├── tags_schema.sql           # タグシステムスキーマ
│   └── backups/                  # バックアップ
├── prisma/                       # Prisma ORM定義
├── client_samples/               # クライアントサンプル
└── samples/                      # サンプルデータ
```

## トラブルシューティング

詳細なトラブルシューティング情報は`SETUP.md`を参照してください。主な問題と解決策：

### 一般的な問題

- **ModuleNotFoundError**: 必要なパッケージのインストール確認
  ```bash
  pip install -r requirements.txt
  ```

- **環境変数エラー**: .envファイルの確認
  ```bash
  cp .env.sample .env  # コピーして編集
  ```

### OS別の問題

**macOS**:
- Popplerが見つからない場合: `brew reinstall poppler`
- 日本語フォント問題: `fc-list | grep -i japan`で確認

**Linux**:
- Tesseract日本語モデル: `sudo apt install -y tesseract-ocr-jpn`
- PostgreSQL接続問題: `sudo systemctl status postgresql`

**Windows**:
- パス設定問題: システム環境変数のPathを確認
- PostgreSQLサービス: サービスから手動起動

### API関連の問題

- APIキーエラー: キーの有効性と使用量制限を確認
- API応答遅延: タイムアウト設定の調整
- レート制限: APIサービスのダッシュボードで確認

## 参考リンク

- [try-vertex-ai-multimodal-search (zenn.dev)](https://zenn.dev/longrun_jp/articles/try-vertex-ai-multimodal-search)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [FastAPI 公式ドキュメント](https://fastapi.tiangolo.com/)
- [AWS Cognito 開発者ガイド](https://docs.aws.amazon.com/cognito/latest/developerguide/)
- [Gemini API ドキュメント](https://ai.google.dev/docs)
- [Claude API ドキュメント](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)

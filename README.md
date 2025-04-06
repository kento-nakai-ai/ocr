# OCR + LLM(LLM-based OCR) + Markdown変換 + ベクターサーチ（Aurora） + マルチモーダル解析パイプライン

このプロジェクトでは、PDF形式の問題データを中心に、以下のステップを経て学習データを構築・蓄積します。

1. **PDF取得 → PDFページを画像化**  
2. **OCR（ローカル or LLMベース）でテキスト抽出**  
3. **Markdown整形（KaTeX数式や画像タグ対応）**  
4. **PostgreSQL（またはAurora）へMarkdownデータをインポート**  
5. **画像をGemini/ClaudeなどのマルチモーダルAPIへ渡し、埋め込み（Embedding）を取得**  
6. **Embedding結果をDBに格納（ベクターサーチに対応）**  
7. **得られたメタ情報を追加でDBに格納またはJSON化**  

この一連のパイプラインにより、類似問題検索などの機能（マルチモーダルベースのベクターサーチ）を実現します。

## 機能概要

1. **PDFファイルのページごとの画像変換**  
   - `pdf_to_images.py`などでPopplerを用いてPDFから画像（PNG/JPEG）を生成
2. **OCR処理**  
   - **ローカルOCR（Tesseract）**  
   - **LLMベースOCR（Gemini, Claude, GPT-4など）**  
3. **Markdown変換（ocr_to_markdown.py）**  
   - テキストをKaTeX数式や適切な画像タグに整形
4. **PostgreSQL/Auroraにインポート（markdown_importer.py）**  
   - `questions`テーブルなどにMarkdown形式の本文や年度、問題IDなどを格納
5. **マルチモーダルAPI（Gemini等）で画像解析 & Embedding取得**  
   - 画像をAPIに送信→テキスト/特徴量（ベクトル）を取得  
   - もしくはテキスト＋画像の両方を入力し、マルチモーダル埋め込みを生成
6. **Embedding結果をDBに格納**  
   - Aurora PostgreSQLの場合、[pgvector拡張](https://github.com/pgvector/pgvector)などを利用可能  
   - 類似度ベースの検索（ベクターサーチ）に活用
7. **追加メタ情報の管理**  
   - Gemini/Claude等から返却されるJSON形式の解析結果をDBに格納するか、別途JSONで保持するかを選択  
   - 必要に応じて`metadata`テーブルを追加し、類似問題のIDやスコアなどを管理

## 前提条件

### システム要件
- Python 3.8以上
- Poppler（PDF→画像変換用）
- PostgreSQL または Amazon Aurora (PostgreSQL互換)
- （必要に応じて）Tesseract OCR
  - 日本語モデル（`jpn.traineddata`）

### LLMベースOCR・画像解析（選択的に使用）
- Gemini API（Googleの次世代マルチモーダルモデルを想定）
- Claude API（Anthropic）
- OpenAI API（GPT-4等）

### Pythonパッケージ例

```bash
pip install pdf2image psycopg2-binary python-dotenv anthropic
# LLM使用例:
# pip install openai  # GPT-4等
# pip install google-cloud-aiplatform  # 例: Vertex AI使用時など
```

## 仮想環境のセットアップ

プロジェクトの依存関係をクリーンに管理するため、仮想環境の使用を強く推奨します。以下の手順でセットアップしてください。

### 仮想環境の作成

#### macOS / Linux:

```bash
# プロジェクトディレクトリに移動
cd /path/to/ocr-project

# 仮想環境を作成
python -m venv venv

# 仮想環境をアクティブ化
source venv/bin/activate
```

#### Windows:

```bash
# プロジェクトディレクトリに移動
cd C:\path\to\ocr-project

# 仮想環境を作成
python -m venv venv

# 仮想環境をアクティブ化
venv\Scripts\activate
```

### パッケージのインストール

仮想環境をアクティブ化した状態で以下のコマンドを実行します：

```bash
# pipを最新バージョンにアップグレード（推奨）
pip install --upgrade pip

# 必要なパッケージをインストール
pip install -r requirements.txt
```

### 仮想環境の終了

作業が終了したら、以下のコマンドで仮想環境を終了できます：

```bash
deactivate
```

### 仮想環境の再アクティブ化

次回作業を行う際は、仮想環境を再度アクティブ化します：

#### macOS / Linux:
```bash
source venv/bin/activate
```

#### Windows:
```bash
venv\Scripts\activate
```

### 注意点

- ターミナル/コマンドプロンプトのプロンプトが `(venv)` で始まっていれば、仮想環境がアクティブな状態です
- プロジェクト関連のコマンドはすべて仮想環境がアクティブな状態で実行してください
- `requirements.txt` に変更があった場合は、再度 `pip install -r requirements.txt` を実行して依存関係を更新してください

### 環境変数

`.env`ファイルをプロジェクトルートに作成し、以下の内容を設定してください（例）:

```
# データベース接続設定
DB_HOST=localhost
DB_PORT=5432
DB_NAME=questions_db
DB_USER=postgres
DB_PASSWORD=your_password

# Claude API（オプション）
CLAUDE_API_KEY=your_claude_api_key

# Gemini API（オプション）
GEMINI_API_KEY=your_gemini_api_key

# OpenAI API
OPENAI_API_KEY=your_openai_api_key
```

## ディレクトリ構造

```
.
├── README.md                     # このファイル
├── run_pipeline.sh               # ワークフロー実行スクリプト
├── .env                          # 環境変数設定ファイル（要作成）
├── scripts/                      # 各種Pythonスクリプト
│   ├── pdf_to_images.py               # [1] PDF→画像変換
│   ├── ocr_engine.py                  # [2] OCR処理 (Tesseract/LLM)
│   ├── ocr_to_markdown.py             # [3] テキスト→Markdown変換
│   ├── markdown_importer.py           # [4] Markdown→DBインポート
│   ├── gemini_image_analyzer.py       # [5] Geminiなどでマルチモーダル解析
│   ├── embed_importer.py              # [6] Embedding情報をDB格納
│   └── ...
└── data/                         # データファイル（自動生成）
    ├── pdf/                      # 元のPDFファイル
    ├── images/                   # 画像化したファイル
    ├── ocr/                      # OCRテキスト
    ├── markdown/                 # 変換されたMarkdown
    ├── embedding/                # 画像・テキスト埋め込み（ベクトル）
    └── ...
```

## パイプラインの流れ

1. **[1] PDFを取得 → PDFページを画像化**  
   - `pdf_to_images.py`でPopplerを呼び出し、ページ単位に画像を生成
2. **[2] OCR処理**  
   - `ocr_engine.py`を介してTesseractかLLMを選択  
   - `--use-llm` オプションなどを指定してGemini/ClaudeのAPIを叩く
3. **[3] OCRテキストをMarkdownへ変換**  
   - `ocr_to_markdown.py` でKaTeX数式や画像タグを整形
4. **[4] MarkdownをPostgreSQL/Auroraへインポート**  
   - `markdown_importer.py` で `questions` テーブルにINSERT  
   - 質問文、年度、問題IDなどを登録
5. **[5] 画像解析 & 埋め込み取得（マルチモーダルAPI）**  
   - `gemini_image_analyzer.py` (名前は例)で画像＋テキストをAPIへ送信  
   - 埋め込み（ベクトル）を取得し、ローカルに`.npy`やJSON形式で保存
6. **[6] ベクトル情報をDBへ格納**  
   - `embed_importer.py`でPostgreSQL/Aurora(ポスグレ互換)のベクトル型カラムにINSERT  
   - pgvector拡張などを用いてベクターサーチを可能にする
7. **[7] メタ情報を追加でDB保存 or JSON管理**  
   - 類似問題のスコアや補足データを`metadata`テーブルに入れる  
   - またはJSONファイルで管理し、必要に応じてフロントエンドから読み込む

## 使い方

### 1. 基本的な実行

```bash
./run_pipeline.sh path/to/your/document.pdf
```

- 上記でステップ[1]～[4]が一括実行されます（OCRはデフォルトでTesseract）

### 2. マルチモーダル解析・Embeddingインポート

```bash
# Gemini/ClaudeなどのAPIを使って画像解析＆ベクトル取得
python scripts/gemini_image_analyzer.py --input images/ --output embedding/
# 得られたembeddingをDBに登録
python scripts/embed_importer.py --input embedding/ --table embeddings
```

### 3. オプションの指定

```bash
./run_pipeline.sh path/to/your/document.pdf \
  --use-llm \
  --dpi 600 \
  --year 2024 \
  --claude
```

- `--use-llm`: OCRにLLM APIを使用
- `--claude`: Claudeを画像解析にも使う  
  （`gemini_image_analyzer.py`を呼び出すスクリプトに改変するなど）

### 4. ベクターサーチ（Aurora/pgvector）

Aurora（PostgreSQL互換）でpgvectorを有効化している場合は、以下のようなクエリで**類似検索**が可能です：

```sql
SELECT id, 
       embedding <-> to_query_vector(:input_vector) AS distance
  FROM embeddings
 ORDER BY distance ASC
 LIMIT 10;
```

(`to_query_vector(:input_vector)` はpgvectorの検索用関数の例)

## カスタマイズ

- **OCRエンジン切り替え**  
  `ocr_engine.py` 内で `--use-llm` フラグに応じてTesseract / Gemini / Claude / GPT-4等を切り替え。  
- **埋め込み格納**  
  `embed_importer.py` 内で、ベクトル型カラム（pgvector拡張）へINSERTするSQLを定義。  
- **メタ情報管理**  
  複数のテーブルを使う・JSON型で管理するなど、要件に応じて変更

## トラブルシューティング

- **OCR精度が低い**  
  - DPIを高めに設定（300→600）  
  - LLMベースOCRに切り替え  
  - PDFがスキャン品質低下の場合、事前に画像補正を行う
- **API接続エラー**  
  - `.env`のAPIキー設定を再確認  
  - レートリミットを超過している可能性  
- **ベクター型が見つからない**  
  - PostgreSQLの拡張（pgvectorなど）を有効化しているかチェック  
  - Auroraのバージョン・設定確認

## 参考リンク

- [try-vertex-ai-multimodal-search (zenn.dev)](https://zenn.dev/longrun_jp/articles/try-vertex-ai-multimodal-search)  
- [pgvector GitHub](https://github.com/pgvector/pgvector)

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

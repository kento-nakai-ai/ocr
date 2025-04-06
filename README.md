# OCR + LLM(LLM-based OCR) + Markdown変換 + ベクターサーチ（Aurora） + マルチモーダル解析パイプライン

このプロジェクトでは、PDF形式の問題データを中心に、以下のステップを経て学習データを構築・蓄積します。

1. **PDF取得 → PDFページを画像化**  
2. **OCR（ローカル or LLMベース）でテキスト抽出**  
3. **Markdown整形（KaTeX数式や画像タグ対応）**  
4. **PostgreSQL（またはAurora）へMarkdownデータをインポート**  
5. **画像をGemini/ClaudeなどのマルチモーダルAPIへ渡し、解析結果を取得**  
   - **日本語試験問題を抽出し、JSON形式で構造化**
6. **解析結果から埋め込み（Embedding）ベクトルを生成**  
7. **Embedding結果をDBに格納（ベクターサーチに対応）**  
8. **得られたメタ情報を追加でDBに格納またはJSON化**  

この一連のパイプラインにより、類似問題検索などの機能（マルチモーダルベースのベクターサーチ）を実現します。

## 機能概要

1. **PDFファイルのページごとの画像変換**  
   - `pdf_to_images.py`などでPopplerを用いてPDFから画像（PNG/JPEG）を生成
2. **OCR処理**  
   - **ローカルOCR（Tesseract）**  
   - **LLMベースOCR（Gemini 2.5 Pro, Claude 3.7 Sonnet, GPT-4など）**  
3. **Markdown変換（ocr_to_markdown.py）**  
   - テキストをKaTeX数式や適切な画像タグに整形
4. **PostgreSQL/Auroraにインポート（markdown_importer.py）**  
   - `questions`テーブルなどにMarkdown形式の本文や年度、問題IDなどを格納
5. **マルチモーダルAPI（Claude/Gemini等）で画像解析**  
   - 画像をAPIに送信→テキスト/解析結果（JSON）を取得
   - `claude_image_analyzer.py`/`gemini_image_analyzer.py`で処理
   - **日本語試験問題の構造化抽出**：
     - 問題番号、問題文、選択肢、解説、正解などを自動認識
     - 以下のようなJSON形式で出力：
     ```json
     {
       "problems": [
         {
           "id": 1,
           "question": "問題文...$Q = R I^2 t$...続く問題文",
           "choices": [
             {
               "number": 1,
               "text": "選択肢1..."
             },
             {
               "number": 2,
               "text": "選択肢2..."
             },
             {
               "number": 3,
               "text": "選択肢3..."
             },
             {
               "number": 4,
               "text": "選択肢4..."
             }
           ],
           "explanation": "解説文...$M = -e_2 \\frac{\\Delta t}{\\Delta i_1}$...続く解説文",
           "correct_answer": 3
         }
       ]
     }
     ```
6. **埋め込みベクトル生成（generate_embedding.py）**  
   - 解析結果JSONから埋め込みベクトルを生成
   - ベクトルをnumpy形式で保存
7. **Embedding結果をDBに格納（embed_importer.py）**  
   - Aurora PostgreSQLの場合、[pgvector拡張](https://github.com/pgvector/pgvector)などを利用可能  
   - 類似度ベースの検索（ベクターサーチ）に活用
8. **追加メタ情報の管理**  
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
- Gemini 2.5 Pro API（Googleの最新マルチモーダルモデル）
- Claude 3.7 Sonnet API（Anthropic）
- OpenAI API（GPT-4等）

### Pythonパッケージ例

```bash
pip install pdf2image psycopg2-binary python-dotenv anthropic PyPDF2 google-generativeai numpy
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
├── extract_sample.sh             # サンプルページ抽出スクリプト
├── .env                          # 環境変数設定ファイル（要作成）
├── src/                          # 各種Pythonスクリプト
│   ├── pdf_to_images.py               # [1] PDF→画像変換
│   ├── ocr_engine.py                  # [2] OCR処理 (Tesseract/LLM)
│   ├── ocr_to_markdown.py             # [3] テキスト→Markdown変換
│   ├── markdown_importer.py           # [4] Markdown→DBインポート
│   ├── claude_image_analyzer.py       # [5a] Claudeを使った画像解析
│   ├── gemini_image_analyzer.py       # [5b] Geminiを使った画像解析
│   ├── generate_embedding.py          # [6] 解析結果からエンベディング生成
│   ├── embed_importer.py              # [7] Embedding情報をDB格納
│   ├── pdf2md_claude.py               # Claude 3.7 Sonnetを使ったPDF→Markdown変換
│   ├── pdf2md_gemini.py               # Gemini 2.5 Proを使ったPDF→Markdown変換
│   ├── extract_sample_pages.py        # PDFからサンプルページを抽出するスクリプト
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
5. **[5] 画像解析（マルチモーダルAPI）**  
   - `claude_image_analyzer.py`または`gemini_image_analyzer.py`で画像をAPIへ送信  
   - 解析結果をJSON形式で保存
   - **日本語試験問題の構造化抽出**：
     - 問題番号、問題文、選択肢、解説、正解などを自動認識
     - 以下のようなJSON形式で出力：
     ```json
     {
       "problems": [
         {
           "id": 1,
           "question": "問題文...$Q = R I^2 t$...続く問題文",
           "choices": [
             {
               "number": 1,
               "text": "選択肢1..."
             },
             {
               "number": 2,
               "text": "選択肢2..."
             },
             {
               "number": 3,
               "text": "選択肢3..."
             },
             {
               "number": 4,
               "text": "選択肢4..."
             }
           ],
           "explanation": "解説文...$M = -e_2 \\frac{\\Delta t}{\\Delta i_1}$...続く解説文",
           "correct_answer": 3
         }
       ]
     }
     ```
6. **[6] 埋め込みベクトル（Embedding）生成**  
   - `generate_embedding.py`でJSON解析結果から埋め込みベクトルを生成
   - ベクトルをnumpy形式（.npy）で保存
7. **[7] ベクトル情報をDBへ格納**  
   - `embed_importer.py`でPostgreSQL/Aurora(ポスグレ互換)のベクトル型カラムにINSERT  
   - pgvector拡張などを用いてベクターサーチを可能にする
8. **[8] メタ情報を追加でDB保存 or JSON管理**  
   - 類似問題のスコアや補足データを`metadata`テーブルに入れる  
   - またはJSONファイルで管理し、必要に応じてフロントエンドから読み込む

## 使い方

### 1. 基本的な実行

```bash
./run_pipeline.sh path/to/your/document.pdf
```

- 上記でステップ[1]～[8]が一括実行されます（OCRはデフォルトでTesseract）

### 2. サンプルページの抽出と処理

```bash
./extract_sample.sh path/to/your/document.pdf --use-llm [--claude|--gemini]
```

- PDFファイルからサンプルとして10ページを抽出してOCR処理を行います
- 主なオプション:
  - `--pages NUM`: 抽出するページ数（デフォルト：10）
  - `--use-llm`: OCRにLLMベースの処理を使用する（必須）
  - `--claude`: 画像解析にClaude 3.7 Sonnet APIを使用する
  - `--gemini`: 画像解析にGemini 2.5 Pro APIを使用する（デフォルト）
  - `--dpi NUM`: 画像変換時のDPI値（デフォルト：300）
  - `--format FORMAT`: 画像フォーマット（png/jpeg、デフォルト：png）

### 3. 個別モジュールの実行

各ステップを個別に実行することもできます：

```bash
# [1] PDFから画像への変換
python src/pdf_to_images.py data/pdf/example.pdf --output_dir data/images --dpi 300 --format png

# [2] OCR処理（TesseractまたはLLM）
python src/ocr_engine.py data/images data/ocr [--use-llm] [--llm-provider claude|gemini]

# [3] OCRテキストをMarkdownへ変換
python src/ocr_to_markdown.py data/ocr data/markdown --image-base-path "../images"

# [4] MarkdownをDBへインポート
python src/markdown_importer.py --input data/markdown --year 2024 --prefix "Q"

# [5] 画像解析（Claude/Gemini）と日本語試験問題抽出
python src/claude_image_analyzer.py --input data/images --output data/embedding
# または
python src/gemini_image_analyzer.py --input data/images --output data/embedding

# [6] 埋め込みベクトル生成
python src/generate_embedding.py --input data/embedding --dimension 1536 --parallel 4

# [7] エンベディングをDBにインポート
python src/embed_importer.py --input data/embedding --table embeddings
```

### 4. オプションの指定

```bash
./run_pipeline.sh path/to/your/document.pdf \
  --use-llm \
  --dpi 600 \
  --year 2024 \
  --claude
```

- `--use-llm`: OCRにLLM APIを使用
- `--claude`: Claude APIを画像解析に使用
- `--dpi 600`: 高解像度でPDFを画像に変換

### 5. 日本語試験問題抽出機能

日本語の試験問題を画像から抽出し、構造化された形式に変換します：

```bash
# Claudeを使った画像からの問題抽出
python src/claude_image_analyzer.py 問題画像.png --output output.json

# または、Geminiを使った画像からの問題抽出
python src/gemini_image_analyzer.py --input 問題画像.png --output ./出力ディレクトリ
```

出力されるJSONは以下の形式になります：

```json
{
  "problems": [
    {
      "id": 1,
      "question": "問題文...$Q = R I^2 t$...続く問題文",
      "choices": [
        {
          "number": 1,
          "text": "選択肢1..."
        },
        {
          "number": 2,
          "text": "選択肢2..."
        },
        {
          "number": 3,
          "text": "選択肢3..."
        },
        {
          "number": 4,
          "text": "選択肢4..."
        }
      ],
      "explanation": "解説文...$M = -e_2 \\frac{\\Delta t}{\\Delta i_1}$...続く解説文",
      "correct_answer": 3
    }
  ]
}
```

この構造化データは以下の特徴を持っています：
- 問題番号、問題文、選択肢、解説、正解を体系的に整理
- 数式はKaTeX構文で表現（インライン数式は $...$ で囲む）
- 図表は `[figure_N]` 形式で表現
- 不完全な問題は出力から除外

### 6. ベクターサーチ（Aurora/pgvector）

Aurora（PostgreSQL互換）でpgvectorを有効化している場合は、以下のようなクエリで**類似検索**が可能です：

```sql
SELECT id, 
       embedding <-> to_query_vector(:input_vector) AS distance
  FROM embeddings
 ORDER BY distance ASC
 LIMIT 10;
```

(`to_query_vector(:input_vector)` はpgvectorの検索用関数の例)

## LLMモデル情報

### Claude 3.7 Sonnet
- 最新のAnthropicのモデル
- モデルID: `claude-3-7-sonnet-20240307`
- PDFネイティブ対応（最新のAPIベータ機能）
- 最大入力トークン: 200K

### Gemini 2.5 Pro
- 最新のGoogleのマルチモーダルモデル
- モデルID: `gemini-2.5-pro`
- 画像、PDFの高精度な認識が可能
- 最大入力トークン: 1M (百万トークン)

## カスタマイズ

- **OCRエンジン切り替え**  
  `ocr_engine.py` 内で `--use-llm` フラグに応じてTesseract / Gemini / Claude / GPT-4等を切り替え。  
- **画像解析プロンプト変更**  
  `claude_image_analyzer.py`や`gemini_image_analyzer.py`内のプロンプト部分を編集して、異なる形式や目的に応じた抽出が可能。
- **埋め込み生成**  
  `generate_embedding.py` 内で、実際のAPIから取得した埋め込みベクトルに置き換えることが可能。  
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
- **エンベディング生成エラー**  
  - JSONファイルのフォーマットを確認
  - 必要なフィールド（text_contentなど）が存在するか確認
- **JSON構造化エラー**
  - 画像の解像度を上げてみる
  - 複雑すぎる問題や図表が多い場合は、より高性能なモデル（Claude-3-Opus等）を使用する

## 参考リンク

- [try-vertex-ai-multimodal-search (zenn.dev)](https://zenn.dev/longrun_jp/articles/try-vertex-ai-multimodal-search)  
- [pgvector GitHub](https://github.com/pgvector/pgvector)

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

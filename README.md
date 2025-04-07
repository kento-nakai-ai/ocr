# OCR + LLM(LLM-based OCR) + Markdown変換 + ベクターサーチ（Aurora） + マルチモーダル解析パイプライン

このプロジェクトでは、PDF形式の問題データを中心に、以下のステップを経て学習データを構築・蓄積します。

1. **PDF取得 → PDFページを画像化**  
2. **OCR（ローカル or LLMベース）でテキスト抽出** または **画像から直接KaTeX形式に変換**  
3. **Markdown整形（KaTeX数式や画像タグ対応）**  
4. **PostgreSQL（またはAurora）へMarkdownデータをインポート**  
5. **画像をGemini/ClaudeなどのマルチモーダルAPIへ渡し、解析結果を取得**  
   - **日本語試験問題を抽出し、JSON形式で構造化**
   - **回路図や表などの図形的要素も認識・構造化**
6. **解析結果から埋め込み（Embedding）ベクトルを生成**
   - **テキストのみのエンベディング**
   - **マルチモーダルエンベディング（画像とテキストの組み合わせ）**
7. **Embedding結果をDBに格納（ベクターサーチに対応）**  
8. **得られたメタ情報を追加でDBに格納またはJSON化**  

この一連のパイプラインにより、類似問題検索などの機能（マルチモーダルベースのベクターサーチ）を実現します。

## 機能概要

1. **PDFファイルのページごとの画像変換**  
   - `pdf_to_images.py`などでPopplerを用いてPDFから画像（PNG/JPEG）を生成
2. **OCR処理または直接KaTeX変換**  
   - **ローカルOCR（Tesseract）**  
   - **LLMベースOCR（Gemini 2.5 Pro, Claude 3.7 Sonnet, GPT-4など）**
   - **画像から直接KaTeX形式への変換**（`ocr_to_markdown.py`の`--direct-image-to-katex`オプション）
3. **Markdown変換（ocr_to_markdown.py）**  
   - テキストをKaTeX数式や適切な画像タグに整形
4. **PostgreSQL/Auroraにインポート（markdown_importer.py）**  
   - `questions`テーブルなどにMarkdown形式の本文や年度、問題IDなどを格納
5. **マルチモーダルAPI（Claude/Gemini等）で画像解析**  
   - 画像をAPIに送信→テキスト/解析結果（JSON）を取得
   - `claude_image_analyzer.py`/`gemini_image_analyzer.py`で処理
   - **日本語試験問題の構造化抽出**：
     - 問題番号、問題文、選択肢、解説、正解などを自動認識
     - 回路図や表などの図形的要素も検出・構造化
     - 以下のようなJSON形式で出力：
     ```json
     {
       "problems": [
         {
           "id": 1,
           "question": "問題文...$Q = R I^2 t$...続く問題文",
           "has_circuit_diagram": true, 
           "circuit_description": "コンデンサとトランジスタを含む回路",
           "has_table": false,
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
   - 解析結果JSONからテキストのエンベディングを生成
   - **マルチモーダルエンベディング生成**（画像とテキストを組み合わせた高度なエンベディング）
   - ベクトルをnumpy形式で保存
   - 実際のGemini APIを使用した正確なエンベディング生成（`--no-api`オプションでダミーエンベディングにフォールバック可能）
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
├── SETUP.md                      # セットアップガイド
├── run_pipeline.sh               # ワークフロー実行スクリプト
├── extract_sample.sh             # サンプルページ抽出スクリプト
├── requirements.txt              # 必要なPythonパッケージ一覧
├── .env                          # 環境変数設定ファイル
├── .env.sample                   # 環境変数設定サンプル
├── src/                          # 各種Pythonスクリプト
│   ├── pdf_to_images.py               # [1] PDF→画像変換
│   ├── ocr_engine.py                  # [2] OCR処理 (Tesseract/LLM)
│   ├── ocr_to_markdown.py             # [3] テキスト→Markdown変換／画像→KaTeX変換
│   ├── markdown_importer.py           # [4] Markdown→DBインポート
│   ├── claude_image_analyzer.py       # [5a] Claudeを使った画像解析
│   ├── gemini_image_analyzer.py       # [5b] Geminiを使った画像解析（マルチモーダルエンベディング対応）
│   ├── generate_embedding.py          # [6] 解析結果からエンベディング生成
│   ├── embed_importer.py              # [7] Embedding情報をDB格納
│   ├── pdf2md_claude.py               # Claude 3.7 Sonnetを使ったPDF→Markdown変換
│   ├── pdf2md_gemini.py               # Gemini 2.5 Proを使ったPDF→Markdown変換
│   ├── extract_sample_pages.py        # PDFからサンプルページを抽出するスクリプト
│   ├── embedding_analyzer.py          # エンベディング分析ツール
│   ├── compare_samples.py             # 類似/非類似問題の比較ツール
│   ├── compare_similarity.py          # 類似度比較ツール
│   ├── db_utils.py                    # データベース操作ユーティリティ
│   ├── README.md                      # srcディレクトリのREADME
│   ├── input/                         # 入力ファイル保存ディレクトリ
│   └── output/                        # 出力ファイル保存ディレクトリ
└── data/                         # データファイル（自動生成）
    ├── pdf/                      # 元のPDFファイル
    ├── images/                   # 画像化したファイル
    ├── ocr/                      # OCRテキスト
    ├── markdown/                 # 変換されたMarkdown
    ├── embedding/                # 画像・テキスト埋め込み（ベクトル）
    ├── claude/                   # Claude APIの出力結果
    ├── gemini/                   # Gemini APIの出力結果
    └── .gitkeep                  # 空ディレクトリをバージョン管理するためのファイル
```

## パイプラインの流れ

1. **[1] PDFを取得 → PDFページを画像化**  
   - `pdf_to_images.py`でPopplerを呼び出し、ページ単位に画像を生成
2. **[2] OCR処理 または 画像からの直接KaTeX変換**  
   - `ocr_engine.py`を介してTesseractかLLMを選択  
   - `--use-llm` オプションなどを指定してGemini/ClaudeのAPIを叩く
   - または `ocr_to_markdown.py` の `--direct-image-to-katex` オプションで画像から直接KaTeX形式に変換
3. **[3] OCRテキストをMarkdownへ変換**  
   - `ocr_to_markdown.py` でKaTeX数式や画像タグを整形
4. **[4] MarkdownをPostgreSQL/Auroraへインポート**  
   - `markdown_importer.py` で `questions` テーブルにINSERT  
   - 質問文、年度、問題IDなどを登録
5. **[5] 画像解析（マルチモーダルAPI）**  
   - `claude_image_analyzer.py`または`gemini_image_analyzer.py`で画像をAPIへ送信  
   - 解析結果をJSON形式で保存
   - `--multimodal-embedding`オプションを指定することでマルチモーダルエンベディングも生成
   - **日本語試験問題の構造化抽出**：
     - 問題番号、問題文、選択肢、解説、正解などを自動認識
     - 回路図や表なども検出して構造化
6. **[6] エンベディング生成**  
   - `generate_embedding.py`で解析結果のテキストからエンベディングベクトルを生成  
   - Gemini APIを使用した実際のエンベディング取得  
   - またはマルチモーダルエンベディングを使用（`gemini_image_analyzer.py`から直接生成）
7. **[7] エンベディングをDBに格納**  
   - `embed_importer.py`でPostgreSQLなどにベクトルを保存
8. **[8] メタデータ管理**  
   - 必要に応じて追加のメタデータをDBに格納

## 主な機能の詳細

### 画像から直接KaTeX変換

OCRテキストを経由せず、画像から直接KaTeX形式の数式を含むMarkdownを生成できます。

```bash
python src/ocr_to_markdown.py input_image.png output.md --direct-image-to-katex
```

### マルチモーダルエンベディング生成

テキストと画像の両方を考慮した高度なエンベディングを生成できます。回路図や図表を含む問題に特に効果的です。

```bash
python src/gemini_image_analyzer.py --input image.png --output output_dir --multimodal-embedding
```

### 実APIベースのエンベディング生成

Gemini APIを使用して実際のエンベディングを生成します。より高精度な類似検索が可能になります。

```bash
python src/generate_embedding.py --input analysis_results.json --api-key your_api_key
```

API呼び出しを避けたい場合は、ダミーエンベディングにフォールバックすることも可能です：

```bash
python src/generate_embedding.py --input analysis_results.json --no-api
```

## 使用例

### 基本的なパイプライン実行

```bash
./run_pipeline.sh data/pdf/sample.pdf --use-llm --year 2024 --gemini
```

### 画像から直接KaTeX変換を使用

```bash
./run_pipeline.sh data/pdf/sample.pdf --direct-katex --year 2024
```

### マルチモーダルエンベディングを生成

```bash
./run_pipeline.sh data/pdf/sample.pdf --use-llm --gemini --multimodal-embedding
```

### サンプルページ抽出と分析

```bash
./extract_sample.sh data/pdf/large_document.pdf --use-llm --claude --pages 10
```

## エンベディング分析ツール

エンベディングの距離分析と類似/非類似問題の比較を行うためのツールが提供されています。

### エンベディング距離分析

`embedding_analyzer.py`を使用して、エンベディング間の距離を計算し、可視化します。

```bash
# エンベディングの分析
python src/embedding_analyzer.py --input data/embedding --output data/embedding/analysis --mode analyze

# 特定のエンベディングファイルに対して類似/非類似ファイルを探す
python src/embedding_analyzer.py --input data/embedding/令和5年度_page_046_embedding.npy --output data/embedding/samples --mode sample
```

### 類似/非類似問題の比較

`compare_samples.py`を使用して、類似問題と非類似問題を視覚的に比較します。

```bash
# 比較レポートを作成
python src/compare_samples.py --input data/embedding/samples/sample_files.json --output data/embedding/comparison
```

これにより、指定された問題に対して類似度が高い問題と低い問題を比較したレポートが生成されます。
レポートには問題の画像とマークダウンテキストが含まれます。

### エンベディング類似度の比較

`compare_similarity.py`を使用して、複数のエンベディング間の類似度を比較します。

```bash
# 類似度比較を実行
python src/compare_similarity.py --input data/embedding --output data/similarity_report
```

## 参考リンク

- [try-vertex-ai-multimodal-search (zenn.dev)](https://zenn.dev/longrun_jp/articles/try-vertex-ai-multimodal-search)  
- [pgvector GitHub](https://github.com/pgvector/pgvector)

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
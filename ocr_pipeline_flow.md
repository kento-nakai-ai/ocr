# OCR処理パイプラインフロー図

```mermaid
flowchart TD
    subgraph "1. PDF処理"
        A[PDF入力] --> B[PDF→画像変換]
        B --> C[画像ファイル]
    end
    
    subgraph "2. OCR処理"
        C --> D1{OCR方式選択}
        D1 -->|Tesseract| D2[ローカルOCR処理]
        D1 -->|LLMベース| D3[Gemini/Claude OCR]
        D1 -->|直接変換| D4[画像→KaTeX直接変換]
        D2 --> E[OCRテキスト]
        D3 --> E
    end
    
    subgraph "3. Markdown変換"
        E --> F[OCR→Markdown変換]
        D4 --> F
        F --> G[Markdown文書]
    end
    
    subgraph "4. データベース登録"
        G --> H[Markdown→DB登録]
        H --> I[(PostgreSQL/Aurora)]
    end
    
    subgraph "5. 画像解析"
        C --> J1{AI選択}
        J1 -->|Gemini| J2[Gemini画像解析]
        J1 -->|Claude| J3[Claude画像解析]
        J2 --> K[JSON構造化データ]
        J3 --> K
    end
    
    subgraph "6. エンベディング"
        K --> L1{エンベディング方式}
        L1 -->|テキストのみ| L2[テキストエンベディング]
        L1 -->|マルチモーダル| L3[マルチモーダルエンベディング]
        L2 --> M[埋め込みベクトル]
        L3 --> M
        M --> N[エンベディング→DB登録]
        N --> I
    end
    
    subgraph "7. 類似検索"
        I --> O[類似問題検索]
        O --> P[類似度比較レポート]
    end
```

## 処理ステップ詳細

1. **PDF処理**
   - PDFファイルを入力として受け取り
   - Popplerを使用してページ単位に高品質画像に変換
   - 変換画像を一時保存

2. **OCR処理**
   - 3種類のOCR方式から選択可能:
     - Tesseract（ローカルOCR）
     - LLMベースOCR（Gemini/Claude）
     - 画像からKaTeXへの直接変換
   - OCRテキストファイルを生成

3. **Markdown変換**
   - OCRテキストをMarkdown形式に変換
   - 数式をKaTeX形式に変換
   - 図表を適切な画像タグに変換
   - レイアウトを整形

4. **データベース登録**
   - Markdownテキストをデータベースに登録
   - 問題ID、年度などのメタデータを付与

5. **画像解析**
   - GeminiまたはClaude APIを使用して画像を解析
   - 問題構造（問題文、選択肢、解説など）を自動認識
   - 回路図や表などの図形的要素も検出
   - JSON形式で構造化データを出力

6. **エンベディング生成**
   - 2種類のエンベディング方式:
     - テキストのみのエンベディング
     - マルチモーダルエンベディング（画像＋テキスト）
   - 埋め込みベクトルをデータベースに登録

7. **類似検索**
   - ベクトル類似度に基づく問題検索
   - 類似度比較レポートの生成

## パイプライン実行オプション

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
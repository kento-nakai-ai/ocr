# 実装した改善点とTODO解決策

## 1. マルチモーダルembeddings APIの利用

画像のまま埋め込みベクトルを生成し、回路図や図式情報を含めた検索を可能にするため、以下の実装を追加しました：

- `gemini_image_analyzer.py`に、画像のみのマルチモーダルエンベディング生成機能を追加
  ```python
  def get_multimodal_embedding(image_path, api_key=None, retry_count=3):
      # 画像ファイルからマルチモーダルエンベディングを取得する
  ```

- テキストと画像を組み合わせたマルチモーダルエンベディング生成機能も追加
  ```python
  def get_text_and_image_embedding(image_path, text_content, api_key=None, retry_count=3):
      # 画像とテキストの両方を含むマルチモーダルエンベディングを取得する
  ```

- コマンドラインオプションを追加して簡単に利用できるように設定
  ```
  python src/gemini_image_analyzer.py --input <画像パス> --multimodal-embedding
  ```

これにより、テキストだけでなく図式情報も含めた検索が可能になり、回路図や構造などの視覚的情報を失うことなく類似問題の検索ができるようになります。

## 2. エンベディングの直接DB保存

一時ファイル（.npy）として保存せず、エンベディングを取得した直後にデータベースに保存する機能を実装しました：

- `db_utils.py`を新規作成し、PostgreSQL（Aurora）との連携機能を実装
  - pgvector拡張のインストールとテーブル作成を行う`initialize_db()`関数
  - エンベディングを直接DBに保存する`save_embedding_to_db()`関数
  - 複数のエンベディングをバッチで保存する`save_multiple_embeddings_to_db()`関数
  - 類似検索を行う`find_similar_items()`関数

- `generate_embedding.py`を拡張し、DB直接保存オプションを追加
  ```python
  parser.add_argument('--direct-db', action='store_true', help='エンベディングを直接DBに保存する')
  parser.add_argument('--initialize-db', action='store_true', help='DBを初期化する')
  ```

これにより、以下のコマンドでエンベディングを生成と同時にDBに保存できるようになりました：
```bash
python src/generate_embedding.py --input data/embedding --direct-db
```

## 3. 運用フローの改善

埋め込みベクトルの追加登録を含む運用フローを改善しました：

1. **初期データのロード**
   ```bash
   # DBの初期化（pgvector拡張のインストールとテーブル作成）
   python src/generate_embedding.py --initialize-db
   
   # 既存データの一括登録
   python src/generate_embedding.py --input data/embedding --direct-db
   ```

2. **新規データの追加**
   - `gemini_image_analyzer.py`に`--direct-db`オプションを追加し、解析と同時にDBに保存できるようにしました
   - このフローにより、新しい問題画像が追加されるたびに、解析→エンベディング生成→DB保存を一連の流れで実行できます

3. **類似問題の検索**
   - `db_utils.py`の`find_similar_items()`関数を使用して、既存データから類似問題を検索できます
   - エンベディングタイプ（テキストのみ、画像のみ、マルチモーダル）を指定して検索することも可能

## 4. 画像から直接KaTeXへの変換

OCRの誤認識を減らすため、「画像→KaTeX」の直接変換機能をすでに実装済みであることを確認しました：

- `ocr_to_markdown.py`に`--direct-image-to-katex`オプションが実装されています
- このオプションを使用すると、中間のOCRステップを省略し、画像から直接KaTeX形式の数式を含むマークダウンを生成できます

```python
def direct_image_to_katex_conversion(self, image_path):
    # 画像から直接KaTeX形式の数式を抽出
```

以下のように使用できます：
```bash
python src/ocr_to_markdown.py --input image.png --output output.md --direct-image-to-katex
```

## 5. OCRと同時にエンベディング生成

OCR処理の段階で同時にエンベディングを生成する改善案については、以下の対応を行いました：

- `gemini_image_analyzer.py`を拡張し、画像解析と同時にテキストエンベディングとマルチモーダルエンベディングを生成できるようにしました
- これにより、OCR/画像解析のステップで一度にテキスト抽出とエンベディング生成の両方を行えるようになりました

```bash
python src/gemini_image_analyzer.py --input image.png --multimodal-embedding --direct-db
```

このコマンド一つで以下の処理が実行されます：
1. 画像の解析とテキスト抽出
2. 抽出したテキストからテキストエンベディングの生成
3. 画像のみのマルチモーダルエンベディングの生成
4. 画像とテキストを組み合わせたマルチモーダルエンベディングの生成
5. 生成したエンベディングのDB保存（`--direct-db`オプション使用時）

## 今後の改善点

1. **バッチ処理の最適化**
   - 大量のデータを処理する際のパフォーマンス向上
   - APIリクエストの並列処理とレート制限の考慮

2. **エラーハンドリングの強化**
   - API障害時の復旧処理
   - DB接続エラー時のリトライ機構

3. **UIの開発**
   - 類似問題検索用のウェブインターフェース
   - エンベディング生成・管理用の管理画面

4. **モニタリングと分析**
   - エンベディング品質の評価指標
   - 検索精度の継続的な改善 
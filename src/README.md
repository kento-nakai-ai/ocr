# PDF to Markdown 変換ツール

このツールは、PDFファイルをMarkdown形式に変換するためのユーティリティです。
ClaudeとGeminiというLLM（大規模言語モデル）を使用してPDFの内容を正確に抽出し、Markdown形式で保存します。

## 機能

- PDFの内容をMarkdown形式に変換
- ClaudeとGemini、2種類のAIモデルによる変換に対応
- バッチ処理機能（複数のPDFファイルを一括変換）

## 前提条件

- Python 3.8以上
- Anthropic APIキー（Claude用）
- Google API キー（Gemini用）

## セットアップ

1. 必要なパッケージをインストールします：

```bash
pip install -r requirements.txt
```

2. `.env`ファイルに必要なAPIキーを設定します：

```
CLAUDE_API_KEY=your_claude_api_key
GEMINI_API_KEY=your_gemini_api_key
```

## 使用方法

1. PDFファイルを`src/input`ディレクトリに配置します
2. 以下のコマンドを実行して変換します：

### Claude AIを使用する場合

```bash
python src/pdf2md_claude.py
```

### Gemini AIを使用する場合

```bash
python src/pdf2md_gemini.py
```

3. 変換結果は`src/output`ディレクトリに保存されます
   - ファイル名の形式: `{モデル名}_{元のファイル名}.md`

## 注意事項

- APIの使用には料金が発生する場合があります
- 大きなPDFファイルは処理に時間がかかることがあります
- モデルによって変換結果の品質が異なる場合があります

## トラブルシューティング

- APIキーが正しく設定されていることを確認してください
- PDFが大きすぎる場合は、複数のファイルに分割することを検討してください
- トークン制限に達した場合は、小さなPDFで試してください 
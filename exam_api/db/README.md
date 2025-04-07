# データベース構造と使用方法

このドキュメントでは、OCRシステムで使用されているデータベースの構造、インポート方法、および使用例について説明します。

## データベース概要

このシステムでは、PostgreSQLデータベースを使用して以下の情報を格納しています：

- OCRで処理された問題文（MarkdownおよびLaTeX形式）
- Gemini APIによって生成されたエンベディングベクトル
- 各問題の年度やIDなどのメタデータ

## データベーススキーマ

主要なテーブルは次の2つです：

### questionsテーブル

問題文とそのメタデータを格納するテーブルです。

| カラム名 | データ型 | 説明 |
|---------|---------|------|
| id | INTEGER | 自動生成される主キー |
| question_id | VARCHAR(50) | 問題の一意識別子（例：R04001） |
| year | INTEGER | 問題の年度 |
| content | TEXT | 問題の内容（Markdown形式） |
| created_at | TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | 更新日時 |

### embeddingsテーブル

Gemini APIで生成されたエンベディングベクトルを格納するテーブルです。

| カラム名 | データ型 | 説明 |
|---------|---------|------|
| id | INTEGER | 自動生成される主キー |
| question_id | VARCHAR(50) | 関連する問題のID（questionsテーブルの外部キー） |
| embedding_type | VARCHAR(50) | エンベディングのタイプ（例：text） |
| embedding | VECTOR(768) | 768次元のエンベディングベクトル |
| metadata | JSONB | エンベディングに関する追加情報 |
| created_at | TIMESTAMP | 作成日時 |

## データベースのインポート方法

### 前提条件

- PostgreSQLがインストールされていること
- pgvector拡張機能がインストールされていること

### バックアップからのリストア

以下のコマンドで、データベースバックアップをリストアできます：

1. データベースを新規作成（存在しない場合）：
   ```bash
   createdb questions_db
   ```

2. pgvector拡張機能のインストール：
   ```bash
   psql -d questions_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

3. バックアップからリストア：
   ```bash
   psql -d questions_db -f db/backups/questions_db_backup.sql
   ```

### パイプラインを使ったデータ生成

または、以下のパイプラインを実行してデータを生成することもできます：

```bash
./run_pipeline.sh data/pdf/令和4年度_sample.pdf --direct-katex --year 2023
```

## 主要テーブル間の関係

`questions`テーブルと`embeddings`テーブルは`question_id`カラムを通じて関連付けられています：

```
questions(question_id) <---> embeddings(question_id)
```

1つの問題に対して1つのエンベディングが格納されています。

## サンプルクエリ

### 全ての問題を取得

```sql
SELECT id, question_id, year, content 
FROM questions 
ORDER BY question_id;
```

### 特定の年度の問題を取得

```sql
SELECT * 
FROM questions 
WHERE year = 2023;
```

### 問題とそのエンベディングを取得

```sql
SELECT q.question_id, q.content, e.embedding 
FROM questions q
JOIN embeddings e ON q.question_id = e.question_id
WHERE q.question_id = 'R04001';
```

### 類似度検索（ベクトル検索）

特定の問題と類似した他の問題を検索する例：

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

## その他の情報

- データベース接続情報は`.env`ファイルで設定できます
- pgvectorについての詳細は[公式ドキュメント](https://github.com/pgvector/pgvector)を参照してください 
# タグシステムの使用方法

このドキュメントでは、タグシステムの概要、データベーススキーマ、および使用方法について説明します。

## 1. タグシステム概要

タグシステムは問題に対して複数の属性（タグ）を柔軟に付与・管理するためのシステムです。これにより、問題の難易度、カテゴリ、問題タイプなどによる検索や集計が可能になります。

主な機能：
- 問題へのタグ付け
- タグベースの問題検索
- タグ定義の追加・更新
- タグによる問題集計・統計

## 2. データベーススキーマ

タグシステムは主に2つのテーブルで構成されています：

### 2.1 タグ定義テーブル（tag_definitions）

タグの種類や使用可能な値などを定義するテーブルです。

| カラム名 | データ型 | 説明 |
|---------|---------|------|
| id | SERIAL | 自動生成される主キー |
| tag_key | VARCHAR(50) | タグのキー（例：difficulty, category）|
| tag_type | ENUM | タグのタイプ（Flag, Categorical, Array, Enum, Text） |
| description | TEXT | タグの説明 |
| possible_values | JSONB | 使用可能な値のリスト（JSONBで格納） |
| remarks | TEXT | 備考・運用例 |
| created_at | TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | 更新日時 |

### 2.2 問題タグテーブル（question_tags）

問題とタグの関連付けを格納するテーブルです。

| カラム名 | データ型 | 説明 |
|---------|---------|------|
| id | SERIAL | 自動生成される主キー |
| question_id | VARCHAR(50) | 問題ID（questionsテーブルの外部キー） |
| tag_key | VARCHAR(50) | タグのキー（tag_definitionsテーブルの外部キー） |
| tag_value | TEXT | タグの値 |
| ai_inference | VARCHAR(20) | AIによる推定か手動かを示す（manual, by_AI, by_expert） |
| remarks | TEXT | 備考 |
| created_at | TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | 更新日時 |

## 3. 事前定義されたタグ

以下のタグが事前に定義されています：

| タグキー | タグタイプ | 可能な値 | 説明 |
|---------|----------|---------|------|
| is_mandatory | Flag | true / false | 必須問題かどうか |
| difficulty | Categorical | LOW / MID / HIGH | 問題の難易度 |
| problem_type | Categorical | calc / memorization / ... | 問題のタイプ（計算問題、暗記問題など） |
| category | Categorical | law / safety / equipment / ... | 問題のカテゴリ（法規、安全管理、設備など） |
| construction_requirement | Flag | "must_50_percent" など | 施工問題の特別要件 |
| year_list | Array | ["2021", "2022", ...] | 出題された年度のリスト |
| exam_type | Enum | 1級電気 / 1級管 / 2級電気 / 2級管 / ... | 試験種別 |
| sub_category | Categorical | 基礎 / 応用 / 施工計画 / ... | 詳細カテゴリ |
| ai_inference | Flag | manual / by_AI / by_expert / ... | 付与方法 |
| remarks | Text | 自由記述 | タグ付け理由や注意事項 |

## 4. 使用例

### 4.1 Python APIの使用例

```python
from tag_manager import TagManager
import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# データベース接続設定
db_config = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

# TagManagerの初期化とコンテキストマネージャーとしての使用
with TagManager(db_config) as tag_manager:
    # 問題にタグを追加する
    tag_manager.add_tag_to_question(
        question_id="R04001",
        tag_key="difficulty",
        tag_value="HIGH",
        ai_inference="by_expert",
        remarks="専門家が難易度を評価"
    )
    
    # 複数のタグを追加する
    tag_manager.add_tag_to_question("R04001", "category", "law")
    tag_manager.add_tag_to_question("R04001", "problem_type", "calc")
    tag_manager.add_tag_to_question("R04001", "is_mandatory", "true")
    
    # 年度情報の追加（配列データ）
    tag_manager.add_tag_to_question("R04001", "year_list", json.dumps(["2020", "2021", "2022"]))
    
    # 問題のすべてのタグを取得する
    tags = tag_manager.get_question_tags("R04001")
    print(f"問題R04001のタグ: {tags}")
    
    # 難易度が「HIGH」の問題を検索する
    high_difficulty_questions = tag_manager.get_questions_by_difficulty("HIGH")
    print(f"難易度HIGHの問題数: {len(high_difficulty_questions)}")
    
    # 法規の計算問題を検索する
    law_calc_questions = tag_manager.get_questions_by_problem_type_and_category("calc", "law")
    print(f"法規の計算問題数: {len(law_calc_questions)}")
    
    # 頻出問題（2年以上出題された問題）を取得する
    frequent_questions = tag_manager.get_frequently_asked_questions(min_years=2)
    print(f"頻出問題数: {len(frequent_questions)}")
    
    # カテゴリごとの問題数を集計する
    category_stats = tag_manager.get_stats_by_tag("category")
    print("カテゴリ別問題数:")
    for category, count in category_stats.items():
        print(f"  {category}: {count}問")
```

### 4.2 SQLクエリの使用例

#### タグ定義を取得する

```sql
SELECT * FROM tag_definitions ORDER BY tag_key;
```

#### 特定のタグを持つ問題を検索する

```sql
-- 難易度が「HIGH」の問題を検索
SELECT q.question_id, q.content 
FROM questions q
JOIN question_tags qt ON q.question_id = qt.question_id
WHERE qt.tag_key = 'difficulty' AND qt.tag_value = 'HIGH';

-- 必須問題を検索
SELECT q.question_id, q.content 
FROM questions q
JOIN question_tags qt ON q.question_id = qt.question_id
WHERE qt.tag_key = 'is_mandatory' AND qt.tag_value = 'true';
```

#### 複数のタグ条件で問題を検索する

```sql
-- カテゴリ「law」かつ難易度「HIGH」の問題を検索
SELECT * FROM get_questions_by_multiple_tags('{"category": "law", "difficulty": "HIGH"}');

-- 1級電気の必須問題を検索
SELECT * FROM get_questions_by_multiple_tags('{"exam_type": "1級電気", "is_mandatory": "true"}');
```

#### タグの統計情報を取得する

```sql
-- カテゴリごとの問題数
SELECT tag_value AS category, COUNT(*) AS count
FROM question_tags
WHERE tag_key = 'category'
GROUP BY tag_value
ORDER BY count DESC;

-- 難易度ごとの問題数
SELECT tag_value AS difficulty, COUNT(*) AS count
FROM question_tags
WHERE tag_key = 'difficulty'
GROUP BY tag_value
ORDER BY count DESC;
```

## 5. スキーマ更新方法

タグシステムのスキーマは以下のSQLスクリプトを実行して更新できます：

```bash
psql -d your_database_name -f db/tags_schema.sql
```

## 6. バックアップとリストア

### バックアップ

```bash
pg_dump -t tag_definitions -t question_tags your_database_name > db/backups/tags_backup_$(date +%Y%m%d).sql
```

### リストア

```bash
psql -d your_database_name -f db/backups/tags_backup_20230407.sql
``` 
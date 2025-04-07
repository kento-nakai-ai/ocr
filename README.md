# 資格試験対策システム API

## 概要

このプロジェクトは、資格試験の頻出問題や苦手問題を提供し、ユーザーの解答を記録・分析するためのREST APIを実装しています。AWS Cognitoを使用してユーザー認証を行い、JSON Web Token (JWT) によるセキュアなアクセス制御を提供します。

## 機能一覧

- **頻出問題API**: ユーザーの試験種別に合わせた頻出問題を取得
- **ユーザー回答API**: ユーザーの回答を記録し、合格率スコアを計算
- **成績統計API**: ユーザーの学習進捗や成績の履歴を取得
- **頻出問題登録API**: 週次バッチ処理用の頻出問題一括登録機能（管理者向け）

## 技術スタック

- **フレームワーク**: FastAPI
- **データベース**: SQLAlchemy (ORM)
- **認証**: AWS Cognito + JWT
- **依存性管理**: Requirements.txt
- **コードスタイル**: PEP 8準拠

## インストールと実行方法

### 環境構築

1. Pythonのインストール (3.9以上)
```bash
# バージョン確認
python --version
```

2. 仮想環境の作成と有効化
```bash
# 仮想環境の作成
python -m venv venv

# 有効化 (Windows)
venv\Scripts\activate

# 有効化 (Mac/Linux)
source venv/bin/activate
```

3. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

### 環境変数の設定

`.env` ファイルを作成し、以下の環境変数を設定してください。

```
# AWS Cognito設定
AWS_REGION=ap-northeast-1
COGNITO_USER_POOL_ID=your-user-pool-id
COGNITO_APP_CLIENT_ID=your-app-client-id

# データベース設定
DATABASE_URL=sqlite:///./exam_api.db
# 本番環境では PostgreSQL 等を使用
# DATABASE_URL=postgresql://user:password@localhost/dbname

# デバッグ設定
SQL_DEBUG=0
```

### アプリケーションの起動

```bash
# 開発用サーバーの起動
uvicorn app.main:app --reload

# 本番用サーバーの起動
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API ドキュメント

API ドキュメントは自動生成されます。サーバー起動後、以下のURLでアクセスできます。

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## テスト

テストの実行方法:

```bash
pytest
```

## ディレクトリ構造

```
exam_api/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── question.py
│   │   ├── frequent_question.py
│   │   ├── user_answer.py
│   │   └── user_stat.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── frequent_questions.py
│   │   └── user_answers.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── frequent_question_service.py
│   │   └── user_answer_service.py
│   └── utils/
│       ├── __init__.py
│       └── auth.py
├── tests/
│   ├── __init__.py
│   ├── test_frequent_questions.py
│   └── test_user_answers.py
├── .env
├── .gitignore
├── README.md
└── requirements.txt
```

## ライセンス

このプロジェクトは非公開です。無断での使用、配布、改変は禁止されています。 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Claude APIを使用して画像解析を行うスクリプト

このスクリプトは、PDFから抽出された画像ファイルをClaude APIに送信し、
画像の内容解析結果を取得します。解析結果はJSON形式で保存され、
必要に応じてPostgreSQLデータベースに保存することも可能です。

要件:
    - anthropic パッケージ: Claude APIの公式Pythonクライアント
    - python-dotenv: 環境変数管理のためのライブラリ
    - psycopg2: PostgreSQL用のPythonアダプタ (DB保存時に使用)

使用例:
    python claude_image_analyzer.py image.png --output result.json
    python claude_image_analyzer.py --batch folder/ --output_dir results/
"""

import os
import sys
import argparse
import json
import logging
import glob
import base64
from datetime import datetime
import psycopg2
from dotenv import load_dotenv

# Claude APIライブラリのインポート
try:
    import anthropic
except ImportError:
    print("Anthropic APIパッケージがインストールされていません。")
    print("pip install anthropic で必要なパッケージをインストールしてください。")
    sys.exit(1)


# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClaudeImageAnalyzer:
    """
    Claude APIを使用して画像解析を行うクラス
    """
    
    def __init__(self, api_key=None, model="claude-3-opus-20240229", db_config=None):
        """
        初期化
        
        Args:
            api_key (str, optional): Claude API キー
            model (str, optional): 使用するClaudeモデル
            db_config (dict, optional): データベース接続設定
        """
        # 環境変数から設定を読み込む
        load_dotenv()
        
        # API設定
        self.api_key = api_key or os.getenv('CLAUDE_API_KEY')
        if not self.api_key:
            raise ValueError("Claude API キーが設定されていません。環境変数 CLAUDE_API_KEY を設定してください。")
        
        self.model = model
        logger.info(f"モデル: {self.model}")
        
        # クライアント初期化
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
        # DB設定（オプション）
        self.db_config = db_config or {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'questions_db'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '')
        }
    
    def encode_image_base64(self, image_path):
        """
        画像ファイルをBase64エンコードします
        
        Args:
            image_path (str): 画像ファイルのパス
            
        Returns:
            str: Base64エンコードされた画像データ
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def analyze_image(self, image_path, prompt=None, question_id=None):
        """
        Claude APIを使用して画像を解析します
        
        Args:
            image_path (str): 画像ファイルのパス
            prompt (str, optional): カスタムプロンプト
            question_id (str, optional): 関連する問題ID
            
        Returns:
            dict: 解析結果
        """
        # 画像ファイルの存在確認
        if not os.path.exists(image_path):
            logger.error(f"画像ファイルが見つかりません: {image_path}")
            return None
        
        # 画像ファイルの拡張子とMIMEタイプの確認
        _, ext = os.path.splitext(image_path)
        ext = ext.lower()
        
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif'
        }
        
        if ext not in mime_types:
            logger.error(f"サポートされていない画像形式です: {ext}")
            return None
        
        mime_type = mime_types[ext]
        
        # デフォルトプロンプト
        if prompt is None:
            prompt = """
            この画像を詳細に解析してください。以下の情報を抽出し、JSON形式で返してください。
            
            1. 画像の種類 (図表、数式、イラスト、フローチャートなど)
            2. 画像の主要な内容の説明
            3. 画像に含まれるテキスト
            4. 数式がある場合はLaTeX形式で表現
            5. 複数の要素がある場合は要素ごとに分けて説明
            
            結果はJSON形式で返してください。形式例:
            {
                "type": "画像の種類",
                "description": "画像の説明",
                "text_content": "画像内のテキスト",
                "math_expressions": ["LaTeX形式の数式1", "LaTeX形式の数式2"],
                "elements": [
                    {"name": "要素1", "description": "要素1の説明"},
                    {"name": "要素2", "description": "要素2の説明"}
                ]
            }
            """
        
        try:
            # 画像をBase64エンコード
            base64_image = self.encode_image_base64(image_path)
            
            logger.info(f"画像解析リクエスト: {image_path}")
            
            # Claude APIリクエスト
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.0,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": base64_image}}
                        ]
                    }
                ]
            )
            
            # レスポンスからJSONを抽出
            response_text = message.content[0].text
            
            # JSONとして解析
            # Claude APIの応答から適切なJSON部分を抽出
            try:
                # JSON部分の抽出
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start != -1 and json_end != -1:
                    json_str = response_text[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    # JSONが見つからない場合、テキスト応答全体を含む結果を作成
                    result = {
                        "type": "unknown",
                        "raw_response": response_text,
                        "error": "JSONフォーマットが見つかりませんでした"
                    }
            except json.JSONDecodeError:
                result = {
                    "type": "unknown",
                    "raw_response": response_text,
                    "error": "JSONデコードエラー"
                }
            
            # メタデータを追加
            result['image_path'] = image_path
            result['filename'] = os.path.basename(image_path)
            result['analysis_time'] = datetime.now().isoformat()
            
            if question_id:
                result['question_id'] = question_id
            
            logger.info(f"画像解析完了: {image_path}")
            return result
            
        except Exception as e:
            logger.error(f"画像解析エラー: {str(e)}")
            return {
                "error": str(e),
                "image_path": image_path,
                "filename": os.path.basename(image_path),
                "analysis_time": datetime.now().isoformat()
            }
    
    def save_result_to_json(self, result, output_path):
        """
        解析結果をJSONファイルに保存します
        
        Args:
            result (dict): 解析結果
            output_path (str): 出力ファイルのパス
            
        Returns:
            bool: 保存が成功したかどうか
        """
        try:
            # 出力ディレクトリの確認と作成
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # JSONとして保存
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"結果をJSONとして保存しました: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"JSON保存エラー: {str(e)}")
            return False
    
    def save_result_to_db(self, result, question_id=None):
        """
        解析結果をデータベースに保存します
        
        Args:
            result (dict): 解析結果
            question_id (str, optional): 関連する問題ID
            
        Returns:
            bool: 保存が成功したかどうか
        """
        # question_idがない場合、結果から取得
        if not question_id and 'question_id' in result:
            question_id = result['question_id']
        
        # それでもquestion_idがない場合はエラー
        if not question_id:
            logger.error("データベース保存エラー: question_idが指定されていません")
            return False
        
        try:
            # データベース接続
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # figure_metaテーブルの存在を確認
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'figure_meta'
                );
            """)
            table_exists = cursor.fetchone()[0]
            
            # テーブルが存在しない場合は作成
            if not table_exists:
                logger.info("figure_metaテーブルが存在しないため作成します")
                cursor.execute("""
                    CREATE TABLE figure_meta (
                        id SERIAL PRIMARY KEY,
                        question_id VARCHAR(50) REFERENCES questions(id),
                        image_path TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        image_type TEXT,
                        description TEXT,
                        text_content TEXT,
                        math_expressions JSONB,
                        elements JSONB,
                        raw_data JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
            
            # 必要なデータを抽出
            image_path = result.get('image_path', '')
            filename = result.get('filename', '')
            image_type = result.get('type', 'unknown')
            description = result.get('description', '')
            text_content = result.get('text_content', '')
            math_expressions = json.dumps(result.get('math_expressions', []))
            elements = json.dumps(result.get('elements', []))
            raw_data = json.dumps(result)
            
            # INSERTクエリの実行
            cursor.execute(
                """
                INSERT INTO figure_meta 
                (question_id, image_path, filename, image_type, description, text_content, math_expressions, elements, raw_data) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (question_id, image_path, filename, image_type, description, text_content, math_expressions, elements, raw_data)
            )
            
            # コミット
            conn.commit()
            
            # 接続のクローズ
            cursor.close()
            conn.close()
            
            logger.info(f"結果をデータベースに保存しました: question_id={question_id}, image={filename}")
            return True
            
        except Exception as e:
            logger.error(f"データベース保存エラー: {str(e)}")
            return False
    
    def batch_analyze(self, folder_path, output_dir=None, save_to_db=False, question_id_mapping=None):
        """
        フォルダ内のすべての画像ファイルを解析します
        
        Args:
            folder_path (str): 画像ファイルを含むフォルダのパス
            output_dir (str, optional): JSONファイルの出力ディレクトリ
            save_to_db (bool, optional): 結果をデータベースに保存するかどうか
            question_id_mapping (dict, optional): ファイル名とquestion_idのマッピング
            
        Returns:
            tuple: (成功件数, 失敗件数)
        """
        # フォルダの存在確認
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            logger.error(f"フォルダが見つかりません: {folder_path}")
            return 0, 0
        
        # 出力ディレクトリの設定
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 画像ファイルのリストを取得
        image_files = []
        for ext in ['.png', '.jpg', '.jpeg', '.gif']:
            image_files.extend(glob.glob(os.path.join(folder_path, f'*{ext}')))
        
        total_files = len(image_files)
        
        if total_files == 0:
            logger.warning(f"解析対象の画像ファイルが見つかりません: {folder_path}")
            return 0, 0
        
        logger.info(f"バッチ解析開始: {folder_path} ({total_files}ファイル)")
        
        success_count = 0
        failure_count = 0
        
        for file_path in image_files:
            file_name = os.path.basename(file_path)
            
            # question_idの取得
            question_id = None
            if question_id_mapping and file_name in question_id_mapping:
                question_id = question_id_mapping[file_name]
            else:
                # ファイル名から推測（例: Q001_page01.png → Q001）
                parts = file_name.split('_')
                if len(parts) > 0:
                    question_id = parts[0]
            
            # 解析実行
            result = self.analyze_image(file_path, question_id=question_id)
            
            if result:
                # JSON保存
                if output_dir:
                    output_path = os.path.join(output_dir, f"{os.path.splitext(file_name)[0]}_analysis.json")
                    self.save_result_to_json(result, output_path)
                
                # DB保存
                if save_to_db:
                    self.save_result_to_db(result, question_id)
                
                success_count += 1
            else:
                failure_count += 1
                
            logger.info(f"進捗: {success_count+failure_count}/{total_files} (成功: {success_count}, 失敗: {failure_count})")
        
        logger.info(f"バッチ解析完了: 成功={success_count}, 失敗={failure_count}")
        return success_count, failure_count


def main():
    """
    コマンドライン引数を解析し、画像解析を実行
    """
    parser = argparse.ArgumentParser(description='Claude APIを使用して画像解析を行います')
    parser.add_argument('image_path', help='画像ファイルまたはフォルダのパス')
    parser.add_argument('--output', '-o', help='出力JSONファイルのパス')
    parser.add_argument('--output_dir', '-d', help='バッチモード時の出力ディレクトリ')
    parser.add_argument('--batch', '-b', action='store_true', help='バッチモード (フォルダ内の全ファイルを処理)')
    parser.add_argument('--save_to_db', '-s', action='store_true', help='結果をデータベースに保存する')
    parser.add_argument('--question_id', '-q', help='関連する問題ID')
    parser.add_argument('--model', '-m', default="claude-3-opus-20240229", help='使用するClaudeモデル')
    parser.add_argument('--mapping', help='ファイル名とquestion_idのマッピングを含むJSONファイルのパス')
    
    args = parser.parse_args()
    
    # Claude APIキーの確認
    api_key = os.getenv('CLAUDE_API_KEY')
    if not api_key:
        logger.error("Claude API キーが設定されていません。環境変数 CLAUDE_API_KEY を設定してください。")
        return
    
    # マッピングファイルの読み込み
    question_id_mapping = None
    if args.mapping and os.path.exists(args.mapping):
        try:
            with open(args.mapping, 'r', encoding='utf-8') as f:
                question_id_mapping = json.load(f)
            logger.info(f"マッピングファイルを読み込みました: {len(question_id_mapping)}件")
        except Exception as e:
            logger.error(f"マッピングファイルの読み込みエラー: {str(e)}")
    
    # 解析器の初期化
    analyzer = ClaudeImageAnalyzer(api_key=api_key, model=args.model)
    
    # バッチモードかどうかで処理を分岐
    if args.batch or os.path.isdir(args.image_path):
        analyzer.batch_analyze(
            args.image_path,
            args.output_dir,
            args.save_to_db,
            question_id_mapping
        )
    else:
        result = analyzer.analyze_image(args.image_path, question_id=args.question_id)
        
        if result:
            # JSON保存
            if args.output:
                analyzer.save_result_to_json(result, args.output)
            else:
                # 標準出力に結果を表示
                print(json.dumps(result, ensure_ascii=False, indent=2))
            
            # DB保存
            if args.save_to_db:
                analyzer.save_result_to_db(result, args.question_id)


if __name__ == "__main__":
    main() 
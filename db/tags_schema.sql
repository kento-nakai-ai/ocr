-- タグ一覧表に基づいたデータベーススキーマ
-- 作成日: 2023年4月7日

-- タグタイプのEnum型を作成
CREATE TYPE tag_type AS ENUM ('Flag', 'Categorical', 'Array', 'Enum', 'Text');

-- 可能な値のEnum型を作成
CREATE TYPE difficulty_level AS ENUM ('LOW', 'MID', 'HIGH');
CREATE TYPE problem_type_value AS ENUM ('calc', 'memorization');
CREATE TYPE category_value AS ENUM ('law', 'safety', 'equipment');
CREATE TYPE exam_type_value AS ENUM ('1級電気', '1級管', '2級電気', '2級管');

-- タグ定義テーブルの作成
CREATE TABLE tag_definitions (
    id SERIAL PRIMARY KEY,
    tag_key VARCHAR(50) NOT NULL UNIQUE,
    tag_type tag_type NOT NULL,
    description TEXT NOT NULL,
    possible_values JSONB, -- 可能な値の配列またはオブジェクト
    remarks TEXT, -- 備考・運用例
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 問題タグテーブルの作成
CREATE TABLE question_tags (
    id SERIAL PRIMARY KEY,
    question_id VARCHAR(50) NOT NULL,
    tag_key VARCHAR(50) NOT NULL,
    tag_value TEXT NOT NULL,
    ai_inference VARCHAR(20), -- AIによる推定か手動かを示す
    remarks TEXT, -- 備考
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE,
    FOREIGN KEY (tag_key) REFERENCES tag_definitions(tag_key) ON DELETE CASCADE,
    UNIQUE (question_id, tag_key) -- 一つの問題に対して同じタグキーは一度だけ
);

-- インデックスの作成
CREATE INDEX idx_question_tags_question_id ON question_tags(question_id);
CREATE INDEX idx_question_tags_tag_key ON question_tags(tag_key);
CREATE INDEX idx_question_tags_tag_value ON question_tags(tag_value);

-- タグ定義の初期データ挿入
INSERT INTO tag_definitions (tag_key, tag_type, description, possible_values, remarks)
VALUES 
    ('is_mandatory', 'Flag', '必須問題に設定すると、合格率計算で大きな重み付けを与えられる。（施工管理法など） falseなら選択問題扱い', 
     '["true", "false"]'::JSONB, 
     '施工問題でも特定問題のみ is_mandatory=true にし、必須正解比率を別途計算する。合格率ロジックで 必須問題を1問落とす→-20%など。'),
    
    ('difficulty', 'Categorical', '難易度(暗記問題ならLOW、計算問題ならHIGHなど)。専門家評価 or AI推定', 
     '["LOW", "MID", "HIGH"]'::JSONB, 
     '合格率で難易度HIGH正解は+%加点など。'),
    
    ('problem_type', 'Categorical', '問題タイプ：暗記 vs 計算など。カテゴリ(category)と並列で管理。', 
     '["calc", "memorization"]'::JSONB, 
     '例: problem_type=calc + category=law →「法規の計算問題」。コレを独立タグにすることで、集計・抽出が柔軟に。'),
    
    ('category', 'Categorical', '単元や大分類 (法規,安全管理,設備工事など)。 同じ問題で問題タイプ(暗記/計算)と両立する。', 
     '["law", "safety", "equipment"]'::JSONB, 
     '例: category=safety + problem_type=memorization →「安全管理の暗記問題」。'),
    
    ('construction_requirement', 'Flag', '施工問題で「50%以上必須」など特別要件を表す。', 
     NULL, 
     '例: construction_requirement="must_50_percent" →合格率計算時に「施工問題のうち50%以下だと不合格」など特別ロジックを設定可能。'),
    
    ('year_list', 'Array', '同一問題の複数年度出題を記録。頻出度(直近3年など)に反映', 
     NULL, 
     '例: "2020,2021,2022" →3年連続出題されている。スコア計算でボーナスなど付与可。'),
    
    ('exam_type', 'Enum', '資格試験種別(1級/2級,電気/管など)', 
     '["1級電気", "1級管", "2級電気", "2級管"]'::JSONB, 
     'DB検索やユーザー受験科目に合わせた出題制御に活用。'),
    
    ('sub_category', 'Categorical', 'カテゴリをさらに細分化する場合に使う。', 
     '["基礎", "応用", "施工計画"]'::JSONB, 
     '例: "calc(大分類)" → "電気理論( sub_category )"。不要なら運用しなくてもよい。'),
    
    ('ai_inference', 'Flag', 'AI推定か人手付与かを区別。', 
     '["manual", "by_AI", "by_expert"]'::JSONB, 
     '後々AIモデルで自動タグ付けする際に、「推定確度」などのメタ情報を格納してもよい。'),
    
    ('remarks', 'Text', 'タグ付け理由や注意事項など。', 
     NULL, 
     '例: "この問題は2023改訂の安全基準...必須扱い"');

-- タグ検索用の関数の作成
CREATE OR REPLACE FUNCTION get_questions_by_tag(p_tag_key VARCHAR, p_tag_value VARCHAR)
RETURNS TABLE (
    question_id VARCHAR,
    content TEXT,
    year INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT q.question_id, q.content, q.year
    FROM questions q
    JOIN question_tags t ON q.question_id = t.question_id
    WHERE t.tag_key = p_tag_key AND t.tag_value = p_tag_value;
END;
$$ LANGUAGE plpgsql;

-- 複数タグでのAND検索用関数
CREATE OR REPLACE FUNCTION get_questions_by_multiple_tags(tag_conditions JSONB)
RETURNS TABLE (
    question_id VARCHAR,
    content TEXT,
    year INTEGER
) AS $$
DECLARE
    tag_key TEXT;
    tag_value TEXT;
BEGIN
    -- 初期クエリ結果（すべての問題）
    CREATE TEMP TABLE temp_results AS
    SELECT question_id FROM questions;
    
    -- 各タグ条件について繰り返し
    FOR tag_key, tag_value IN
        SELECT * FROM jsonb_each_text(tag_conditions)
    LOOP
        -- 条件に一致する問題IDのみを残す
        DELETE FROM temp_results tr
        WHERE NOT EXISTS (
            SELECT 1 FROM question_tags qt
            WHERE qt.question_id = tr.question_id
            AND qt.tag_key = tag_key
            AND qt.tag_value = tag_value
        );
    END LOOP;
    
    -- 最終結果の取得
    RETURN QUERY
    SELECT q.question_id, q.content, q.year
    FROM questions q
    JOIN temp_results tr ON q.question_id = tr.question_id;
    
    -- 一時テーブルを削除
    DROP TABLE temp_results;
END;
$$ LANGUAGE plpgsql;

-- 例: get_questions_by_multiple_tags('{"difficulty": "HIGH", "category": "law"}') 
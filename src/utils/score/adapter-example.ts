/**
 * 合格率計算アダプターの使用例
 * 
 * @description 実際のアプリケーションで合格率計算アダプターをどのように使用するかの例を示します。
 * これは、実際のデータベースからのデータ形式を模倣しています。
 */

import { ScoreCalculator } from './adapter';

/**
 * アダプタークラスの使用方法を示す関数
 */
function demonstrateScoreCalculatorUsage(): void {
  // データベースから取得されたかのような問題データ
  const dbQuestions = [
    { id: 101, is_mandatory: 1, difficulty: 'MID', question_text: '問題1の内容...' },
    { id: 102, is_mandatory: 1, difficulty: 'MID', question_text: '問題2の内容...' },
    { id: 103, is_mandatory: 1, difficulty: 'LOW', question_text: '問題3の内容...' },
    { id: 104, is_mandatory: 0, difficulty: 'HIGH', question_text: '問題4の内容...' },
    { id: 105, is_mandatory: 0, difficulty: 'HIGH', question_text: '問題5の内容...' },
    { id: 106, is_mandatory: 0, difficulty: 'MID', question_text: '問題6の内容...' },
    { id: 107, is_mandatory: 0, difficulty: 'LOW', question_text: '問題7の内容...' },
    { id: 108, is_mandatory: 0, difficulty: 'LOW', question_text: '問題8の内容...' },
    { id: 109, is_mandatory: 0, difficulty: 'MID', question_text: '問題9の内容...' },
    { id: 110, is_mandatory: 0, difficulty: 'LOW', question_text: '問題10の内容...' },
  ];

  // データベースから取得されたかのようなユーザー回答データ
  const dbUserAnswers = [
    { id: 1001, user_id: 5001, question_id: 101, is_correct: 1, answer_text: 'ユーザーの回答...' },
    { id: 1002, user_id: 5001, question_id: 102, is_correct: 1, answer_text: 'ユーザーの回答...' },
    { id: 1003, user_id: 5001, question_id: 103, is_correct: 1, answer_text: 'ユーザーの回答...' },
    { id: 1004, user_id: 5001, question_id: 104, is_correct: 1, answer_text: 'ユーザーの回答...' },
    { id: 1005, user_id: 5001, question_id: 105, is_correct: 1, answer_text: 'ユーザーの回答...' },
    { id: 1006, user_id: 5001, question_id: 106, is_correct: 1, answer_text: 'ユーザーの回答...' },
    { id: 1007, user_id: 5001, question_id: 107, is_correct: 1, answer_text: 'ユーザーの回答...' },
    { id: 1008, user_id: 5001, question_id: 108, is_correct: 0, answer_text: 'ユーザーの回答...' },
    { id: 1009, user_id: 5001, question_id: 109, is_correct: 0, answer_text: 'ユーザーの回答...' },
    { id: 1010, user_id: 5001, question_id: 110, is_correct: 0, answer_text: 'ユーザーの回答...' },
  ];

  console.log('=== アダプタークラスの使用例 ===');
  console.log('データベースからの問題・回答データを使用した合格率計算\n');

  // 合格率の計算
  const scoreResult = ScoreCalculator.calculateFromDbFormat(dbQuestions, dbUserAnswers);
  
  // 合格率の表示
  console.log('▼ 合格率詳細情報:');
  console.log(ScoreCalculator.formatResult(scoreResult));
  
  // 合格判定
  console.log('\n▼ 合格判定:');
  const passed = ScoreCalculator.hasPassed(scoreResult.finalScore);
  console.log(`合格: ${passed ? '○' : '×'}`);
  
  // 評価メッセージ
  console.log('\n▼ 評価メッセージ:');
  console.log(ScoreCalculator.getEvaluationMessage(scoreResult.finalScore));
  
  // APIレスポンス例
  console.log('\n▼ APIレスポンス例:');
  console.log(JSON.stringify(ScoreCalculator.createApiResponse(scoreResult), null, 2));
}

// サンプルを実行
demonstrateScoreCalculatorUsage(); 
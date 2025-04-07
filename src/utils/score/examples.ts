/**
 * 合格率計算の使用例とサンプルテストケース
 * 
 * @description このファイルは合格率計算モジュールの使用方法を示す例と、
 * 実際の計算結果を検証するためのサンプルテストケースを提供します。
 * 開発者がモジュールの動作を理解しやすくするためのものです。
 */

import { 
  calculateScore,
  ScoreCalculationInput,
  Question,
  UserAnswer,
  QuestionDifficulty,
  ScoreConfig
} from './index';
import { formatScoreDetails } from './utils';

/**
 * サンプルの問題と回答データを作成する関数
 * 
 * @returns サンプルの入力データ
 */
export const createSampleInput = (): ScoreCalculationInput => {
  // サンプル問題データ
  const questions: Question[] = [
    { id: '1', isMandatory: true, difficulty: QuestionDifficulty.MID },
    { id: '2', isMandatory: true, difficulty: QuestionDifficulty.MID },
    { id: '3', isMandatory: true, difficulty: QuestionDifficulty.LOW },
    { id: '4', isMandatory: false, difficulty: QuestionDifficulty.HIGH },
    { id: '5', isMandatory: false, difficulty: QuestionDifficulty.HIGH },
    { id: '6', isMandatory: false, difficulty: QuestionDifficulty.MID },
    { id: '7', isMandatory: false, difficulty: QuestionDifficulty.LOW },
    { id: '8', isMandatory: false, difficulty: QuestionDifficulty.LOW },
    { id: '9', isMandatory: false, difficulty: QuestionDifficulty.MID },
    { id: '10', isMandatory: false, difficulty: QuestionDifficulty.LOW },
  ];

  // サンプル回答データ (8問正解、2問不正解のケース)
  const userAnswers: UserAnswer[] = [
    { questionId: '1', isCorrect: true },
    { questionId: '2', isCorrect: true },
    { questionId: '3', isCorrect: true },
    { questionId: '4', isCorrect: true },
    { questionId: '5', isCorrect: true },
    { questionId: '6', isCorrect: true },
    { questionId: '7', isCorrect: true },
    { questionId: '8', isCorrect: true },
    { questionId: '9', isCorrect: false },
    { questionId: '10', isCorrect: false },
  ];

  return { questions, userAnswers };
};

/**
 * サンプルケース1: 必須問題全問正解、HIGH問題も正解
 */
export const sampleCase1 = (): void => {
  const input = createSampleInput();
  const result = calculateScore(input);
  
  console.log('【サンプルケース1: 必須問題全問正解、HIGH問題も正解】');
  console.log(formatScoreDetails(result));
  console.log('\n期待される結果: 80% × 1.0 + 0.4% = 80.4%');
};

/**
 * サンプルケース2: 必須問題1問不正解
 */
export const sampleCase2 = (): void => {
  const input = createSampleInput();
  
  // 必須問題1問を不正解に変更
  const modifiedUserAnswers = [...input.userAnswers];
  modifiedUserAnswers[2] = { questionId: '3', isCorrect: false }; // 3番目の必須問題を不正解に
  
  const modifiedInput = {
    ...input,
    userAnswers: modifiedUserAnswers,
  };
  
  const result = calculateScore(modifiedInput);
  
  console.log('【サンプルケース2: 必須問題1問不正解】');
  console.log(formatScoreDetails(result));
  console.log('\n期待される結果: 70% × (1 - (1/3) × 0.2) + 0.4% = 70% × 0.933 + 0.4% = 65.7%');
};

/**
 * 全サンプルケースを実行する関数
 */
export const runAllSamples = (): void => {
  console.log('=========== 合格率計算サンプル ===========');
  console.log(`現在の設定値:
  - 必須問題ペナルティ係数: ${ScoreConfig.MANDATORY_PENALTY_FACTOR * 100}%
  - HIGH問題ボーナス: +${ScoreConfig.DIFFICULTY_BONUS.HIGH}%/問
  - 合格率上限: ${ScoreConfig.CLIP_MAX_SCORE ? ScoreConfig.MAX_SCORE + '%' : '無制限'}
  `);
  
  sampleCase1();
  console.log('\n----------------------------------------\n');
  sampleCase2();
  console.log('\n=========================================');
};

// サンプルを実行
runAllSamples(); 
/**
 * 合格率計算モジュールのエントリーポイント
 * 
 * @description 合格率計算に関する機能をまとめて外部に公開するファイル。
 * 必要な関数やデータ型をエクスポートします。
 */

// 計算ロジック
export { calculateScore } from './calculator';
export { 
  calculateFrequentlyAskedScore,
  selectTop300FrequentlyAskedQuestions,
  selectUniqueTop300FrequentlyAskedQuestions,
  calculateFrequencyScore,
  calculateAccuracyScore,
  calculateYearlyBonus,
  FrequentlyAskedScoreConfig
} from './frequently_asked_calculator';

// 設定値
export { ScoreConfig } from './config';

// 型定義
export {
  ScoreCalculationInput,
  ScoreResult,
  Question,
  UserAnswer,
  QuestionDifficulty,
  FrequentlyAskedQuestionData,
  FrequentlyAskedScoreResult,
  FrequentlyAskedScoreConfig as FrequentlyAskedScoreConfigType
} from './types';

// ユーティリティ関数
export { formatScoreDetails, isPassing, getScoreMessage } from './utils';

// アダプタークラス
export { ScoreCalculator } from './adapter'; 
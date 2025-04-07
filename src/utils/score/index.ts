/**
 * 合格率計算モジュールのエントリーポイント
 * 
 * @description 合格率計算に関する機能をまとめて外部に公開するファイル。
 * 必要な関数やデータ型をエクスポートします。
 */

// 計算ロジック
export { calculateScore } from './calculator';

// 設定値
export { ScoreConfig } from './config';

// 型定義
export {
  ScoreCalculationInput,
  ScoreResult,
  Question,
  UserAnswer,
  QuestionDifficulty
} from './types';

// ユーティリティ関数
export { formatScoreDetails, isPassing, getScoreMessage } from './utils';

// アダプタークラス
export { ScoreCalculator } from './adapter'; 
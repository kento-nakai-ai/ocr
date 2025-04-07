/**
 * 頻出問題スコア計算モジュール
 * 
 * @description 過去の出題頻度と正答率、有識者評価に基づいて問題の重要度スコアを算出し、
 * 上位300問を抽出するためのロジック。特に毎年出題される問題には追加ボーナスを付与します。
 */

import { ScoreConfig } from './config';

/**
 * 問題情報の型定義
 */
export interface QuestionData {
  id: string;
  content: string;
  yearList: string[]; // 出題された年度のリスト
  accuracy: number;   // 正答率
  expertScore: number; // 有識者評価
}

/**
 * 頻出問題スコア計算の結果
 */
export interface FrequentlyAskedScoreResult {
  questionId: string;
  frequencyScore: number; // 出題頻度スコア
  accuracyScore: number;  // 正答率スコア
  expertScore: number;    // 有識者評価スコア
  yearBonus: number;      // 毎年出題ボーナス
  finalScore: number;     // 最終スコア
  yearList: string[];     // 出題された年度
  isEveryYear: boolean;   // 毎年出題フラグ
}

/**
 * 頻出問題スコア計算の設定
 */
export const FrequentlyAskedScoreConfig = {
  // 各要素の配分（合計1.0になるように）
  FREQUENCY_WEIGHT: 0.4,   // 出題頻度の重み
  ACCURACY_WEIGHT: 0.3,    // 正答率の重み（低い方が重要と仮定）
  EXPERT_WEIGHT: 0.3,      // 有識者評価の重み
  
  // 毎年出題ボーナス
  EVERY_YEAR_BONUS: 0.20,  // 8/8年出題時の加点
  ALMOST_EVERY_YEAR_BONUS: {
    7: 0.15, // 7/8年出題時の加点
    6: 0.10, // 6/8年出題時の加点
  },
  
  // その他設定
  YEARS_TO_CONSIDER: 8,     // 考慮する過去の年数
  DECIMAL_PLACES: 2,        // 小数点以下の桁数
};

/**
 * 出題頻度スコアを計算する関数
 * 
 * @param yearList 出題された年度のリスト
 * @param totalYears 考慮する過去の年数
 * @returns 頻度スコア（0.0～1.0）
 */
export const calculateFrequencyScore = (yearList: string[], totalYears: number): number => {
  if (!yearList || yearList.length === 0) return 0;
  return yearList.length / totalYears;
};

/**
 * 正答率スコアを計算する関数
 * 正答率は低いほど「難しい」と判断し、高いスコアを与えます
 * 
 * @param accuracy 問題の正答率（0.0～1.0）
 * @returns 正答率スコア（0.0～1.0）
 */
export const calculateAccuracyScore = (accuracy: number): number => {
  // 正答率が低いほど重要度が高いとみなす（1 - 正答率）
  return Math.max(0, Math.min(1, 1 - accuracy));
};

/**
 * 毎年出題ボーナスを計算する関数
 * 
 * @param yearList 出題された年度のリスト
 * @param totalYears 考慮する過去の年数
 * @returns ボーナス値
 */
export const calculateYearlyBonus = (yearList: string[], totalYears: number): number => {
  if (!yearList || yearList.length === 0) return 0;
  
  // 全年度で出題された場合
  if (yearList.length === totalYears) {
    return FrequentlyAskedScoreConfig.EVERY_YEAR_BONUS;
  }
  
  // 7/8年度で出題された場合
  if (yearList.length === 7) {
    return FrequentlyAskedScoreConfig.ALMOST_EVERY_YEAR_BONUS[7];
  }
  
  // 6/8年度で出題された場合
  if (yearList.length === 6) {
    return FrequentlyAskedScoreConfig.ALMOST_EVERY_YEAR_BONUS[6];
  }
  
  return 0;
};

/**
 * 頻出問題の総合スコアを計算する関数
 * 
 * @param question 問題データ
 * @returns スコア計算結果
 */
export const calculateFrequentlyAskedScore = (question: QuestionData): FrequentlyAskedScoreResult => {
  const totalYears = FrequentlyAskedScoreConfig.YEARS_TO_CONSIDER;
  
  // 各要素のスコアを計算
  const frequencyScore = calculateFrequencyScore(question.yearList, totalYears);
  const accuracyScore = calculateAccuracyScore(question.accuracy);
  const expertScore = question.expertScore || 0;
  
  // 毎年出題ボーナスを計算
  const yearBonus = calculateYearlyBonus(question.yearList, totalYears);
  const isEveryYear = question.yearList.length === totalYears;
  
  // 要素の重み付け計算
  const weightedScore = 
    frequencyScore * FrequentlyAskedScoreConfig.FREQUENCY_WEIGHT +
    accuracyScore * FrequentlyAskedScoreConfig.ACCURACY_WEIGHT +
    expertScore * FrequentlyAskedScoreConfig.EXPERT_WEIGHT;
  
  // 最終スコア = 重み付けスコア + 毎年出題ボーナス
  let finalScore = weightedScore + yearBonus;
  
  // 小数点以下を丸める
  finalScore = Number(finalScore.toFixed(FrequentlyAskedScoreConfig.DECIMAL_PLACES));
  
  return {
    questionId: question.id,
    frequencyScore,
    accuracyScore,
    expertScore,
    yearBonus,
    finalScore,
    yearList: question.yearList,
    isEveryYear,
  };
};

/**
 * 問題リストから上位300問を抽出する関数
 * 
 * @param questions 問題データのリスト
 * @returns スコア計算結果のリスト（上位300問）
 */
export const selectTop300FrequentlyAskedQuestions = (questions: QuestionData[]): FrequentlyAskedScoreResult[] => {
  // すべての問題のスコアを計算
  const scoredQuestions = questions.map(question => calculateFrequentlyAskedScore(question));
  
  // スコアの高い順にソート
  const sortedQuestions = scoredQuestions.sort((a, b) => b.finalScore - a.finalScore);
  
  // 上位300問を返す（300問未満の場合は全問返す）
  return sortedQuestions.slice(0, 300);
};

/**
 * 同一問題を除外して上位300問を抽出する関数
 * 
 * @param questions 問題データのリスト（同一問題が複数含まれている可能性あり）
 * @returns スコア計算結果のリスト（重複除外後の上位300問）
 */
export const selectUniqueTop300FrequentlyAskedQuestions = (questions: QuestionData[]): FrequentlyAskedScoreResult[] => {
  // 同一問題を除外（問題IDをキーとして最新のデータだけを残す）
  const uniqueQuestions = new Map<string, QuestionData>();
  
  for (const question of questions) {
    uniqueQuestions.set(question.id, question);
  }
  
  // 一意の問題リストでスコア計算
  return selectTop300FrequentlyAskedQuestions(Array.from(uniqueQuestions.values()));
}; 
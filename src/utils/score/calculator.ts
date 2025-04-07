/**
 * 合格率計算モジュール
 * 
 * @description ユーザーの回答データから合格率を算出するためのコアロジック。
 * 基本スコア、必須問題係数、難易度ボーナスの計算を行い、最終的な合格率を返します。
 */

import { ScoreConfig } from './config';
import { 
  ScoreCalculationInput, 
  ScoreResult,
  QuestionDifficulty
} from './types';

/**
 * 基本スコアを計算する関数
 * 
 * @param correctCount 正解数
 * @param totalQuestions 総問題数
 * @returns 基本スコア（百分率）
 */
const calculateBaseScore = (correctCount: number, totalQuestions: number): number => {
  if (totalQuestions === 0) return 0;
  return (correctCount / totalQuestions) * 100;
};

/**
 * 必須問題係数を計算する関数
 * 
 * @param correctMandatory 必須問題の正解数
 * @param totalMandatory 必須問題の総数
 * @returns 必須問題係数（1.0以下の小数値）
 */
const calculateMandatoryFactor = (correctMandatory: number, totalMandatory: number): number => {
  if (totalMandatory === 0) return 1.0; // 必須問題がない場合は係数1.0
  
  // 必須問題を全問正解した場合は係数1.0
  if (correctMandatory === totalMandatory) return 1.0;
  
  // 必須問題を落とした場合のペナルティ計算
  // 1.0 - (1 - correctMandatory/totalMandatory) * ペナルティ係数
  return 1.0 - (1.0 - correctMandatory / totalMandatory) * ScoreConfig.MANDATORY_PENALTY_FACTOR;
};

/**
 * 難易度ボーナスを計算する関数
 * 
 * @param correctByDifficulty 難易度別の正解数
 * @returns 難易度ボーナス（加点値）
 */
const calculateDifficultyBonus = (
  correctByDifficulty: { [key in QuestionDifficulty]: number }
): number => {
  return (
    correctByDifficulty[QuestionDifficulty.LOW] * ScoreConfig.DIFFICULTY_BONUS.LOW +
    correctByDifficulty[QuestionDifficulty.MID] * ScoreConfig.DIFFICULTY_BONUS.MID +
    correctByDifficulty[QuestionDifficulty.HIGH] * ScoreConfig.DIFFICULTY_BONUS.HIGH
  );
};

/**
 * 合格率を計算する関数
 * 
 * @param input 計算に必要な入力データ
 * @returns 合格率と計算内訳
 */
export const calculateScore = (input: ScoreCalculationInput): ScoreResult => {
  const { questions, userAnswers } = input;
  
  // 計算に必要な集計値を初期化
  const totalQuestions = questions.length;
  const mandatoryQuestions = questions.filter(q => q.isMandatory).length;
  
  // 正解数の集計
  const correctAnswers = userAnswers.filter(a => a.isCorrect).length;
  
  // 正解した必須問題の数を集計
  const correctMandatory = userAnswers
    .filter(a => a.isCorrect)
    .filter(a => {
      const question = questions.find(q => q.id === a.questionId);
      return question?.isMandatory;
    }).length;
  
  // 難易度別の正解数を集計
  const correctByDifficulty = {
    [QuestionDifficulty.LOW]: 0,
    [QuestionDifficulty.MID]: 0,
    [QuestionDifficulty.HIGH]: 0,
  };
  
  userAnswers
    .filter(a => a.isCorrect)
    .forEach(a => {
      const question = questions.find(q => q.id === a.questionId);
      if (question) {
        correctByDifficulty[question.difficulty]++;
      }
    });
  
  // 各スコア要素の計算
  const baseScore = calculateBaseScore(correctAnswers, totalQuestions);
  const mandatoryFactor = calculateMandatoryFactor(correctMandatory, mandatoryQuestions);
  const difficultyBonus = calculateDifficultyBonus(correctByDifficulty);
  
  // 最終スコアの計算
  let finalScore = baseScore * mandatoryFactor + difficultyBonus;
  
  // 最大値でクリップするかどうか
  if (ScoreConfig.CLIP_MAX_SCORE && finalScore > ScoreConfig.MAX_SCORE) {
    finalScore = ScoreConfig.MAX_SCORE;
  }
  
  // 小数点以下を丸める
  finalScore = Number(finalScore.toFixed(ScoreConfig.DECIMAL_PLACES));
  
  return {
    finalScore,
    details: {
      baseScore,
      mandatoryFactor,
      difficultyBonus,
      totalQuestions,
      correctAnswers,
      mandatoryQuestions,
      correctMandatory,
      correctByDifficulty,
    },
  };
}; 